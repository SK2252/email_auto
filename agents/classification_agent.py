"""
agents/classification_agent.py — AG-02: Classification Agent
Sprint 4-5.

KEY DESIGN DECISIONS:
  - Single Groq call for BOTH classification AND sentiment (conserve 30 rpm limit)
  - Model: llama-3.3-70b-versatile (via llm_client.py — never hardcoded here)
  - Confidence < 0.7  → low_confidence_flag = True → human review queue
  - Sentiment  < -0.5 → escalation_flag → Slack alert to Team Lead channel
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from config.settings import settings
from mcp_tools.llm_client import LLMProvider, call_llm
from prompts.classification_prompt import (
    build_classification_prompts,
    CLASSIFICATION_SYSTEM_PROMPT,
    CLASSIFICATION_USER_PROMPT,
)
from state.shared_state import AgentState
from utils.domain_loader import get_sla_seconds, get_escalation_threshold
from utils.retry_utils import retry_with_backoff, send_to_dead_letter_queue

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SLA bucket → timedelta map (legacy fallback — domain configs override this)
# ---------------------------------------------------------------------------
_SLA_MAP_LEGACY = {
    "4h":  lambda: timedelta(hours=4),
    "8h":  lambda: timedelta(hours=8),
    "24h": lambda: timedelta(hours=24),
    "48h": lambda: timedelta(hours=48),
}


# ---------------------------------------------------------------------------
# Groq call — batched classification + sentiment in ONE request
# ---------------------------------------------------------------------------
@retry_with_backoff(retries=3, on_exhaust="dlq")
def _classify_and_score(
    email_text: str,
    domain_config: dict | None = None,
) -> Dict[str, Any]:
    """
    Single Groq call that returns both classification and sentiment.
    Uses domain-aware prompts when domain_config is provided.
    Batching into one call conserves the 30 rpm / 14,400 rpd free quota.
    """
    if domain_config:
        sys_prompt, usr_prompt = build_classification_prompts(domain_config)
    else:
        sys_prompt = CLASSIFICATION_SYSTEM_PROMPT
        usr_prompt = CLASSIFICATION_USER_PROMPT

    raw = call_llm(
        provider=LLMProvider.GROQ,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user",   "content": usr_prompt.format(email_text=email_text)},
        ],
        temperature=0.1,
        max_tokens=256,
    )

    try:
        result = json.loads(raw.strip())
    except json.JSONDecodeError:
        logger.error(json.dumps({"event": "classification_json_parse_error", "raw": raw[:300]}))
        raise ValueError(f"LLM returned non-JSON: {raw[:200]}")

    # Validate required keys
    required = {"category", "priority", "sla_bucket", "confidence", "sentiment_score"}
    missing  = required - set(result.keys())
    if missing:
        raise ValueError(f"LLM response missing keys: {missing}")

    return result


# ---------------------------------------------------------------------------
# Slack escalation alert (AG-02 — sentiment < -0.5)
# ---------------------------------------------------------------------------
def _send_escalation_alert(email_id: str, sentiment: float, sender: str) -> None:
    from config.settings import settings
    import httpx

    channel = getattr(settings, "SLACK_CHANNEL_ESCALATIONS", "#escalations")
    message = (
        f":rotating_light: *Escalation Alert* :rotating_light:\n"
        f"Email `{email_id}` from `{sender}` has sentiment score `{sentiment:.2f}` "
        f"(threshold: {settings.SENTIMENT_ESCALATION_THRESHOLD}).\n"
        f"Immediate Team Lead review required."
    )

    token    = getattr(settings, "SLACK_BOT_TOKEN", None)
    slack_ok = False

    if token:
        try:
            resp = httpx.post(
                "https://slack.com/api/chat.postMessage",
                headers={"Authorization": f"Bearer {token}",
                         "Content-Type": "application/json"},
                json={"channel": channel, "text": message, "mrkdwn": True},
                timeout=8,
            )
            slack_ok = resp.json().get("ok", False)
            if slack_ok:
                logger.info(json.dumps({
                    "event":   "escalation_slack_sent",
                    "email_id": email_id, "channel": channel,
                }))
            else:
                logger.error(json.dumps({
                    "event":  "escalation_slack_failed",
                    "error":  resp.json().get("error"),
                }))
        except Exception as exc:
            logger.error(json.dumps({"event": "escalation_slack_exception", "error": str(exc)}))

    # Mandatory fallback: email via gmail-mcp if Slack failed
    if not slack_ok:
        logger.warning(json.dumps({"event": "escalation_slack_failed_trying_gmail_fallback",
                                    "email_id": email_id}))
        try:
            import asyncio
            from app.domains.email_ai import tools_email as email_tools
            team_lead = getattr(settings, "TEAM_LEAD_EMAIL", None)
            if team_lead:
                asyncio.get_event_loop().run_until_complete(
                    email_tools.gmail_send_email(
                        to=team_lead,
                        subject=f"[ESCALATION] Sentiment alert on email {email_id}",
                        body=(
                            f"Escalation alert: email {email_id} from {sender}\n"
                            f"Sentiment score: {sentiment:.2f} (threshold: "
                            f"{settings.SENTIMENT_ESCALATION_THRESHOLD})\n"
                            f"Immediate Team Lead review required."
                        ),
                        thread_id=None,
                    )
                )
                logger.info(json.dumps({"event": "escalation_gmail_fallback_sent",
                                        "email_id": email_id}))
        except Exception as exc:
            # Both Slack and gmail failed — log only
            logger.error(json.dumps({"event": "escalation_all_alerts_failed",
                                     "email_id": email_id, "error": str(exc)}))


# ---------------------------------------------------------------------------
# AG-02 LangGraph node
# ---------------------------------------------------------------------------
def classification_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node for AG-02.
    Reads: email_text, parsed_email, domain_config
    Writes: classification_result, confidence, sentiment_score,
            low_confidence_flag, sla_deadline, event_queue
    """
    email_text    = state.get("email_text", "")
    parsed        = state.get("parsed_email", {})
    email_id      = parsed.get("email_id", state.get("email_id", "unknown"))
    sender        = parsed.get("sender", "unknown")
    domain_config = state.get("domain_config")  # injected at intake; may be None in tests

    logger.info(json.dumps({"event": "classification_started", "email_id": email_id,
                             "domain": (domain_config or {}).get("domain_id", "unknown")}))

    # ---- ONE batched Groq call (domain-aware) ----
    try:
        result = _classify_and_score(email_text, domain_config=domain_config)
    except Exception as exc:
        send_to_dead_letter_queue({"email_id": email_id}, str(exc))
        return {
            "error":       str(exc),
            "retry_count": state.get("retry_count", 0) + 1,
            "event_queue": [_audit_event(email_id, "classification_failed", {"error": str(exc)})],
        }

    confidence      = float(result["confidence"])
    sentiment_score = float(result["sentiment_score"])
    priority        = result.get("priority", "medium")

    # ---- Threshold logic (locked from design doc) ----
    low_confidence_flag = confidence < settings.CONFIDENCE_THRESHOLD    # < 0.7
    escalation_flag     = sentiment_score < settings.SENTIMENT_ESCALATION_THRESHOLD  # < -0.5

    if escalation_flag:
        _send_escalation_alert(email_id, sentiment_score, sender)

    # ---- Compute SLA deadline (domain-aware) ----
    if domain_config:
        # Use domain's priority → SLA seconds mapping
        sla_seconds = get_sla_seconds(domain_config, priority)
        sla_delta   = timedelta(seconds=sla_seconds)
        sla_bucket  = result.get("sla_bucket", list(domain_config.get("sla_rules", {"24h": {}}).keys())[0])
    else:
        # Legacy fallback for tests without domain config
        sla_bucket = result.get("sla_bucket", "24h")
        sla_delta  = _SLA_MAP_LEGACY.get(sla_bucket, lambda: timedelta(hours=24))()

    sla_deadline = datetime.utcnow() + sla_delta

    next_step = "human_review" if low_confidence_flag else "routing"

    audit = _audit_event(email_id, "email_classified", {
        "category":       result["category"],
        "priority":       result["priority"],
        "sla_bucket":     sla_bucket,
        "confidence":     confidence,
        "sentiment_score": sentiment_score,
        "escalated":      escalation_flag,
        "low_confidence": low_confidence_flag,
    })

    logger.info(json.dumps({
        "event":      "classification_completed",
        "email_id":   email_id,
        "category":   result["category"],
        "confidence": confidence,
        "next_step":  next_step,
    }))

    # --- Phase 5: UPDATE PostgreSQL emails table ---
    async def _async_update_email():
        import asyncpg
        db_url = getattr(settings, "DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
        try:
            conn = await asyncpg.connect(db_url)
            try:
                await conn.execute(
                    """
                    UPDATE emails SET
                        classification_result = $1::jsonb,
                        sentiment_score = $2,
                        confidence = $3,
                        low_confidence_flag = $4,
                        sla_deadline = $5,
                        escalated = $6,
                        current_step = $7
                    WHERE email_id = $8::uuid
                    """,
                    json.dumps(result),
                    sentiment_score,
                    confidence,
                    low_confidence_flag,
                    sla_deadline,
                    escalation_flag,
                    next_step,
                    email_id
                )
            finally:
                await conn.close()
        except Exception as exc:
            logger.error(json.dumps({"event": "db_update_failed", "error": str(exc), "email_id": email_id}))

    import asyncio
    asyncio.run(_async_update_email())

    return {
        "classification_result": result,
        "confidence":            confidence,
        "sentiment_score":       sentiment_score,
        "low_confidence_flag":   low_confidence_flag,
        "escalation_flag":       escalation_flag,
        "global_sla_deadline":   sla_deadline,
        "sla_deadline":          sla_deadline,  # also set for AG-05
        "escalated":             escalation_flag,
        "current_step":          next_step,
        "agent_statuses":        {**state.get("agent_statuses", {}), "AG-02": "completed"},
        "event_queue":           [audit],
        "error":                 None,
    }


def _audit_event(email_id: str, event_type: str, payload: dict) -> Dict[str, Any]:
    return {
        "type":      event_type,
        "agent_id":  "AG-02",
        "email_id":  email_id,
        "timestamp": datetime.utcnow().isoformat(),
        "payload":   payload,
    }
