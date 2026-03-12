"""
state/shared_state.py — LangGraph Shared State Definition
Exact variable names from design doc. All 8 agents.
"""
from __future__ import annotations
from typing import Annotated, Any, Dict, List, Optional
import operator
from datetime import datetime


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
    current_step:       str                    # e.g. 'intake', 'classification', 'routing'
    agent_statuses:     Dict[str, str]         # {'AG-01': 'completed', 'AG-02': 'running', ...}
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
    sla_deadline:       Optional[datetime]   # hard deadline for resolution
    sla_timer_started:  bool                 # True once monitoring begins (ST-E1-05)
    elapsed_time:       float                # seconds elapsed since intake
    alert_80_sent:      bool                 # True once 80% threshold Slack alert sent
    escalated:          bool                 # True once SLA breached → escalated
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
    error:              Optional[str]    # last error message, cleared on success
    case_reference:     Optional[str]   # CASE-{YYYYMMDD}-{uuid[:6]}
