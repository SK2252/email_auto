"""
agents/orchestrator.py — AG-00: LangGraph StateGraph Orchestrator
Full wiring of all 7 agents.

PARALLEL EXECUTION DESIGN:
  After AG-02 Classification completes:
    → AG-03 Routing  }  run IN PARALLEL
    → AG-05 SLA      }  via LangGraph parallel branching

AG-06 Audit runs ASYNC (background thread via AuditWriter singleton).
AG-07 Analytics runs on SCHEDULE (not in main email flow).
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from langgraph.graph import END, StateGraph
from langgraph.types import Send

from agents.audit_agent import audit_node
from agents.classification_agent import classification_node
from agents.intake_agent import intake_node
from agents.routing_agent import routing_node    # AG-03 — replaces stub (Sprint 6)
from state.shared_state import AgentState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Stub nodes for agents built in later sprints
# These nodes return minimal valid state so the graph can run end-to-end today.
# ---------------------------------------------------------------------------

# routing_node is now imported from agents/routing_agent.py above.
# The Sprint 6 stub has been removed.


def sla_node(state: AgentState) -> Dict[str, Any]:
    """AG-05 — Sprint 9. Starts SLA timer. Can start in parallel with AG-02."""
    import datetime
    domain_config = state.get("domain_config")
    sla_deadline = state.get("sla_deadline")

    # If starting in parallel with AG-02, we don't have priority yet.
    # Set a default deadline from domain_config rules.
    if not sla_deadline and domain_config:
        rules = domain_config.get("sla_rules", {})
        # Pick 'medium' or the first available rule as the initial baseline
        default_rule = rules.get("medium") or (next(iter(rules.values())) if rules else {})
        if default_rule:
            seconds = default_rule.get("bucket_seconds", 86400) # fallback 24h
            sla_deadline = datetime.datetime.utcnow() + datetime.timedelta(seconds=seconds)

    logger.info(json.dumps({
        "event": "sla_node_started", 
        "deadline": str(sla_deadline),
        "parallel_start": state.get("sla_timer_started") is not True
    }))

    return {
        "sla_deadline":   sla_deadline,
        "sla_timer_started": True,
        "elapsed_time":   0.0,
        "alert_80_sent":  False,
        "escalated":      False,
        "agent_statuses": {**state.get("agent_statuses", {}), "AG-05": "running"},
        "event_queue":    [{
            "type": "sla_timer_started", "agent_id": "AG-05",
            "email_id": state.get("email_id"), "timestamp": datetime.datetime.utcnow().isoformat(),
            "payload": {"sla_deadline": str(sla_deadline)}
        }],
    }


def response_node(state: AgentState) -> Dict[str, Any]:
    """AG-04 — Sprint 7-8. Gemini draft + PII scan hard-block."""
    logger.info(json.dumps({"event": "response_node_stub", "email_id": state.get("email_id")}))
    return {
        "draft":          "[DRAFT PENDING — AG-04 Sprint 7-8]",
        "current_step":   "audit",
        "agent_statuses": {**state.get("agent_statuses", {}), "AG-04": "completed"},
    }


def human_review_node(state: AgentState) -> Dict[str, Any]:
    """Holds the email in a review queue when confidence < 0.7."""
    logger.info(json.dumps({
        "event":      "human_review_queued",
        "email_id":   state.get("email_id"),
        "confidence": state.get("confidence"),
    }))
    return {
        "current_step":   "human_review",
        "agent_statuses": {**state.get("agent_statuses", {}), "AG-00": "awaiting_human"},
    }


# ---------------------------------------------------------------------------
# Conditional edge functions
# ---------------------------------------------------------------------------

def route_after_intake(state: AgentState) -> str:
    """If intake errored and retry limit hit → DLQ, else → classification."""
    if state.get("error") and state.get("retry_count", 0) >= 3:
        return "dead_letter"
    return "classification"


def route_after_classification(state: AgentState) -> str:
    """Confidence < 0.7 → human review; otherwise → parallel fan-out."""
    if state.get("low_confidence_flag"):
        return "human_review"
    return "parallel_routing_sla"


def fan_out_after_intake(state: AgentState) -> List[Send]:
    """
    ST-E1-05: Fan out to Classification (AG-02) and SLA (AG-05) in parallel.
    SLA starts monitoring immediately while LLM classifies.
    """
    return [
        Send("classification", state),
        Send("sla",            state),
    ]


def fan_out_routing_only(state: AgentState) -> List[Send]:
    """
    After AG-02 completes, we fan out to AG-03 Routing.
    AG-05 is already running.
    """
    return [
        Send("routing", state),
    ]


def dead_letter_node(state: AgentState) -> Dict[str, Any]:
    """Records emails that exhausted all retries."""
    from utils.retry_utils import send_to_dead_letter_queue
    send_to_dead_letter_queue(
        {"email_id": state.get("email_id"), "error": state.get("error")},
        reason="max_retries_exceeded",
    )
    return {"current_step": "dead_letter", "agent_statuses": {**state.get("agent_statuses", {}), "AG-00": "dead_letter"}}


# ---------------------------------------------------------------------------
# Build and compile the graph
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    """
    Constructs the complete 8-node StateGraph.

    Flow:
      intake
        ↓ (conditional)
      classification ──── fan_out ──→ routing ─┐
                     └───────────→ sla      ─┤
                                             ↓
                                         response
                                             ↓
                                           audit
                                             ↓
                                            END
    """
    workflow = StateGraph(AgentState)

    # ---- Register all nodes ----
    workflow.add_node("intake",         intake_node)
    workflow.add_node("classification", classification_node)
    workflow.add_node("routing",        routing_node)
    workflow.add_node("sla",            sla_node)
    workflow.add_node("response",       response_node)
    workflow.add_node("audit",          audit_node)
    workflow.add_node("human_review",   human_review_node)
    workflow.add_node("dead_letter",    dead_letter_node)

def fan_out_after_intake(state: AgentState) -> List[Send] | str:
    """
    ST-E1-05: Fan out to Classification (AG-02) and SLA (AG-05) in parallel.
    SLA starts monitoring immediately while LLM classifies.
    Also handles route to dead_letter if intake failed.
    """
    if state.get("error") and state.get("retry_count", 0) >= 3:
        return "dead_letter"
    return [
        Send("classification", state),
        Send("sla",            state),
    ]


def build_graph() -> StateGraph:
    """
    Constructs the complete 8-node StateGraph.

    Flow:
      intake
        ↓ (parallel fan-out)
      {classification, sla} ────→ routing ─┐
                                         ↓
                                     bottom join → response
                                                ↓
                                              audit
                                                ↓
                                               END
    """
    workflow = StateGraph(AgentState)

    # ---- Register all nodes ----
    workflow.add_node("intake",         intake_node)
    workflow.add_node("classification", classification_node)
    workflow.add_node("routing",        routing_node)
    workflow.add_node("sla",            sla_node)
    workflow.add_node("response",       response_node)
    workflow.add_node("audit",          audit_node)
    workflow.add_node("human_review",   human_review_node)
    workflow.add_node("dead_letter",    dead_letter_node)

    # ---- Entry point ----
    workflow.set_entry_point("intake")

    # ---- intake → parallel [classification, sla] or dead_letter ----
    workflow.add_conditional_edges(
        "intake",
        fan_out_after_intake,
        {
            "classification": "classification",
            "sla":            "sla",
            "dead_letter":    "dead_letter",
        },
    )

    # ---- routing + sla → response ----
    workflow.add_edge("routing", "response")
    workflow.add_edge("sla",     "response")

    # ---- response → audit → END ----
    workflow.add_edge("response",     "audit")
    workflow.add_edge("audit",        END)

    # ---- terminal nodes ----
    workflow.add_edge("human_review", END)
    workflow.add_edge("dead_letter",  END)

    return workflow.compile()


# ---------------------------------------------------------------------------
# Public run function
# ---------------------------------------------------------------------------

# Compiled graph singleton
_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


async def run_pipeline(raw_email: dict, source: str = "gmail") -> Dict[str, Any]:
    """
    Entry point for processing a single email through the entire pipeline.

    Args:
        raw_email: Raw API payload from Gmail / Outlook / Zendesk / Freshdesk
        source:    String tag identifying the mail source

    Returns:
        Final AgentState dict after all nodes complete.
    """
    initial_state: AgentState = {
        "email_id":        "",
        "current_step":    "intake",
        "agent_statuses":  {},
        "retry_count":     0,
        "raw_email":       {**raw_email, "source": source},
        "attachment_paths": [],
        "ack_sent":        False,
        "event_queue":     [],
        "write_buffer":    [],
        "email_text":      "",
        "sentiment_score": 0.0,
        "confidence":      0.0,
        "low_confidence_flag": False,
        "elapsed_time":    0.0,
        "sla_timer_started": False,
        "alert_80_sent":   False,
        "escalated":       False,
        "tone_score":      0.0,
        "pii_scan_result": {},
        "kpi_snapshot":    {},
        "trend_data":      {},
        "insight_text":    "",
        "routing_matrix":  {},
        "email_thread":    [],
        "customer_context": {},
    }

    logger.info(json.dumps({"event": "pipeline_started", "source": source}))
    result = await get_graph().ainvoke(initial_state)
    logger.info(json.dumps({"event": "pipeline_completed", "step": result.get("current_step")}))
    return result
