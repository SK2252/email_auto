"""
prompts/templates/hr_query_template.py
Structured response template for HR-related email queries.
Used by AG-04 (ResponseAgent) when category is hr / leave_request / payroll_query / grievance.
"""

HR_QUERY_TEMPLATE = """
Dear {customer_name},

Thank you for reaching out to the HR team at {company_name}.

Your enquiry regarding "{subject_summary}" has been received and logged 
under case **{case_reference}**.

A member of our {team_name} will be in touch within **{response_sla}** to 
assist you with your request.

{next_steps}

Please note that all HR matters are handled confidentially in accordance 
with our company policy and applicable employment law.

If your matter is urgent, please contact your direct HR Business Partner.

Best regards,
{agent_name}
{company_name}
""".strip()

REQUIRED_SLOTS = [
    "customer_name",
    "company_name",
    "subject_summary",
    "case_reference",
    "team_name",
    "response_sla",
    "next_steps",
    "agent_name",
]

FILL_PROMPT = """
Fill the HR query acknowledgement template below.
Fill ONLY the named placeholders. Do NOT modify template structure.

Template:
{template}

Context:
- Customer name: {customer_name}
- Case reference: {case_reference}
- Company name: {company_name}
- Subject summary: {subject_summary}
- Team name (e.g. HR Operations, Payroll Team): {team_name}
- Response SLA: {response_sla}
- Next steps (1-2 sentences): {next_steps_context}
- Agent name: {agent_name}

Return ONLY the filled template. No JSON, no extra text.
""".strip()
