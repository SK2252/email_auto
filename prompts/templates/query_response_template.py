"""
prompts/templates/query_response_template.py
General-purpose query/info-request response template.
Used by AG-04 (ResponseAgent) for: query, general_query, info_request, others.
"""

QUERY_TEMPLATE = """
Dear {customer_name},

Thank you for reaching out to {company_name}.

We have received your enquiry regarding "{subject_summary}" and logged it 
under case **{case_reference}**.

{resolution_or_info}

Our team will review your message and respond within **{response_sla}**.

If you need to follow up, please quote **{case_reference}** in any reply.

Best regards,
{agent_name}
{company_name}
""".strip()

REQUIRED_SLOTS = [
    "customer_name",
    "company_name",
    "subject_summary",
    "case_reference",
    "resolution_or_info",
    "response_sla",
    "agent_name",
]

FILL_PROMPT = """
Fill the general query acknowledgement template below.
Fill ONLY the named placeholders. Do NOT modify template structure.

Template:
{template}

Context:
- Customer name: {customer_name}
- Case reference: {case_reference}
- Company name: {company_name}
- Subject summary (brief): {subject_summary}
- Resolution or info (1-2 sentences about what happens next): {resolution_context}
- Response SLA (e.g. "24 hours", "2 business days"): {response_sla}
- Agent name: {agent_name}

Return ONLY the filled template. No JSON, no extra text.
""".strip()
