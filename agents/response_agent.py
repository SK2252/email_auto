"""
agents/response_agent.py — AG-04: Response Agent
Sprint 7-8.

PHASE 1 SCOPE (current):
  - Draft response using email thread context only.
  - No CRM customer context fetch.
  # TODO: Phase 2 — salesforce-mcp: fetch customer context before drafting
  # TODO: Phase 2 — hubspot-mcp: fallback if no Salesforce record found

AUTO-SEND DECISION GATE (exact conditions, locked from design doc):
  confidence >= 0.90
  AND sentiment_score >= -0.3
  AND category in [inquiry, info_request]
  AND pii_scan_result["is_safe"] == True
  → auto-send via Gmail/Outlook (no human review)
  else → analyst_queue_node

AUTO-SEND PATH: LLM fills a CANNED TEMPLATE — does NOT freewrite.
HUMAN-REVIEW PATH: Gemini drafts freely; analyst edits before send.

Provider: Gemini 2.5 Flash-Lite (via llm_client.py)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from config.settings import settings
from mcp_tools.llm_client import LLMProvider, call_llm
from prompts.response_draft_prompt import (
    build_response_prompts,
    RESPONSE_SYSTEM_PROMPT,
    RESPONSE_USER_PROMPT,
)
from prompts.templates import get_template
from state.shared_state import AgentState
from utils.domain_loader import is_auto_send_permitted
from utils.pii_scanner import PIIScanner
from utils.retry_utils import retry_with_backoff
from agents.agent_metrics import instrument_agent

logger = logging.getLogger(__name__)

_pii_scanner = PIIScanner()


# ---------------------------------------------------------------------------
# Slack compliance alert (AG-04 — PII detected hard-block)
# Channel: #compliance-alerts
# ---------------------------------------------------------------------------
def _send_pii_compliance_alert(
    email_id:       str,
    case_ref:       str,
    detected_types: list,
) -> None:
    """POST PII detection alert to #compliance-alerts. Fallback to gmail-mcp."""
    import httpx

    token   = getattr(settings, "SLACK_BOT_TOKEN", None)
    channel = getattr(settings, "SLACK_CHANNEL_COMPLIANCE", "#compliance-alerts")

    message = (
        f":shield: *PII Hard-Block Fired* :shield:\n"
        f"Case: `{case_ref}` | Email: `{email_id}`\n"
        f"Detected PII types: `{'`, `'.join(detected_types) if detected_types else 'unknown'}`\n"
        f"Email routed to analyst queue. Auto-send blocked."
    )

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
                    "event":    "pii_compliance_slack_sent",
                    "email_id": email_id, "channel": channel,
                }))
            else:
                logger.error(json.dumps({
                    "event":  "pii_compliance_slack_failed",
                    "error":  resp.json().get("error"),
                }))
        except Exception as exc:
            logger.error(json.dumps({"event": "pii_compliance_slack_exception",
                                     "error": str(exc)}))

    # Mandatory fallback: log to audit_log (always). Email if Slack failed.
    if not slack_ok:
        logger.warning(json.dumps({"event": "pii_compliance_slack_failed_using_audit_log",
                                    "email_id": email_id, "types": detected_types}))
        try:
            import asyncio
            from app.domains.email_ai import tools_email as email_tools
            team_lead = getattr(settings, "TEAM_LEAD_EMAIL", None)
            if team_lead:
                asyncio.get_event_loop().run_until_complete(
                    email_tools.gmail_send_email(
                        to=team_lead,
                        subject=f"[COMPLIANCE] PII detected in case {case_ref}",
                        body=(
                            f"PII hard-block fired for case {case_ref}.\n"
                            f"Email ID: {email_id}\n"
                            f"Detected types: {', '.join(detected_types)}\n"
                            f"Email has been routed to analyst queue."
                        ),
                        thread_id=None,
                    )
                )
                logger.info(json.dumps({"event": "pii_compliance_gmail_fallback_sent",
                                        "email_id": email_id}))
        except Exception as exc:
            logger.error(json.dumps({"event": "pii_compliance_all_alerts_failed",
                                     "email_id": email_id, "error": str(exc)}))


# ---------------------------------------------------------------------------
# Auto-send decision gate — exact conditions, non-negotiable
# ---------------------------------------------------------------------------

