"""
state/shared_state.py — LangGraph Shared State Definition
Exact variable names from design doc. All 8 agents.
"""
from __future__ import annotations
from typing import Annotated, Any, Dict, List, Optional
import operator
from datetime import datetime


# Reducer function for merging dictionaries from concurrent nodes
def merge_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two dictionaries, with b's values taking precedence."""
    result = a.copy() if a else {}
    if b:
        result.update(b)
    return result


# Reducer function for datetime — prefer first non-None value
def merge_datetime(a: Optional[datetime], b: Optional[datetime]) -> Optional[datetime]:
    """Merge two datetime values — prefer non-None first value."""
    return a if a is not None else b


# Reducer function for booleans — True takes precedence (logical OR)
def merge_bool(a: bool, b: bool) -> bool:
    """Merge two boolean values — True takes precedence."""
    return a or b


# Reducer function for optional strings — prefer first non-None value
def merge_str(a: Optional[str], b: Optional[str]) -> Optional[str]:
    """Merge two string values — prefer first non-None."""
    return a if a is not None else b


# ---------------------------------------------------------------------------
# Email schema: canonical format after normalization by AG-01
# ---------------------------------------------------------------------------
class EmailSchema(dict):
    """
    Typed alias for the normalized email payload.
    Keys: email_id, source, sender, subject, body, timestamp,
          attachments (List[str]), thread_id
    """


# ---------------------------------------------------------------------------
# Classification sub-type (returned by AG-02)
# ---------------------------------------------------------------------------
class ClassificationResult(dict):
    """
    Keys: category (str), priority (str), sla_bucket (str)
    May include: sentiment_score (float), confidence (float)
    """


# ---------------------------------------------------------------------------
# Full LangGraph State — TypedDict with ALL agent variable namespaces
# ---------------------------------------------------------------------------
from typing import TypedDict


class AgentState(TypedDict, total=False):
    # -----------------------------------------------------------------------
    # AG-00 — Global / Orchestrator
    # -----------------------------------------------------------------------
    email_id:           str                    # UUID of the email being processed
    current_step:       Annotated[str, merge_str]  # FIX: concurrent nodes write this — merge_str keeps first non-None
    agent_statuses:     Annotated[Dict[str, str], merge_dicts]  # merge dicts from concurrent nodes
    retry_count:        int                    # global retry counter
    global_sla_deadline: Optional[datetime]   # computed after classification

    # -----------------------------------------------------------------------
    # Multi-Domain / Multi-Tenant
    # -----------------------------------------------------------------------
    tenant_id:          str                    # identifies the client / tenant
    domain_config:      Dict[str, Any]         # loaded by domain_loader at AG-01 intake;
                                               # flows unchanged through entire pipeline
    escalation_flag:    bool                   # True when sentiment threshold breached

    # -----------------------------------------------------------------------
    # AG-01 — Intake
    # -----------------------------------------------------------------------
    raw_email:          Optional[Dict[str, Any]]   # raw payload from Gmail / Outlook / Zendesk
    parsed_email:       Optional[Dict[str, Any]]   # normalized EmailSchema dict
    attachment_paths:   List[str]                  # list of local/cloud storage paths
    ack_sent:           bool                       # True once auto-ACK email sent

    # -----------------------------------------------------------------------
    # AG-02 — Classification
    # -----------------------------------------------------------------------
    email_text:             str                          # body text fed to LLM
    classification_result:  Optional[Dict[str, Any]]     # ClassificationResult dict
    sentiment_score:        float                        # -1.0 to 1.0
    confidence:             float                        # 0.0 to 1.0
    low_confidence_flag:    bool                         # True when confidence < 0.7

    # -----------------------------------------------------------------------
    # AG-03 — Routing
    # -----------------------------------------------------------------------
    routing_matrix:     Dict[str, Any]    # rules table / LLM routing context
    routing_decision:   Optional[str]     # target team / queue name
    assignment_id:      Optional[str]     # ticket/issue ID in Jira / ServiceNow

    # -----------------------------------------------------------------------
    # AG-04 — Response
    # -----------------------------------------------------------------------
    email_thread:       List[Dict[str, Any]]  # conversation history
    customer_context:   Dict[str, Any]        # CRM data from Salesforce / HubSpot
    draft:              Optional[str]         # LLM-generated draft reply
    tone_score:         float                 # 0-1, politeness of draft
    pii_scan_result:    Dict[str, Any]        # {is_safe, detected_types, match_counts, llm_flag}
    analyst_edits:      Optional[str]         # human override text if in review

    # -----------------------------------------------------------------------
    # AG-05 — SLA
    # -----------------------------------------------------------------------
    sla_deadline:       Annotated[Optional[datetime], merge_datetime]  # hard deadline for resolution (set by classification or sla node)
    sla_timer_started:  Annotated[bool, merge_bool]              # True once monitoring begins (ST-E1-05)
    elapsed_time:       float                # seconds elapsed since intake
    alert_80_sent:      Annotated[bool, merge_bool]              # True once 80% threshold Slack alert sent
    escalated:          Annotated[bool, merge_bool]              # True once SLA breached → escalated
    current_assignee:   Optional[str]        # current owner of the ticket

    # -----------------------------------------------------------------------
    # AG-06 — Audit
    # -----------------------------------------------------------------------
    event_queue:        Annotated[List[Dict[str, Any]], operator.add]  # accumulates across nodes
    write_buffer:       List[Dict[str, Any]]  # local in-memory buffer when DB unavailable
    last_flush_time:    Optional[datetime]    # last successful flush to DB

    # -----------------------------------------------------------------------
    # AG-07 — Analytics
    # -----------------------------------------------------------------------
    kpi_snapshot:       Dict[str, Any]   # {total_ingested, avg_resolution_time, ...}
    trend_data:         Dict[str, Any]   # time-series delta vs previous period
    insight_text:       str              # LLM-generated insight paragraph
    report_timestamp:   Optional[datetime]

    # -----------------------------------------------------------------------
    # Cross-cutting
    # -----------------------------------------------------------------------
    error:              Annotated[Optional[str], merge_str]    # last error message, cleared on success
    case_reference:     Optional[str]   # CASE-{YYYYMMDD}-{uuid[:6]}