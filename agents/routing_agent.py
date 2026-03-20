"""
agents/routing_agent.py — AG-03: Routing Agent
Sprint 6.

SIMPLIFIED (Phase 1):
  - ServiceNow, Jira, Freshdesk ticket creation removed → Phase 2
  - Post-routing: log decision to postgres + move Gmail folder only
  - CRM syncs: Phase 2

Phase 2 items tagged with: # TODO: Phase 2 — <tool>

EXACT DESIGN (master prompt + design doc):

Step 1 — Rule-based matrix (deterministic, no retry):
  Maps email category → team from domain_config['routing_rules']

Step 2 — LLM fallback (Gemini 2.5 Flash-Lite, 2x retry ONLY):
  Used only when Step 1 has no rule match.
  On persistent failure → escalate to Team Lead queue.

Step 3 — Post-routing actions (Phase 1 scope):
  1. email.gmail_move_to_folder → move email to team folder (via mcp.py)
  2. Write routing_decision + reason → postgres audit trail

ACCEPTANCE CRITERIA:
  ✅ 95%+ routing accuracy
  ✅ Every decision logged with reason in postgres
  ✅ Completes within 15 seconds end-to-end
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from config.settings import settings
from mcp_tools.llm_client import LLMProvider, call_llm
from prompts.routing_prompt import build_routing_prompts
from state.shared_state import AgentState
from agents.agent_metrics import instrument_agent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Ticket system constants (kept for Phase 2 routing matrix metadata)
# ---------------------------------------------------------------------------
_JIRA       = "jira"
_SERVICENOW = "servicenow"
_FRESHDESK  = "freshdesk"

# ---------------------------------------------------------------------------
# Rule matrix: category → routing metadata
# team name always resolved from domain_config['routing_rules'] at runtime
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Semantic intent → Gmail label path mapping
# Used when category is not in domain routing_rules.
# Covers all LLM output variants — no keyword matching needed.
# ---------------------------------------------------------------------------
_SEMANTIC_LABEL_MAP: Dict[str, str] = {
    "hr":                   "HR/HR Operations",
    "hr_issue":             "HR/HR Operations",
    "leave":                "HR/HR Operations",
    "leave_request":        "HR/HR Operations",
    "employee_policy":      "HR/HR Operations",
    "grievance":            "HR/HR Operations",
    "harassment":           "HR/HR Operations",
    "policy_clarification": "HR/HR Operations",
    "benefits_query":       "HR/HR Operations",
    "offboarding":          "HR/HR Operations",
    "payroll":              "HR/Payroll Team",
    "payroll_query":        "HR/Payroll Team",
    "salary_issue":         "HR/Payroll Team",
    "salary":               "HR/Payroll Team",
    "salary_query":         "HR/Payroll Team",
    "recruitment":          "HR/Recruitment Team",
    "hiring":               "HR/Recruitment Team",
    "headcount":            "HR/Recruitment Team",
    "interview":            "HR/Recruitment Team",
    "offer_letter":         "HR/Employee Relations",
    "employee_relations":   "HR/Employee Relations",
    "appraisal":            "HR/Employee Relations",
    "it":                   "IT Support/General IT Queue",
    "password_reset":       "IT Support/General IT Queue",
    "software_bug":         "IT Support/General IT Queue",
    "hardware_issue":       "IT Support/General IT Queue",
    "software_issue":       "IT Support/General IT Queue",
    "access_denied":        "IT Support/General IT Queue",
    "access_request":       "IT Support/Security Team",
    "security_incident":    "IT Support/Security Team",
    "network_issue":        "IT Support/Network Ops Team",
    "vpn_issue":            "IT Support/Network Ops Team",
    "connectivity":         "IT Support/Network Ops Team",
    "onboarding":           "HR/Recruitment Team",
    "general_query":        "IT Support/General IT Queue",
    "billing":              "Customer Support/Customer Issues",
    "invoice":              "Customer Support/Customer Issues",
    "payment":              "Customer Support/Customer Issues",
    "refund_request":       "Customer Support/Customer Issues",
    "overcharge":           "Customer Support/Customer Issues",
    "complaint":            "Customer Support/Customer Issues",
    "query":                "Customer Support/Customer Issues",
    "info_request":         "Customer Support/Customer Issues",
    "escalation":           "Customer Support/Customer Issues",
    "product_support":      "Customer Support/Product Support",
    "product_issue":        "Customer Support/Product Support",
    "warranty":             "Customer Support/Warranty",
    "warranty_claim":       "Customer Support/Warranty",
    "other":                "Others/Uncategorised",
    "others":               "Others/Uncategorised",
    "spam":                 "Others/Uncategorised",
    "unknown":              "Others/Uncategorised",
}


_RULE_MATRIX: Dict[str, Dict[str, Any]] = {
    # --- Billing ---
    "billing":              {"ticket": _SERVICENOW, "team_lead": False},
    "invoice_dispute":      {"ticket": _SERVICENOW, "team_lead": False},
    "payment_failure":      {"ticket": _SERVICENOW, "team_lead": False},
    "overcharge":           {"ticket": _SERVICENOW, "team_lead": False},
    "refund_request":       {"ticket": _SERVICENOW, "team_lead": False},
    "general_billing":      {"ticket": _FRESHDESK,  "team_lead": False},
    "payment_confirmation": {"ticket": _FRESHDESK,  "team_lead": False},
    "tax_query":            {"ticket": _SERVICENOW, "team_lead": False},
    "subscription_change":  {"ticket": _SERVICENOW, "team_lead": False},

    # --- IT Tier 2 ---
    "hardware_issue":       {"ticket": _JIRA, "team_lead": False},
    "software_bug":         {"ticket": _JIRA, "team_lead": False},
    "network_issue":        {"ticket": _JIRA, "team_lead": False},
    "security_incident":    {"ticket": _JIRA, "team_lead": True},
    "technical_issue":      {"ticket": _JIRA, "team_lead": False},

    # --- IT Tier 1 ---
    "password_reset":       {"ticket": _JIRA,      "team_lead": False},
    "access_request":       {"ticket": _JIRA,      "team_lead": False},
    "onboarding":           {"ticket": _SERVICENOW, "team_lead": False},
    "general_query":        {"ticket": _FRESHDESK,  "team_lead": False},

    # --- HR ---
    "leave_request":        {"ticket": _SERVICENOW, "team_lead": False},
    "payroll_query":        {"ticket": _SERVICENOW, "team_lead": False},
    "benefits_query":       {"ticket": _SERVICENOW, "team_lead": False},
    "policy_clarification": {"ticket": _SERVICENOW, "team_lead": False},
    "offboarding":          {"ticket": _SERVICENOW, "team_lead": False},
    "grievance":            {"ticket": _SERVICENOW, "team_lead": True},
    "recruitment":          {"ticket": _SERVICENOW, "team_lead": False},

    # --- Escalation / complaint ---
    "complaint":            {"ticket": _SERVICENOW, "team_lead": True},
    "escalation":           {"ticket": _SERVICENOW, "team_lead": True},

    # --- Customer Service ---
    "inquiry":              {"ticket": _FRESHDESK, "team_lead": False},
    "info_request":         {"ticket": _FRESHDESK, "team_lead": False},
    "query":                {"ticket": _FRESHDESK, "team_lead": False},

    # --- Healthcare ---
    "appointment":              {"ticket": _SERVICENOW, "team_lead": False},
    "prescription_refill":      {"ticket": _SERVICENOW, "team_lead": False},
    "lab_result":               {"ticket": _SERVICENOW, "team_lead": True},
    "insurance_query":          {"ticket": _FRESHDESK,  "team_lead": False},
    "emergency":                {"ticket": _SERVICENOW, "team_lead": True},
    "medical_record_request":   {"ticket": _SERVICENOW, "team_lead": False},

    # --- Legal ---
    "contract_review":      {"ticket": _SERVICENOW, "team_lead": True},
    "dispute":              {"ticket": _SERVICENOW, "team_lead": True},
    "regulatory_filing":    {"ticket": _SERVICENOW, "team_lead": True},
    "consultation_request": {"ticket": _SERVICENOW, "team_lead": True},
    "nda_request":          {"ticket": _SERVICENOW, "team_lead": True},
    "litigation":           {"ticket": _SERVICENOW, "team_lead": True},
    "general_legal_query":  {"ticket": _SERVICENOW, "team_lead": False},

    # --- E-Commerce ---
    "order_status":         {"ticket": _FRESHDESK,  "team_lead": False},
    "return_request":       {"ticket": _FRESHDESK,  "team_lead": False},
    "delivery_issue":       {"ticket": _SERVICENOW, "team_lead": False},
    "product_query":        {"ticket": _FRESHDESK,  "team_lead": False},
    "account_issue":        {"ticket": _JIRA,       "team_lead": False},
    "discount_query":       {"ticket": _FRESHDESK,  "team_lead": False},
    "fraud_report":         {"ticket": _SERVICENOW, "team_lead": True},

    # --- Education ---
    "enrolment_query":          {"ticket": _FRESHDESK,  "team_lead": False},
    "fee_payment":              {"ticket": _SERVICENOW, "team_lead": False},
    "academic_record":          {"ticket": _SERVICENOW, "team_lead": True},
    "course_information":       {"ticket": _FRESHDESK,  "team_lead": False},
    "student_support":          {"ticket": _SERVICENOW, "team_lead": False},
    "library_access":           {"ticket": _FRESHDESK,  "team_lead": False},
    "accommodation_request":    {"ticket": _SERVICENOW, "team_lead": False},
}


# ---------------------------------------------------------------------------
# Step 1 — Rule-based routing
# ---------------------------------------------------------------------------

def _rule_based_route(
    category: str,
    domain_config: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Deterministic rule lookup. Returns None if category not in static matrix
    (so caller can try LLM fallback next).
    Team name resolved from domain_config['routing_teams'/'routing_rules'].
    For known categories on unknown domains, _resolve_team returns 'Team Lead'.
    """
    rule = _RULE_MATRIX.get(category)
    if not rule:
        return None  # Not in static matrix — let LLM try

    team, reason = _resolve_team(category, domain_config)
    return {
        "team":               team,
        "ticket_system":      rule["ticket"],
        "team_lead_required": rule["team_lead"],
        "source":             "rule_matrix",
        "reason":             reason,
    }


