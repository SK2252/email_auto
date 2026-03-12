"""
prompts/templates/hr_query_template.py
Canned template for HR-related queries on auto-send path.
"""

HR_QUERY_TEMPLATE = """
Dear {employee_name},

Thank you for reaching out to {company_name} HR.

We have received your query regarding **{hr_subject}** and registered 
it under reference **{case_reference}**.

{hr_response_info}

For policy documents and self-service tools, please visit the HR portal.
If your query is time-sensitive, please indicate that in your 
follow-up with reference **{case_reference}**.

Warm regards,
HR Support Team
{company_name}
""".strip()

REQUIRED_SLOTS = [
    "employee_name",
    "company_name",
    "hr_subject",
    "case_reference",
    "hr_response_info",
]

FILL_PROMPT = """
Fill the HR query response template below.
Fill ONLY the named placeholders. Do not modify template structure.

Template:
{template}

Context:
- Employee name: {employee_name}
- Case reference: {case_reference}
- Company name: {company_name}
- HR subject (one phrase): {hr_subject}
- HR response info (2-3 sentences with relevant guidance): {hr_context}

Return ONLY the filled template. No JSON, no extra text.
""".strip()
