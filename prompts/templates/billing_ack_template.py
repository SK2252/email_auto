"""
prompts/templates/billing_ack_template.py
Structured ACK template for billing-related emails.
Used by AG-04 (ResponseAgent) when category is billing / invoice_dispute / payment_failure.
"""

BILLING_ACK_TEMPLATE = """
Dear {customer_name},

Thank you for contacting us regarding your billing enquiry at {company_name}.

We have received your message and logged it under case **{case_reference}**.

Our billing team will review your {issue_type} and respond within **{response_sla}**. 
If you have any supporting documents (invoices, receipts), please reply to this 
email with them attached.

We appreciate your patience.

Best regards,
{agent_name}
{company_name}
""".strip()

REQUIRED_SLOTS = [
    "customer_name",
    "company_name",
    "case_reference",
    "issue_type",
    "response_sla",
    "agent_name",
]

FILL_PROMPT = """
Fill the billing acknowledgement template below.
Fill ONLY the named placeholders. Do NOT modify template structure.

Template:
{template}

Context:
- Customer name: {customer_name}
- Company name: {company_name}
- Case reference: {case_reference}
- Issue type (short description): {issue_type}
- Response SLA: {response_sla}
- Agent name: {agent_name}

Return ONLY the filled template. No JSON, no extra text.
""".strip()