def _resolve_team(
    category: str,
    domain_config: Optional[Dict[str, Any]],
) -> tuple[str, str]:
    """
    Resolve team name from domain_config['routing_teams'].
    Falls back to 'Team Lead' for unknown email type OR unknown domain.
    Returns (team, reason).
    """
    if domain_config:
        # Primary: routing_rules → exact Gmail label path
        routing_rules = domain_config.get("routing_rules", {})
        if isinstance(routing_rules, dict):
            team = routing_rules.get(category)
            if team:
                return team, f"domain routing_rules['{category}']"
        # Secondary: routing_teams dict
        routing_teams = domain_config.get("routing_teams", {})
        if isinstance(routing_teams, dict):
            team = routing_teams.get(category)
            if team:
                return team, f"domain routing_teams['{category}']"

    # Semantic fallback — covers all LLM output variants
    if category in _SEMANTIC_LABEL_MAP:
        label = _SEMANTIC_LABEL_MAP[category]
        logger.info(json.dumps({
            "event":    "routing_semantic_match",
            "category": category,
            "label":    label,
        }))
        return label, f"semantic_label_map['{category}']"

    # Final fallback — unknown category → uncategorised, never Team Lead
    logger.warning(json.dumps({
        "event":    "routing_unknown_category",
        "category": category,
        "action":   "routing to Others/Uncategorised",
    }))
    return "Others/Uncategorised", f"Unknown category '{category}'"


