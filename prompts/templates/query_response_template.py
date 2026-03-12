"""
prompts/templates/query_response_template.py
Canned template for auto-send path: general inquiries / info requests.
The LLM fills {placeholders} — it does NOT freewrite outside this structure.
"""

QUERY_TEMPLATE = """
Dear {customer_name},

Thank you for contacting {company_name} support. We received your enquiry 
regarding {subject_summary}.

{resolution_or_info}

If you need any further clarification, please reply to this email with your 
case reference **{case_reference}** and we'll be happy to assist.

Kind regards,
{agent_name}
{company_name} Customer Support
Case: {case_reference}
""".strip()

# Slots the LLM must fill — nothing outside these is injected into auto-send emails
REQUIRED_SLOTS = [
    "customer_name",
    "company_name",
    "subject_summary",
    "resolution_or_info",
    "case_reference",
    "agent_name",
]

FILL_PROMPT = """
You are filling a customer support email template.
Fill ONLY the placeholders listed below. Do not add any new content, 
change the structure, or deviate from the template.

Template:
{template}

Context:
- Customer name: {customer_name}
- Case reference: {case_reference}
- Company name: {company_name}
- Agent name: Support Team
- Subject summary (one phrase): {subject_summary}
- Resolution or info (2-3 sentences max): {resolution_context}

Return ONLY the filled template text, no JSON, no headers.
""".strip()
