"""
prompts/templates/query_response_template.py
General-purpose query/info-request response template.
Used by AG-04 (ResponseAgent) for: query, general_query, info_request, others.
"""

QUERY_RESPONSE_TEMPLATE = (
    "Thank you for reaching out.\n\n"
    "We have received your enquiry and logged it under Case Reference: {case_id}.\n\n"
    "Our team will review your message and respond within {sla_bucket}.\n\n"
    "If you need to follow up in the meantime, please quote your case reference "
    "in any reply.\n\n"
    "Case Reference: {case_id}"
)


def build_query_response(
    case_id: str,
    sla_bucket: str = "24 hours",
    team: str = "Support Team",
    customer_name: str = "",
) -> str:
    """
    Render a general query acknowledgement message.

    Args:
        case_id:       Unique case reference ID.
        sla_bucket:    Expected response window (e.g. '24h', '48h').
        team:          Team name handling this query.
        customer_name: Optional customer name for personalisation.

    Returns:
        Formatted acknowledgement string ready to send.
    """
    greeting = f"Dear {customer_name},\n\n" if customer_name else ""
    body = QUERY_RESPONSE_TEMPLATE.format(
        case_id=case_id,
        sla_bucket=sla_bucket,
        team=team,
    )
    return greeting + body
