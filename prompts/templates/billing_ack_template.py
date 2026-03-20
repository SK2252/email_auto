"""
prompts/templates/billing_ack_template.py
Structured ACK template for billing-related emails.
Used by AG-04 (ResponseAgent) when category is billing / invoice_dispute / payment_failure.
"""

BILLING_ACK_TEMPLATE = (
    "Thank you for contacting us regarding your billing enquiry.\n\n"
    "We have received your message and logged it under Case Reference: {case_id}.\n\n"
    "Our billing team will review your {issue_type} and respond within {sla_bucket}.\n"
    "If you have any supporting documents (invoices, receipts), please reply to this\n"
    "email with them attached.\n\n"
    "We appreciate your patience.\n\n"
    "Case Reference: {case_id}"
)


def build_billing_ack(
    case_id: str,
    sla_bucket: str = "24 hours",
    issue_type: str = "billing enquiry",
    customer_name: str = "",
) -> str:
    """
    Render a billing acknowledgement message.

    Args:
        case_id:       Unique case reference ID.
        sla_bucket:    Expected response window (e.g. '4h', '8h', '24h').
        issue_type:    Short description of the billing issue.
        customer_name: Optional customer name for personalisation.

    Returns:
        Formatted ACK string ready to send.
    """
    greeting = f"Dear {customer_name},\n\n" if customer_name else ""
    body = BILLING_ACK_TEMPLATE.format(
        case_id=case_id,
        sla_bucket=sla_bucket,
        issue_type=issue_type,
    )
    return greeting + body
