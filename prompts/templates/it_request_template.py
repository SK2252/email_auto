"""
prompts/templates/it_request_template.py
Canned template for IT / technical support requests on auto-send path.
"""

IT_REQUEST_TEMPLATE = """
Dear {customer_name},

Thank you for submitting an IT support request.

Your ticket **{case_reference}** has been logged and assigned to the 
{team_name} team with **{priority_label} priority**.

{next_steps}

Expected first response: **{response_sla}**.

For urgent issues, please contact the IT helpdesk directly and quote 
**{case_reference}**.

Best regards,
IT Support Team
{company_name}
""".strip()

REQUIRED_SLOTS = [
    "customer_name",
    "case_reference",
    "team_name",
    "priority_label",
    "next_steps",
    "response_sla",
    "company_name",
]

FILL_PROMPT = """
Fill the IT support acknowledgement template below.
Fill ONLY the named placeholders. Do NOT modify template structure.

Template:
{template}

Context:
- Customer name: {customer_name}
- Case reference: {case_reference}
- Company name: {company_name}
- Assigned team: {team_name}
- Priority label (e.g. High / Medium / Low): {priority_label}
- Next steps (1-2 sentences describing what happens next): {next_steps_context}
- Response SLA (e.g. "4 hours", "1 business day"): {response_sla}

Return ONLY the filled template. No JSON, no extra text.
""".strip()
