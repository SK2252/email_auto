"""
prompts/templates/it_request_template.py
Structured response template for IT support requests.
Used by AG-04 (ResponseAgent) when category is one of:
  password_reset, hardware_issue, software_bug, network_issue, access_request, etc.
"""

IT_REQUEST_TEMPLATE = """
Dear {customer_name},

Thank you for contacting the IT Support team at {company_name}.

Your request regarding "{subject_summary}" has been logged under case **{case_reference}**.

Ticket Type  : {ticket_type}
Priority     : {priority}
Expected SLA : {response_sla}

{resolution_hint}

Our team will follow up with you shortly. For urgent production issues, 
please also call the IT Hotline at ext. 999.

Best regards,
{agent_name}
{company_name}
""".strip()

REQUIRED_SLOTS = [
    "customer_name",
    "company_name",
    "subject_summary",
    "case_reference",
    "ticket_type",
    "priority",
    "response_sla",
    "resolution_hint",
    "agent_name",
]

FILL_PROMPT = """
Fill the IT support request acknowledgement template below.
Fill ONLY the named placeholders. Do NOT modify template structure.

Template:
{template}

Context:
- Customer name: {customer_name}
- Company name: {company_name}
- Subject summary: {subject_summary}
- Case reference: {case_reference}
- Ticket type (e.g. Service Request, Incident): {ticket_type}
- Priority: {priority}
- Response SLA: {response_sla}
- Resolution hint (optional self-serve steps, 1-2 sentences): {resolution_hint}
- Agent name: {agent_name}

Return ONLY the filled template. No JSON, no extra text.
""".strip()
