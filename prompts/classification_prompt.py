"""
prompts/classification_prompt.py — PROMPT-01 (Domain-Aware)
Single batched prompt for BOTH classification AND sentiment scoring.
One Groq API call = conserves 30 rpm free quota.

DYNAMIC: taxonomy and SLA buckets are injected at runtime from domain_config.
Agents call build_classification_prompts(domain_config) instead of importing
the string constants directly.
"""

# ---------------------------------------------------------------------------
# GLOBAL CONSTANTS  — used by classification_agent for validation
# ---------------------------------------------------------------------------
VALID_CATEGORIES = [
    "billing", "invoice_dispute", "payment_failure", "overcharge", "refund_request",
    "general_billing", "payment_confirmation", "tax_query", "subscription_change",
    "hardware_issue", "software_bug", "network_issue", "security_incident", "technical_issue",
    "password_reset", "access_request", "onboarding", "leave_request", "payroll_query",
    "benefits_query", "policy_clarification", "offboarding", "grievance", "recruitment",
    "complaint", "escalation", "inquiry", "info_request", "query", "general_query", "others"
]

VALID_TICKET_TYPES = ["incident", "service_request", "change", "problem", "null"]


def build_classification_prompts(domain_config: dict) -> tuple[str, str]:
    """
    Build domain-aware system + user prompt strings for AG-02.
    Returns (system_prompt, user_prompt) tuple.
    """
    # Use universal_taxonomy if available (default inbox receives all email types)
    # Fall back to domain-specific taxonomy otherwise
    raw_taxonomy    = domain_config.get("universal_taxonomy") or domain_config.get("taxonomy", ["query", "complaint", "others"])
    taxonomy        = " | ".join(raw_taxonomy)
    sla_buckets     = " | ".join(domain_config.get("sla_rules", {}).keys())
    domain_name     = domain_config.get("display_name", "customer support")
    priority_levels = list(domain_config.get("sla_rules", {}).keys())

    priority_guidance_lines = []
    for tier, rule in domain_config.get("sla_rules", {}).items():
        bucket = rule.get("bucket", "24h")
        priority_guidance_lines.append(f"  - {tier:20s} / {bucket}")
    priority_guidance = "\n".join(priority_guidance_lines) if priority_guidance_lines else (
        "  - high   / 4h\n  - medium / 24h\n  - low    / 48h"
    )

    system_prompt = f"""
You are an expert email triage AI for a {domain_name} inbox management system.
Classify the email, assess sentiment, and determine ticket status in ONE response.

DOMAIN: {domain_name}
Available categories (choose EXACTLY one):
{chr(10).join(f"  - {cat}" for cat in raw_taxonomy)}

━━━ CLASSIFICATION DECISION TREE ━━━
Step 1 — CONTENT TYPE CHECK (apply first):
  Is the email body primarily non-business content?
  (news, trivia, jokes, personal stories, forwarded non-biz content)
  → YES → others / low / confidence 0.90 / is_ticket false
  → NO  → continue to Step 2

Step 2 — TICKET DETERMINATION:
  Does the email require a trackable action or resolution?
  → YES → is_ticket: true, ticket_type: incident (bug/outage) or service_request (access/reset/info)
  → NO  → is_ticket: false, ticket_type: null (greetings, feedback, spam)

Step 3 — URGENCY SIGNALS:
  HIGH: "urgent", "asap", "production down", "data loss", "blocked", "SLA breach", "legal", "CEO"
  → found → priority = high
  MEDIUM: complaint, billing dispute, technical problem, access issue, payroll missing
  → found → priority = medium
  LOW: general question, feedback, info request, non-urgent
  → found → priority = low

Step 4 — CATEGORY MATCH (most specific wins):
  billing      → invoice, charge, payment, refund, GST, receipt, subscription fee, overcharge
  it           → VPN, password, error code, system down, software bug, access denied, hardware
  hr           → leave, payroll, salary, grievance, harassment, employee policy, benefits
  complaint    → strong negative tone + demand for action (refund, apology, cancellation)
  escalation   → CEO/VP/executive involved OR SLA breach OR legal threat OR production outage
  query        → genuine business question about product, pricing, service, feature, support
  info_request → asking for document, report, data, API docs, compliance records
  general_query → short/vague from customer, greeting only
  others       → non-business content (news, jokes, trivia)

Output ONLY a valid JSON object with exactly these keys:
{{
  "category":        "<one of the categories above>",
  "priority":        "<{" | ".join(priority_levels)}>",
  "sla_bucket":      "<{sla_buckets}>",
  "confidence":      <float 0.0–1.0>,
  "sentiment_score": <float -1.0 to 1.0>,
  "is_ticket":       <boolean>,
  "ticket_type":     "<incident | service_request | null>"
}}

Priority and SLA mapping for {domain_name}:
{priority_guidance}

Confidence scoring:
  0.90–1.00 → clear match, strong keywords
  0.70–0.89 → good match, some ambiguity
  below 0.70 → borderline — set minimum 0.70

Sentiment: -1.0=furious, 0.0=neutral, +1.0=grateful

CRITICAL: Output ONLY the JSON object. No markdown, no extra text.
""".strip()

    user_prompt = """
Classify the following customer email:

Subject: {email_subject}

Body:
{email_text}
""".strip()

    return system_prompt, user_prompt


# ---------------------------------------------------------------------------
# Backwards-compatible fallback (used when no domain_config available)
# ---------------------------------------------------------------------------
CLASSIFICATION_SYSTEM_PROMPT = """
You are an expert email triage AI for a customer support inbox management system.
Classify the email, assess sentiment, and determine ticket status in ONE response.

Available categories (choose EXACTLY one):
  - billing        : invoices, charges, refunds, payments, pricing, GST
  - it             : VPN, password, system errors, software/hardware, access denied
  - hr             : leave, payroll, grievance, harassment, HR policy, benefits
  - complaint      : angry customer demanding action (refund, apology, cancellation)
  - query          : genuine business question about product, pricing, service
  - info_request   : request for document, report, data, API docs, compliance
  - escalation     : CEO/executive involved, SLA breach, production outage, legal
  - general_query  : short/vague from customer, greeting only
  - others         : non-business content — news, sports, trivia, personal, jokes

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
  "confidence":      <float 0.0–1.0>,
  "sentiment_score": <float -1.0 to 1.0>,
  "is_ticket":       <boolean>,
  "ticket_type":     "<incident | service_request | null>"
}

SLA mapping:
  high   / 4h  | medium / 8h  | low / 24h

CRITICAL: Output ONLY the JSON object. No explanation, no markdown.
""".strip()

CLASSIFICATION_USER_PROMPT = """
Classify the following customer email:

Subject: {email_subject}

Body:
{email_text}
""".strip()