# ---------------------------------------------------------------------------
# Step 2 — LLM fallback (Gemini 2.5 Flash-Lite, 2x retry ONLY)
# ---------------------------------------------------------------------------

def _llm_fallback_route(
    classification: Dict[str, Any],
    domain_config: Optional[Dict[str, Any]],
    email_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Gemini 2.5 Flash-Lite fallback. Exactly 2 retries (locked from design doc).
    Returns None if both attempts fail → caller escalates to Team Lead.
    """
    max_retries = settings.ROUTING_LLM_FALLBACK_RETRIES  # = 2, locked

    if domain_config:
        sys_prompt, usr_prompt = build_routing_prompts(domain_config)
    else:
        sys_prompt = (
            "You are a routing specialist. Return JSON only: "
            "{\"routing_decision\": \"<team>\", \"confidence\": <float>, \"reason\": \"<str>\"}"
        )
        usr_prompt = "Route this email: {classification_json}"

    classification_json = json.dumps(classification, default=str)

    for attempt in range(1, max_retries + 1):
        try:
            # FIX: switched from Gemini (429 daily quota exhausted) to Groq
            raw = call_llm(
                provider=LLMProvider.GROQ,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user",   "content": str(usr_prompt).format(
                        classification_json=classification_json
                    )},
                ],
                temperature=0.1,
                max_tokens=256,
                model_override="llama-3.1-8b-instant",
            )

            result     = json.loads(raw.strip())
            team       = result.get("routing_decision", "")
            confidence = float(result.get("confidence", 0.0))
            reason     = result.get("reason", "")

            # Validate team name against domain config
            if domain_config:
                valid_teams = domain_config.get("routing_teams", [])  # type: ignore
                if valid_teams and team not in valid_teams:
                    logger.warning(json.dumps({
                        "event":    "llm_routing_invalid_team",
                        "team":     team,
                        "valid":    valid_teams,
                        "attempt":  attempt,
                        "email_id": email_id,
                    }))
                    if attempt < max_retries:
                        continue
                    return None  # exhausted retries

            logger.info(json.dumps({
                "event":      "llm_routing_success",
                "team":       team,
                "confidence": confidence,
                "attempt":    attempt,
                "email_id":   email_id,
            }))

            return {
                "team":               team,
                "ticket_system":      _SERVICENOW,
                "team_lead_required": confidence < 0.6,
                "source":             "llm_fallback",
                "reason":             reason,
                "llm_confidence":     confidence,
            }

        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.warning(json.dumps({
                "event":    "llm_routing_parse_error",
                "error":    str(exc),
                "attempt":  attempt,
                "email_id": email_id,
            }))
        except Exception as exc:
            logger.error(json.dumps({
                "event":    "llm_routing_error",
                "error":    str(exc),
                "attempt":  attempt,
                "email_id": email_id,
            }))

    return None  # both retries exhausted


# ---------------------------------------------------------------------------
# Step 3a — Gmail move to folder (via existing mcp.py)
# ---------------------------------------------------------------------------

def _move_to_gmail_folder(email_id: str, team: str) -> bool:
    """
    Calls email.gmail_move_to_folder via the Enterprise MCP Server.
    Non-blocking: routing succeeds even if move fails.
    """
    try:
        import asyncio
        from app.domains.email_ai import tools_email as email_tools
        folder = _team_to_gmail_folder(team)
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                email_tools.gmail_move_to_folder(
                    message_ids=[email_id],
                    folder_label=folder,
                )
            )
        finally:
            loop.close()
        logger.info(json.dumps({
            "event":    "gmail_move_to_folder",
            "folder":   folder,
            "email_id": email_id,
        }))
        return True
    except Exception as exc:
        logger.warning(json.dumps({
            "event":    "gmail_move_failed_non_blocking",
            "error":    str(exc),
            "email_id": email_id,
        }))
        return False


def _team_to_gmail_folder(team: str) -> str:
    """Map team name to Gmail label. Default: use team name directly."""
    mapping = {
        "Finance Ops":           "Finance",
        "Tier 1 Support":        "IT-Tier1",
        "Tier 2 Engineering":    "IT-Tier2",
        "HR Ops":                "HR",
        "Customer Service":      "CustomerService",
        "Customer Service Lead": "Escalations",
        "Triage Nurse":          "Healthcare-Triage",
        "Billing Dept":          "Healthcare-Billing",
        "Appointments Desk":     "Healthcare-Appointments",
        "Litigation Team":       "Legal-Litigation",
        "General Counsel":       "Legal-General",
        "Returns & Refunds":     "Returns",
        "Fraud Prevention":      "Fraud",
    }
    return mapping.get(team, team.replace(" ", "-"))


# ---------------------------------------------------------------------------
# Step 3b — Postgres audit write
# ---------------------------------------------------------------------------

def _write_routing_to_db(
    email_id:         str,
    routing_decision: Dict[str, Any],
    assignment_id:    Optional[str],
    tenant_id:        Optional[str],
) -> None:
    """
    Write routing decision + reason to postgres.
    Phase 1: structured JSON log (asyncpg wired in Week 3 per master prompt).
    AG-06 event_queue provides the guaranteed delivery (infinite retry).

    # TODO: Phase 2 — servicenow-mcp: create ServiceNow incident ticket
    # TODO: Phase 2 — jira-mcp: create Jira issue for IT/Engineering types
    # TODO: Phase 2 — freshdesk-mcp: tag ticket and set assignment group
    """
    logger.info(json.dumps({
        "event":           "routing_decision_logged",
        "email_id":        email_id,
        "team":            routing_decision.get("team"),
        "reason":          routing_decision.get("routing_reason"),
        "ticket_system":   routing_decision.get("ticket_system"),  # metadata only Phase 1
        "assignment_id":   assignment_id,
        "source":          routing_decision.get("source"),
        "tenant_id":       tenant_id,
        "timestamp":       datetime.now(timezone.utc).isoformat(),
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
                        routing_decision = $1,
                        assignment_id = $2,
                        current_step = 'response',
                        current_assignee = $1
                    WHERE email_id = $3::uuid
                    """,
                    routing_decision.get("team"),
                    assignment_id,
                    email_id
                )
            finally:
                await conn.close()
        except Exception as exc:
            logger.error(json.dumps({"event": "db_routing_update_failed", "error": str(exc), "email_id": email_id}))

    import asyncio
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_async_update_email())
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# AG-03 Main LangGraph Node
# ---------------------------------------------------------------------------