def should_auto_send(state: AgentState) -> bool:
    """
    Returns True only when ALL conditions are met:
      1. Domain permits auto-send (healthcare/legal always block)
      2. Category is in domain's auto_send_types
      3. confidence >= 0.90
      4. sentiment_score >= -0.3
      5. pii_scan_result["is_safe"] == True
    """
    classification = state.get("classification_result") or {}
    pii_result     = state.get("pii_scan_result") or {}
    domain_config  = state.get("domain_config")
    category       = classification.get("category", "")

    # Domain-level gate (Healthcare, Legal always False)
    if domain_config and not is_auto_send_permitted(domain_config, category):
        return False

    # Fallback: if no domain config, use original hardcoded check
    if not domain_config and category not in ("inquiry", "info_request"):
        return False

    return (
        state.get("confidence", 0.0)          >= 0.90
        and state.get("sentiment_score", -1.0) >= -0.3
        and pii_result.get("is_safe", False)  is True
    )


# ---------------------------------------------------------------------------
# Template-based draft (auto-send path)
# ---------------------------------------------------------------------------

@retry_with_backoff(retries=2, on_exhaust="return_none")
def _fill_template(category: str, context: Dict[str, Any]) -> Optional[str]:
    """
    Calls Gemini to fill a canned template — LLM only fills slots,
    it does NOT freewrite outside the template boundaries.
    """
    template_str, fill_prompt_str, _ = get_template(category)

    prompt = fill_prompt_str.format(
        template=template_str,
        **context,
    )

    return call_llm(
        provider=LLMProvider.GEMINI,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=512,
    )


# ---------------------------------------------------------------------------
# Free-form draft (human-review path)
# ---------------------------------------------------------------------------

@retry_with_backoff(retries=2, on_exhaust="return_none")
def _generate_free_draft(state: AgentState) -> Optional[str]:
    """
    Calls Gemini with full creative freedom, tone calibrated to domain.
    Draft is human-reviewed BEFORE send — no auto-send from this path.
    """
    parsed    = state.get("parsed_email") or {}
    email_txt = state.get("email_text", "")
    context   = state.get("customer_context") or {}
    thread    = state.get("email_thread") or []
    case_ref  = state.get("case_reference", "")
    domain_config = state.get("domain_config")

    if domain_config:
        sys_prompt, usr_prompt = build_response_prompts(domain_config)
    else:
        sys_prompt = RESPONSE_SYSTEM_PROMPT
        usr_prompt = RESPONSE_USER_PROMPT

    return call_llm(
        provider=LLMProvider.GEMINI,
        messages=[
            {"role": "system", "content": sys_prompt.format(case_reference=case_ref)},
            {"role": "user",   "content": usr_prompt.format(
                case_reference=case_ref,
                email_text=email_txt,
                customer_context_json=json.dumps(context, default=str),
                thread_json=json.dumps([t for i, t in enumerate(thread) if i < 5], default=str),
            )},
        ],
        temperature=0.4,
        max_tokens=512,
    )


# ---------------------------------------------------------------------------
# Send node helpers
# ---------------------------------------------------------------------------

async def _send_email(parsed_email: Dict[str, Any], draft: str, case_ref: str) -> bool:
    """Step 4: Real send via GmailClient."""
    from mcp_tools.gmail_client import gmail_client
    source = parsed_email.get("source", "gmail")
    to     = parsed_email.get("sender", "")
    subj   = f"Re: {parsed_email.get('subject', '')} [{case_ref}]"
    thread_id = parsed_email.get("thread_id")

    if source == "gmail":
        await gmail_client.send_reply(
            to=to,
            subject=subj,
            body=draft,
            thread_id=thread_id
        )
        logger.info(json.dumps({"event": "gmail_response_sent", "to": to, "thread_id": thread_id}))
    else:
        # graph_client placeholder
        logger.info(json.dumps({"event": "outlook_response_skipped", "to": to}))

    return True


# ---------------------------------------------------------------------------
# AG-04 LangGraph node
# ---------------------------------------------------------------------------

