"""
agents/classification_agent.py  —  AG-02: Classification Agent

KEY DESIGN DECISIONS:
  - async def classification_node — runs inside LangGraph's event loop
  - Single Groq call returns ALL 7 fields (classification + sentiment + ticket)
  - Model:  llama-3.3-70b-versatile  (primary, via llm_client.py)
  - Fallback chain: llama-4-scout-17b → qwen3-32b → llama-3.1-8b (rate-limit only)
  - Confidence < 0.70 → low_confidence_flag=True → human_review queue
  - Sentiment  < -0.50 → escalation_flag=True → Slack alert

ALL BUGS FIXED vs previous version:
  BUG-1  max_tokens was 256 — too small for 7-field JSON
         FIX: raised to 350
  BUG-2  asyncio.new_event_loop() inside running LangGraph loop → RuntimeError
         FIX: classification_node is now async def; DB update uses direct await
  BUG-3  email_text read from single key — empty when intake writes to email_body
         FIX: 4-key fallback chain (email_text → email_body → parsed.body → parsed.text)
  BUG-4  is_ticket + ticket_type not extracted or written to state / DB
         FIX: extracted from result, written to state dict and Supabase
  BUG-5  DB SQL had 7 params but only 7 $N placeholders — now 9 with is_ticket/ticket_type
         FIX: SQL updated, _async_update_email extracted as standalone async function
  BUG-6  JSON fence stripping missing — LLM occasionally wraps output in ```json
         FIX: defensive strip before json.loads()
  BUG-7  empty email_text produced silent wrong classification (general_query always)
         FIX: warning logged + early human_review route when body is empty
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx

from config.settings import settings
from mcp_tools.llm_client import LLMProvider, call_llm
from prompts.classification_prompt import (
    VALID_TICKET_TYPES,
    build_classification_prompts,
    CLASSIFICATION_SYSTEM_PROMPT,
    CLASSIFICATION_USER_PROMPT,
)
from state.shared_state import AgentState
from utils.domain_loader import get_sla_seconds
from utils.retry_utils import retry_with_backoff, send_to_dead_letter_queue
from agents.agent_metrics import instrument_agent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SLA FALLBACK MAP  (used when no domain_config — tests / cold start)
# ---------------------------------------------------------------------------
_SLA_FALLBACK: dict[str, timedelta] = {
    "4h":  timedelta(hours=4),
    "8h":  timedelta(hours=8),
    "24h": timedelta(hours=24),
    "48h": timedelta(hours=48),
}

# ---------------------------------------------------------------------------
# GROQ LLM CALL  — single batched request for all 7 output fields
# ---------------------------------------------------------------------------
@retry_with_backoff(retries=3, on_exhaust="dlq")
def _classify_and_score(
    email_text: str,
    email_subject: str = "",
    domain_config: Optional[dict] = None,
) -> Dict[str, Any]:
    """
    Call Groq with the classification prompt and return the parsed JSON result.

    Returns dict with keys:
      category · priority · sla_bucket · confidence · sentiment_score
      is_ticket · ticket_type

    Raises ValueError on parse failure or missing required keys.
    Uses domain-aware prompt when domain_config is provided.
    max_tokens=350 — raised from 256 to safely fit all 7 fields.
    """
    if domain_config:
        sys_prompt, usr_template = build_classification_prompts(domain_config)
    else:
        sys_prompt   = CLASSIFICATION_SYSTEM_PROMPT
        usr_template = CLASSIFICATION_USER_PROMPT

    user_msg = usr_template.format(
        email_subject=email_subject,
        email_text=email_text,
    )

    raw = call_llm(
        provider=LLMProvider.GROQ,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user",   "content": user_msg},
        ],
        temperature=0.1,
        max_tokens=350,          # BUG-1 FIX: was 256, too small for 7 fields
    )

    # BUG-6 FIX: strip markdown code fences before parsing
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines   = [l for l in cleaned.splitlines() if not l.startswith("```")]
        cleaned = "\n".join(lines).strip()

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.error(json.dumps({
            "event": "classification_json_parse_error",
            "raw":   raw[:400],
        }))
        raise ValueError(f"LLM returned non-JSON: {raw[:200]}")

    # Validate core required keys
    required = {"category", "priority", "sla_bucket", "confidence", "sentiment_score"}
    missing  = required - set(result.keys())
    if missing:
        raise ValueError(f"LLM response missing keys: {missing}")

    # FIX: Case-insensitive label path detection with canonical casing restoration.
    # LLM sometimes returns correct label but wrong case e.g. "others/uncategorised"
    # Gmail API is case-sensitive — must restore exact casing before label lookup.
    cat = result.get("category", "others")

    # Canonical casing map — every valid Gmail label path
    _CANONICAL = {
        "it support/network ops team":                 "IT Support/Network Ops Team",
        "it support/security team":                    "IT Support/Security Team",
        "it support/general it queue":                 "IT Support/General IT Queue",
        "hr/hr operations":                            "HR/HR Operations",
        "hr/payroll team":                             "HR/Payroll Team",
        "hr/recruitment team":                         "HR/Recruitment Team",
        "hr/employee relations":                       "HR/Employee Relations",
        "customer support/customer issues":            "Customer Support/Customer Issues",
        "customer support/customer issues/priority 1": "Customer Support/Customer Issues/Priority 1",
        "customer support/customer issues/priority 2": "Customer Support/Customer Issues/Priority 2",
        "customer support/customer issues/priority 3": "Customer Support/Customer Issues/Priority 3",
        "customer support/product support":            "Customer Support/Product Support",
        "customer support/warranty":                   "Customer Support/Warranty",
        "others/uncategorised":                        "Others/Uncategorised",
        "others/uncategorized":                        "Others/Uncategorised",
    }

    _FULL_LABEL_PREFIXES_LOWER = (
        "it support/", "hr/", "customer support/", "others/",
    )

    # Strip trailing explanation text LLM may append after label path
    # e.g. "IT Support/IT Support Team → Hardware issue" → keep only label
    if "→" in cat:
        cat = cat.split("→")[0].strip()
    elif " - " in cat and "/" in cat:
        cat = cat.split(" - ")[0].strip()

    cat_lower = cat.lower().strip()

    if any(cat_lower.startswith(p) for p in _FULL_LABEL_PREFIXES_LOWER):
        # Full Gmail label path — restore canonical casing
        cat = _CANONICAL.get(cat_lower, cat)
        logger.info(json.dumps({
            "event":    "classification_category_resolved",
            "raw":      result.get("category"),
            "resolved": cat,
            "type":     "gmail_label_path",
        }))
    else:
        # Short code from generic fallback prompt — normalise to lowercase
        cat = cat_lower.replace(" ", "_").replace("-", "_")
        _NORM = {
            "other":           "others",
            "general":         "general_query",
            "it_support":      "it",
            "hr_issue":        "hr",
            "salary_issue":    "hr",
            "salary_query":    "hr",
            "payroll":         "hr",
            "payroll_query":   "hr",
            "headcount":       "hr",
            "recruitment":     "hr",
            "hiring":          "hr",
            "leave":           "hr",
            "leave_request":   "hr",
            "offer_letter":    "hr",
            "grievance":       "hr",
            "harassment":      "hr",
            "invoice":         "billing",
            "invoice_dispute": "billing",
            "payment":         "billing",
            "refund":          "billing",
            "overcharge":      "billing",
            "vpn_issue":       "network_issue",
            "connectivity":    "network_issue",
            "access_denied":   "access_request",
            "software_issue":  "software_bug",
            "technical_issue": "software_bug",
        }
        cat = _NORM.get(cat, cat)
        logger.info(json.dumps({
            "event":    "classification_category_resolved",
            "raw":      result.get("category"),
            "resolved": cat,
            "type":     "short_code",
        }))

    result["category"] = cat

    # BUG-4 FIX: backfill is_ticket / ticket_type if model omitted them
    result["is_ticket"]   = bool(result.get("is_ticket", False))
    ticket_type = result.get("ticket_type", "null")
    if ticket_type not in VALID_TICKET_TYPES:
        ticket_type = "null"
    result["ticket_type"] = ticket_type

    return result


# ---------------------------------------------------------------------------
# SLACK ESCALATION ALERT  (sentiment < -0.5)
# ---------------------------------------------------------------------------
def _send_escalation_alert(
    email_id: str,
    sentiment: float,
    sender: str,
) -> None:
    """
    Fire escalation alert to Slack. Falls back to Gmail if Slack fails.
    Called from within an async context — uses asyncio.create_task for Gmail.
    """
    channel = getattr(settings, "SLACK_CHANNEL_ESCALATIONS", "#escalations")
    token   = getattr(settings, "SLACK_BOT_TOKEN", None)
    message = (
        f":rotating_light: *Escalation Alert* :rotating_light:\n"
        f"Email `{email_id}` from `{sender}` · sentiment `{sentiment:.2f}` "
        f"(threshold {settings.SENTIMENT_ESCALATION_THRESHOLD})\n"
        f"Immediate Team Lead review required."
    )

    slack_ok = False
    if token:
        try:
            resp = httpx.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type":  "application/json",
                },
                json={"channel": channel, "text": message, "mrkdwn": True},
                timeout=8,
            )
            slack_ok = resp.json().get("ok", False)
            if slack_ok:
                logger.info(json.dumps({
                    "event":    "escalation_slack_sent",
                    "email_id": email_id,
                    "channel":  channel,
                }))
            else:
                logger.error(json.dumps({
                    "event": "escalation_slack_failed",
                    "error": resp.json().get("error"),
                }))
        except Exception as exc:
            logger.error(json.dumps({
                "event": "escalation_slack_exception",
                "error": str(exc),
            }))

    # Gmail fallback — fire-and-forget via asyncio.create_task
    # Safe here because classification_node is async def
    if not slack_ok:
        logger.warning(json.dumps({
            "event":    "escalation_slack_failed_gmail_fallback",
            "email_id": email_id,
        }))
        try:
            from mcp_tools.gmail_client import gmail_client
            team_lead = getattr(settings, "TEAM_LEAD_EMAIL", None)
            if team_lead:
                asyncio.create_task(
                    gmail_client.send_reply(
                        to=team_lead,
                        subject=f"[ESCALATION] Sentiment alert — email {email_id}",
                        body=(
                            f"Email {email_id} from {sender}\n"
                            f"Sentiment: {sentiment:.2f} "
                            f"(threshold {settings.SENTIMENT_ESCALATION_THRESHOLD})\n"
                            f"Immediate Team Lead review required."
                        ),
                        thread_id=None,
                    )
                )
                logger.info(json.dumps({
                    "event":    "escalation_gmail_fallback_queued",
                    "email_id": email_id,
                }))
        except Exception as exc:
            logger.error(json.dumps({
                "event":    "escalation_all_alerts_failed",
                "email_id": email_id,
                "error":    str(exc),
            }))


# ---------------------------------------------------------------------------
# DATABASE UPDATE  — standalone async function (clean, testable, no new loop)
# ---------------------------------------------------------------------------
async def _async_update_email(
    email_id:           str,
    result:             dict,
    sentiment_score:    float,
    confidence:         float,
    low_confidence_flag: bool,
    sla_deadline:       datetime,
    escalation_flag:    bool,
    next_step:          str,
    is_ticket:          bool,
    ticket_type:        Optional[str],
) -> None:
    """
    Update the emails table in Supabase with all classification results.

    BUG-2 FIX: this function is awaited directly inside the async
    classification_node — no asyncio.new_event_loop() needed.
    asyncio.new_event_loop() inside a running LangGraph loop raises RuntimeError.

    BUG-5 FIX: SQL now has 9 parameters including is_ticket ($8) and ticket_type ($9).
    Requires Supabase migration:
      ALTER TABLE emails ADD COLUMN IF NOT EXISTS is_ticket boolean DEFAULT false;
      ALTER TABLE emails ADD COLUMN IF NOT EXISTS ticket_type text;
    """
    import asyncpg

    db_url = getattr(settings, "DATABASE_URL", "").replace(
        "postgresql+asyncpg://", "postgresql://"
    )
    try:
        conn = await asyncpg.connect(db_url)
        try:
            await conn.execute(
                """
                UPDATE emails SET
                    classification_result = $1::jsonb,
                    sentiment_score       = $2,
                    confidence            = $3,
                    low_confidence_flag   = $4,
                    sla_deadline          = $5,
                    escalated             = $6,
                    current_step          = $7,
                    is_ticket             = $8,
                    ticket_type           = $9
                WHERE email_id = $10::uuid
                """,
                json.dumps(result),   # $1  jsonb
                sentiment_score,      # $2
                confidence,           # $3
                low_confidence_flag,  # $4
                sla_deadline,         # $5
                escalation_flag,      # $6
                next_step,            # $7
                is_ticket,            # $8
                ticket_type,          # $9
                email_id,             # $10 uuid
            )
        finally:
            await conn.close()
    except Exception as exc:
        logger.error(json.dumps({
            "event":    "db_update_failed",
            "email_id": email_id,
            "error":    str(exc),
        }))


# ---------------------------------------------------------------------------
# AG-02 LANGGRAPH NODE  — must be async def (BUG-2 FIX)
# ---------------------------------------------------------------------------
@instrument_agent("AG-02")
async def classification_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node for AG-02.

    Reads from state:
      email_text / email_body / parsed_email.body / parsed_email.text
      email_subject / parsed_email.subject / raw_email.subject
      parsed_email · domain_config · email_id

    Writes to state:
      classification_result · category · confidence · sentiment_score
      low_confidence_flag · escalation_flag · escalated
      sla_deadline · global_sla_deadline · sla_bucket
      is_ticket · ticket_type
      current_step · agent_statuses · event_queue · error
    """

    # ── Extract all inputs from state ──────────────────────────────────────
    parsed        = state.get("parsed_email") or {}
    email_id      = parsed.get("email_id") or state.get("email_id", "unknown")
    sender        = parsed.get("sender", "unknown")
    domain_config = state.get("domain_config")   # None is fine — falls back to generic prompt

    # BUG-3 FIX: 4-key fallback chain for email body
    # intake_agent may write body under different state keys depending on source
    email_text: str = (
        state.get("email_text")
        or state.get("email_body")
        or parsed.get("body", "")
        or parsed.get("text", "")
        or ""
    )

    # Subject fallback chain
    email_subject: str = (
        state.get("email_subject")
        or parsed.get("subject", "")
        or (state.get("raw_email") or {}).get("subject", "")
    )

    logger.info(json.dumps({
        "event":    "classification_started",
        "email_id": email_id,
        "domain":   (domain_config or {}).get("domain_id", "unknown"),
        "subject":  email_subject[:60],
        "body_len": len(email_text),
    }))

    # BUG-7 FIX: detect empty body early — can't classify what we can't read
    if not email_text.strip():
        logger.warning(json.dumps({
            "event":    "classification_empty_body",
            "email_id": email_id,
            "action":   "routing to human_review",
            "hint":     "Check intake_agent — body may be written under a different state key",
        }))
        return {
            "error":             "email_text is empty — cannot classify",
            "low_confidence_flag": True,
            "current_step":      "human_review",
            "retry_count":       state.get("retry_count", 0) + 1,
            "agent_statuses":    {**state.get("agent_statuses", {}), "AG-02": "empty_body"},
            "event_queue": [_audit_event(email_id, "classification_skipped", {
                "reason": "empty email body",
            })],
        }

    # ── Single Groq call (domain-aware) ───────────────────────────────────
    try:
        result = _classify_and_score(
            email_text,
            email_subject=email_subject,
            domain_config=domain_config,
        )
    except Exception as exc:
        send_to_dead_letter_queue({"email_id": email_id}, str(exc))
        return {
            "error":       str(exc),
            "retry_count": state.get("retry_count", 0) + 1,
            "agent_statuses": {**state.get("agent_statuses", {}), "AG-02": "failed"},
            "event_queue": [_audit_event(email_id, "classification_failed", {
                "error": str(exc),
            })],
        }

    # ── Extract all 7 fields ───────────────────────────────────────────────
    category        = result["category"]
    priority        = result.get("priority", "medium")
    sla_bucket      = result.get("sla_bucket", "24h")
    confidence      = float(result["confidence"])
    sentiment_score = float(result["sentiment_score"])
    is_ticket       = bool(result.get("is_ticket", False))
    ticket_type     = result.get("ticket_type", "null")

    # ── Threshold gates (locked values from design doc) ───────────────────
    low_confidence_flag = confidence < settings.CONFIDENCE_THRESHOLD           # 0.70
    escalation_flag     = sentiment_score < settings.SENTIMENT_ESCALATION_THRESHOLD  # -0.50

    if escalation_flag:
        _send_escalation_alert(email_id, sentiment_score, sender)

    # ── SLA deadline (domain-aware) ────────────────────────────────────────
    if domain_config:
        sla_seconds = get_sla_seconds(domain_config, priority)
        sla_delta   = timedelta(seconds=sla_seconds)
        # Prefer LLM's sla_bucket; fall back to first domain rule key
        sla_bucket = result.get(
            "sla_bucket",
            next(iter(domain_config.get("sla_rules", {"24h": {}})), "24h"),
        )
    else:
        sla_delta = _SLA_FALLBACK.get(sla_bucket, timedelta(hours=24))

    sla_deadline = datetime.utcnow() + sla_delta
    next_step    = "human_review" if low_confidence_flag else "routing"

    # ── Audit event ────────────────────────────────────────────────────────
    audit = _audit_event(email_id, "email_classified", {
        "category":         category,
        "priority":         priority,
        "sla_bucket":       sla_bucket,
        "confidence":       confidence,
        "sentiment_score":  sentiment_score,
        "is_ticket":        is_ticket,
        "ticket_type":      ticket_type,
        "escalated":        escalation_flag,
        "low_confidence":   low_confidence_flag,
        "next_step":        next_step,
    })

    logger.info(json.dumps({
        "event":        "classification_completed",
        "email_id":     email_id,
        "category":     category,
        "priority":     priority,
        "confidence":   round(confidence, 3),
        "sentiment":    round(sentiment_score, 3),
        "is_ticket":    is_ticket,
        "ticket_type":  ticket_type,
        "next_step":    next_step,
    }))

    # ── DB update — direct await (BUG-2 FIX) ──────────────────────────────
    await _async_update_email(
        email_id=email_id,
        result=result,
        sentiment_score=sentiment_score,
        confidence=confidence,
        low_confidence_flag=low_confidence_flag,
        sla_deadline=sla_deadline,
        escalation_flag=escalation_flag,
        next_step=next_step,
        is_ticket=is_ticket,
        ticket_type=ticket_type,
    )

    # ── Return to LangGraph state ──────────────────────────────────────────
    return {
        # Full result dict (used by routing_agent, audit_agent)
        "classification_result": result,

        # Individual fields (used by various downstream agents)
        "category":              category,
        "confidence":            confidence,
        "sentiment_score":       sentiment_score,
        "low_confidence_flag":   low_confidence_flag,
        "escalation_flag":       escalation_flag,
        "escalated":             escalation_flag,
        "sla_bucket":            sla_bucket,
        "sla_deadline":          sla_deadline,   # read by AG-05 SLA Monitor
        "global_sla_deadline":   sla_deadline,
        "is_ticket":             is_ticket,
        "ticket_type":           ticket_type,    # read by AG-01 ACK engine

        # Pipeline control
        "current_step":   next_step,
        "agent_statuses": {**state.get("agent_statuses", {}), "AG-02": "completed"},
        "event_queue":    [audit],
        "error":          None,
    }


# ---------------------------------------------------------------------------
# AUDIT HELPER
# ---------------------------------------------------------------------------
def _audit_event(
    email_id:   str,
    event_type: str,
    payload:    dict,
) -> Dict[str, Any]:
    return {
        "type":      event_type,
        "agent_id":  "AG-02",
        "email_id":  email_id,
        "timestamp": datetime.utcnow().isoformat(),
        "payload":   payload,
    }