@instrument_agent("AG-03")
def routing_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node for AG-03.

    Reads from state:
        classification_result, parsed_email, domain_config,
        case_reference, tenant_id

    Writes to state (exact names from design doc Section 1.4):
        classification, routing_matrix, routing_decision,
        assignment_id, current_step, agent_statuses, event_queue
    """
    start_time     = time.monotonic()
    classification = state.get("classification_result") or {}
    parsed         = state.get("parsed_email") or {}
    domain_config  = state.get("domain_config")
    case_reference = state.get("case_reference", "")
    tenant_id      = state.get("tenant_id", "default")

    email_id: str = parsed.get("email_id") or state.get("email_id") or "unknown"
    category = classification.get("category", "")
    priority = classification.get("priority", "medium")

    logger.info(json.dumps({
        "event":    "routing_started",
        "email_id": email_id,
        "category": category,
        "priority": priority,
        "domain":   (domain_config or {}).get("domain_id", "unknown"),
    }))

    # =========================================================================
    # STEP 1 — Rule-based matrix (deterministic, no retry)
    # =========================================================================
    route_info = _rule_based_route(category, domain_config)

    if route_info:
        logger.info(json.dumps({
            "event":    "routing_rule_match",
            "category": category,
            "team":     route_info["team"],
            "email_id": email_id,
        }))

    # =========================================================================
    # STEP 2 — LLM fallback (Gemini 2.5 Flash-Lite, 2x retry ONLY)
    # =========================================================================
    if not route_info:
        logger.info(json.dumps({
            "event":    "routing_no_rule_match",
            "category": category,
            "email_id": email_id,
            "fallback": "llm",
        }))
        route_info = _llm_fallback_route(classification, domain_config, email_id)

        if not route_info:
            # Both retries exhausted → Team Lead escalation
            logger.error(json.dumps({
                "event":    "routing_llm_exhausted_escalating",
                "email_id": email_id,
                "category": category,
            }))
            team_lead_team = _get_team_lead_team(domain_config)
            route_info = {
                "team":               team_lead_team,
                "ticket_system":      _SERVICENOW,
                "team_lead_required": True,
                "source":             "team_lead_escalation",
                "reason":             "No rule match + LLM fallback failed after 2 retries",
            }

    team           = route_info["team"]
    routing_reason = route_info.get(
        "reason",
        f"Rule match for category '{category}'"
    )

    # =========================================================================
    # STEP 3 — Post-routing actions (Phase 1 scope)
    # =========================================================================

    # 3.1 Move email to team folder in Gmail (via existing mcp.py)
    # 3.1 Move email to team folder in Gmail (via existing mcp.py)
    # BUG FIX: Disabled this call. It was taking the routing Team (e.g. "Finance Ops")
    # and mapping it to new unapproved tags (like "Finance", "HR", "IT-Tier1") which 
    # Gmail auto-created. Labels should strictly come from classification output.
    # _move_to_gmail_folder(email_id=email_id, team=str(team))

    # TODO: Phase 2 — servicenow-mcp: _create_servicenow_ticket(...)
    # TODO: Phase 2 — jira-mcp:       _create_jira_ticket(...)
    # TODO: Phase 2 — freshdesk-mcp:  _tag_freshdesk(...)

    # 3.2 Write routing decision to postgres audit trail
    assignment_id   = None   # TODO: Phase 2 — set to ServiceNow/Jira ticket ID
    routing_decision_obj = {
        "team":           team,
        "assignee":       team,
        "gmail_label":    team,   # Gmail label path for apply_label_node
        "queue_id":       assignment_id,
        "routing_reason": routing_reason,
        "timestamp":      datetime.now(timezone.utc).isoformat(),
        "source":         route_info.get("source", "rule_matrix"),
        "category":       category,
        "ticket_system":  route_info.get("ticket_system"),  # metadata for Phase 2
    }

    _write_routing_to_db(
        email_id=email_id,
        routing_decision=routing_decision_obj,
        assignment_id=assignment_id,
        tenant_id=tenant_id,
    )

    # =========================================================================
    # Timing check
    # =========================================================================
    elapsed = time.monotonic() - start_time
    if elapsed > settings.ROUTING_TIMEOUT_SECONDS:
        logger.warning(json.dumps({
            "event":           "routing_timeout_exceeded",
            "elapsed_seconds": float(int(elapsed * 100) / 100.0),
            "limit_seconds":   settings.ROUTING_TIMEOUT_SECONDS,
            "email_id":        email_id,
        }))

    # =========================================================================
    # Audit event for AG-06 (never-drop guarantee)
    # =========================================================================
    audit_event = {
        "type":      "email_routed",
        "agent_id":  "AG-03",
        "email_id":  email_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {
            "team":            team,
            "assignment_id":   assignment_id,
            "routing_reason":  routing_reason,
            "source":          route_info.get("source"),
            "elapsed_seconds": float(int(elapsed * 100) / 100.0),
            "tenant_id":       tenant_id,
        },
    }

    logger.info(json.dumps({
        "event":    "routing_completed",
        "email_id": email_id,
        "team":     team,
        "elapsed_s": float(int(elapsed * 100) / 100.0),
    }))

    return {
        # Exact state variable names from design doc Section 1.4
        "classification":   classification,
        "routing_matrix":   _build_routing_matrix_snapshot(domain_config),
        "routing_decision": routing_decision_obj,
        "assignment_id":    assignment_id,
        # Orchestrator control
        "current_step":    "response",
        "agent_statuses":  {**state.get("agent_statuses", {}), "AG-03": "completed"},
        "event_queue":     [audit_event],
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_team_lead_team(domain_config: Optional[Dict[str, Any]]) -> str:
    """Return the Team Lead escalation team for the current domain."""
    if not domain_config:
        return "Customer Service Lead"
    teams = domain_config.get("routing_teams", [])
    for team in teams:
        if any(kw in team.lower() for kw in ("lead", "triage", "escalation", "counsel", "general")):
            return team
    return teams[0] if teams else "Customer Service Lead"


def _build_routing_matrix_snapshot(domain_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Snapshot of the routing matrix used — stored in state for AG-07 analytics."""
    if domain_config:
        return {
            "domain_id":     domain_config.get("domain_id", "unknown"),
            "routing_rules": domain_config.get("routing_rules", {}),
            "routing_teams": domain_config.get("routing_teams", []),
        }
    return {"domain_id": "default", "routing_rules": {}, "routing_teams": []}