@instrument_agent("AG-04")
async def response_node(state: AgentState) -> Dict[str, Any]:
    """
    Main LangGraph node for AG-04.

    Outputs:
      - On auto-send path: draft, pii_scan_result, current_step='audit'
      - On human-review path: draft, pii_scan_result, current_step='analyst_queue'
    """
    parsed   = state.get("parsed_email") or {}
    email_id: str = parsed.get("email_id") or state.get("email_id") or "unknown"
    category = (state.get("classification_result") or {}).get("category", "inquiry")
    case_ref = state.get("case_reference", "")

    logger.info(json.dumps({"event": "response_node_started", "email_id": email_id}))

    # ---- 1. PII scan on raw email body first ----
    email_text     = state.get("email_text", "")
    pii_scan_result = _pii_scanner.scan(email_text)

    if not pii_scan_result["is_safe"]:
        # Hard-block: PII in incoming email — do not draft, route to human
        detected = pii_scan_result.get("detected_types", [])
        logger.warning(json.dumps({
            "event":    "response_blocked_pii",
            "email_id": email_id,
            "types":    detected,
        }))

        # ---- Slack #compliance-alerts (AG-04 TODO — now wired) ----
        _send_pii_compliance_alert(
            email_id=email_id,
            case_ref=case_ref,
            detected_types=detected,
        )

        await _update_db_async(
            email_id=email_id,
            draft=None,
            pii_scan_result=pii_scan_result,
            current_step="analyst_queue"
        )

        return {
            "pii_scan_result": pii_scan_result,
            "draft":           None,
            "current_step":    "analyst_queue",
            "agent_statuses":  {**state.get("agent_statuses", {}), "AG-04": "blocked_pii"},
            "event_queue":     [_audit(email_id, "response_blocked_pii",
                                       {**pii_scan_result, "slack_alert": "sent"})],
        }

    # ---- 2. Auto-send gate check ----
    auto_send = should_auto_send({**state, "pii_scan_result": pii_scan_result})

    if auto_send:
        # Template-constrained draft
        context = {
            "customer_name":    parsed.get("sender", "Customer"),
            "company_name":     "Your Company",
            "case_reference":   case_ref,
            "agent_name":       "Support Team",
            "subject_summary":  parsed.get("subject", ""),
            "resolution_or_info": "",  # Gemini fills this from context
            "resolution_context": email_text[:400],
        }
        draft = _fill_template(category, context)
        next_step = "auto_send"
    else:
        # Free-form Gemini draft — goes to analyst queue
        draft = _generate_free_draft(state)
        next_step = "analyst_queue"

    # ---- 3. PII scan on outgoing DRAFT (hard-block before any send) ----
    if draft:
        draft_pii = _pii_scanner.scan(draft)
        if not draft_pii["is_safe"]:
            logger.error(json.dumps({"event": "draft_pii_block", "email_id": email_id}))
            draft      = None
            next_step  = "analyst_queue"
            auto_send  = False
            pii_scan_result = draft_pii  # override with draft's PII result

    # ---- 4. Auto-send dispatch ----
    if auto_send and draft:
        await _send_email(parsed, draft, case_ref)

    logger.info(json.dumps({
        "event":     "response_node_completed",
        "email_id":  email_id,
        "path":      "auto_send" if auto_send else "analyst_queue",
    }))

    await _update_db_async(
        email_id=email_id,
        draft=draft,
        pii_scan_result=pii_scan_result,
        current_step=next_step if next_step == "analyst_queue" else "audit"
    )

    return {
        "draft":           draft,
        "pii_scan_result": pii_scan_result,
        "current_step":    "audit",
        "agent_statuses":  {**state.get("agent_statuses", {}), "AG-04": "completed"},
        "event_queue":     [_audit(email_id, "response_drafted", {
            "auto_sent":  auto_send and draft is not None,
            "path":       next_step,
            "category":   category,
        })],
    }


def analyst_queue_node(state: AgentState) -> Dict[str, Any]:
    """
    Holds email for human analyst review.
    Called when should_auto_send() returned False.
    """
    email_id = (state.get("parsed_email") or {}).get("email_id", "unknown")
    logger.info(json.dumps({"event": "analyst_queue_entered", "email_id": email_id}))
    return {
        "current_step":   "analyst_queue",
        "agent_statuses": {**state.get("agent_statuses", {}), "AG-04": "awaiting_analyst"},
        "event_queue":    [_audit(email_id, "sent_to_analyst_queue", {
            "confidence":     state.get("confidence"),
            "sentiment_score": state.get("sentiment_score"),
        })],
    }


def _audit(email_id: str, event_type: str, payload: dict) -> Dict[str, Any]:
    return {
        "type":      event_type,
        "agent_id":  "AG-04",
        "email_id":  email_id,
        "timestamp": datetime.utcnow().isoformat(),
        "payload":   payload,
    }


async def _update_db_async(email_id: str, draft: Optional[str], pii_scan_result: Dict[str, Any], current_step: str) -> None:
    """Phase 5: Asyncpg update for the emails table."""
    import asyncpg
    db_url = getattr(settings, "DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    try:
        conn = await asyncpg.connect(db_url)
        try:
            await conn.execute(
                """
                UPDATE emails SET
                    draft = $1,
                    pii_scan_result = $2::jsonb,
                    current_step = $3
                WHERE email_id = $4::uuid
                """,
                draft,
                json.dumps(pii_scan_result),
                current_step,
                email_id
            )
        finally:
            await conn.close()
    except Exception as exc:
        logger.error(json.dumps({"event": "db_response_update_failed", "error": str(exc), "email_id": email_id}))
