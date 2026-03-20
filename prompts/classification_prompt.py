"""
prompts/classification_prompt.py — PROMPT-01 (Domain-Aware Router)
Single batched prompt for BOTH classification AND sentiment scoring.
One Groq API call = conserves 30 rpm free quota.

ARCHITECTURE:
  Each domain now has its own dedicated prompt file that returns
  EXACT Gmail sublabel paths directly — no alias_map lookup needed.

  Domain routing:
    it_support  → prompts/it_support_prompt.py
    hr          → prompts/hr_prompt.py
    billing     → prompts/customer_support_prompt.py
    default     → CLASSIFICATION_SYSTEM_PROMPT (generic fallback)

  The LLM now returns exact Gmail label paths:
    "HR/Payroll Team"              (not just "hr")
    "IT Support/Network Ops Team"  (not just "network_issue")
"""

# ---------------------------------------------------------------------------
# VALID TICKET TYPES
# ---------------------------------------------------------------------------
VALID_TICKET_TYPES = ["incident", "service_request", "change", "problem", "null"]

# ---------------------------------------------------------------------------
# VALID CATEGORIES — kept for backwards compatibility only
# classification_agent _NORM dict handles normalisation, not this list
# ---------------------------------------------------------------------------
VALID_CATEGORIES = [
    # Gmail label paths (returned directly by domain prompts)
    "IT Support/Network Ops Team",
    "IT Support/Security Team",
    "IT Support/General IT Queue",
    "HR/HR Operations",
    "HR/Payroll Team",
    "HR/Recruitment Team",
    "HR/Employee Relations",
    "Customer Support/Customer Issues/Priority 1",
    "Customer Support/Customer Issues/Priority 2",
    "Customer Support/Customer Issues/Priority 3",
    "Customer Support/Product Support",
    "Customer Support/Warranty",
    "Others/Uncategorised",
    # Short codes (returned by generic fallback prompt)
    "billing", "it", "hr", "complaint", "escalation",
    "query", "info_request", "general_query", "others",
]


# ---------------------------------------------------------------------------
# DOMAIN PROMPT ROUTER
# ---------------------------------------------------------------------------

def build_classification_prompts(domain_config: dict) -> tuple[str, str]:
    """
    Route to the correct domain-specific prompt based on domain_id.
    Returns (system_prompt, user_prompt) tuple.

    it_support → returns exact IT Support/* Gmail label paths
    hr         → returns exact HR/* Gmail label paths
    billing    → returns exact Customer Support/* Gmail label paths
    default    → generic prompt returning short category codes
    """
    domain_id = (domain_config or {}).get("domain_id", "default")

    if domain_id == "it_support":
        from prompts.it_support_prompt import build_it_support_prompts
        return build_it_support_prompts()

    if domain_id == "hr":
        from prompts.hr_prompt import build_hr_prompts
        return build_hr_prompts()

    if domain_id == "billing":
        from prompts.customer_support_prompt import build_customer_support_prompts
        return build_customer_support_prompts()

    # Unknown domain → generic fallback
    return CLASSIFICATION_SYSTEM_PROMPT, CLASSIFICATION_USER_PROMPT


# ---------------------------------------------------------------------------
# GENERIC FALLBACK PROMPT
# ---------------------------------------------------------------------------
CLASSIFICATION_SYSTEM_PROMPT = """
You are an expert email triage AI for a customer support inbox management system.
Classify the email, assess sentiment, and determine ticket status in ONE response.

Available categories (choose EXACTLY one):
  - billing      : invoices, charges, refunds, payments, pricing, GST
  - it           : VPN, password, system errors, software/hardware, access denied
  - hr           : leave, payroll, grievance, harassment, HR policy, benefits
  - complaint    : angry customer demanding action (refund, apology, cancellation)
  - query        : genuine business question about product, pricing, service
  - info_request : request for document, report, data, API docs, compliance
  - escalation   : CEO/executive involved, SLA breach, production outage, legal
  - general_query: short/vague from customer, greeting only
  - others       : non-business content — news, sports, trivia, personal, jokes

━━━ CLASSIFICATION DECISION TREE ━━━
Step 1 — CONTENT TYPE CHECK:
  Is body primarily non-business? → YES → others / low / is_ticket false
Step 2 — TICKET CHECK:
  Action required? → YES → is_ticket true (incident/service_request) else false (null)
Step 3 — URGENCY:
  HIGH: urgent, asap, blocked, data loss, legal, CEO, outage
  MEDIUM: complaint, billing dispute, access issue, payroll
  LOW: question, info request, feedback, greeting

Output ONLY a valid JSON object with exactly these keys:
{
  "category":        "<billing | it | hr | complaint | query | info_request | escalation | general_query | others>",
  "priority":        "<high | medium | low>",
  "sla_bucket":      "<4h | 8h | 24h | 48h>",
  "confidence":      <float 0.70-1.0>,
  "sentiment_score": <float -1.0 to 1.0>,
  "is_ticket":       <boolean>,
  "ticket_type":     "<incident | service_request | null>"
}

SLA: high/4h | medium/8h | low/24h
CRITICAL: Output ONLY the JSON. No explanation, no markdown.
""".strip()

CLASSIFICATION_USER_PROMPT = """
Classify the following customer email:

Subject: {email_subject}

Body:
{email_text}
""".strip()