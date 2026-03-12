"""
prompts/templates/billing_ack_template.py
Canned template for billing-related auto-responses.
Used only on auto-send path — LLM fills slots only.
"""

BILLING_ACK_TEMPLATE = """
Dear {customer_name},

Thank you for contacting {company_name} about your billing enquiry.

We have received your request regarding **{billing_subject}** and have 
logged it under case **{case_reference}**.

{billing_action_taken}

Expected resolution: within **{resolution_timeframe}**.

If you have questions before then, please quote **{case_reference}** 
in any follow-up.

Kind regards,
Billing Support Team
{company_name}
""".strip()

REQUIRED_SLOTS = [
    "customer_name",
    "company_name",
    "billing_subject",
    "case_reference",
    "billing_action_taken",
    "resolution_timeframe",
]

FILL_PROMPT = """
Fill the billing acknowledgement template below.
Fill ONLY the named placeholders. Do not modify the template structure.

Template:
{template}

Context:
- Customer name: {customer_name}
- Case reference: {case_reference}
- Company name: {company_name}
- Billing subject (one phrase from email): {billing_subject}
- Action taken (1-2 sentences): {billing_action_context}
- Resolution timeframe: {resolution_timeframe}

Return ONLY the filled template. No JSON, no extra text.
""".strip()
