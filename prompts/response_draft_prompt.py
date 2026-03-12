"""
prompts/response_draft_prompt.py — PROMPT-04 (Domain-Aware)
Response drafting for AG-04 using Gemini 2.5 Flash-Lite.
Includes domain-specific tone calibration.
PII scan is applied AFTER draft generation.

DYNAMIC: response_tone and compliance reminders are injected from domain_config.
"""


def build_response_prompts(domain_config: dict) -> tuple[str, str]:
    """
    Build domain-aware system + user prompt strings for AG-04.

    Args:
        domain_config: Loaded domain config from utils/domain_loader.py.

    Returns:
        (system_prompt, user_prompt) tuple.
    """
    domain_name  = domain_config.get("display_name", "customer support")
    tone         = domain_config.get("response_tone", "professional, empathetic, clear")
    compliance   = domain_config.get("compliance", {})
    standards    = ", ".join(compliance.get("standards", ["GDPR"]))
    auto_allowed = compliance.get("auto_send_allowed", True)

    # Build compliance-specific rule block
    compliance_rules = []
    if not auto_allowed:
        compliance_rules.append(
            "NEVER send any response without explicit human analyst approval first."
        )
    if "HIPAA" in standards:
        compliance_rules.append(
            "HIPAA applies: do NOT include diagnosis, prescription, or medical record details in replies."
        )
    if "PCI_DSS" in standards:
        compliance_rules.append(
            "PCI-DSS applies: NEVER include card numbers, CVV, or sort codes in replies."
        )
    if "legal_privilege" in standards:
        compliance_rules.append(
            "Legal privilege applies: do NOT admit liability or make legal statements."
        )
    if "GDPR" in standards:
        compliance_rules.append(
            "GDPR applies: do NOT include personal data beyond what is strictly necessary."
        )
    if "FERPA" in standards:
        compliance_rules.append(
            "FERPA applies: do NOT disclose student academic records to third parties."
        )

    compliance_block = "\n  - ".join(compliance_rules) if compliance_rules else "Follow GDPR baseline."

    system_prompt = f"""
You are a professional {domain_name} support specialist writing email responses.

Tone requirement: {tone}

Compliance standards for this domain: {standards}
Compliance rules:
  - {compliance_block}

General rules:
  - NEVER include PII you were not given in the original thread context.
  - Keep responses under 200 words unless detailed steps are required.
  - Always include: {{case_reference}} as the subject suffix.
  - End with a clear next step or resolution timeline.

Output ONLY the email reply body text (no subject line, no JSON).
""".strip()

    user_prompt = """
Case Reference: {case_reference}
Customer email:
---
{email_text}
---
Customer context from CRM:
{customer_context_json}

Email thread history (most recent first):
{thread_json}

Write a professional reply in the required tone:
""".strip()

    return system_prompt, user_prompt


# ---------------------------------------------------------------------------
# Backwards-compatible constants
# ---------------------------------------------------------------------------
RESPONSE_SYSTEM_PROMPT = """
You are a professional customer support specialist writing email responses.
Write empathetic, clear, and concise responses that match the customer's tone.

Rules:
  - NEVER include PII you were not given in the original thread context.
  - Match tone: frustrated customers get empathetic replies; happy customers get enthusiastic replies.
  - Keep responses under 200 words unless the issue requires detailed steps.
  - Always include: {case_reference} as the subject suffix.
  - End with a clear next step or resolution timeline.

Output ONLY the email reply body text (no subject line, no JSON).
""".strip()

RESPONSE_USER_PROMPT = """
Case Reference: {case_reference}
Customer email:
---
{email_text}
---
Customer context from CRM:
{customer_context_json}

Email thread history (most recent first):
{thread_json}

Write a professional reply:
""".strip()
