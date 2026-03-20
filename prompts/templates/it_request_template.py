"""
prompts/templates/it_request_template.py
Structured response template for IT support requests.
Used by AG-04 (ResponseAgent) when category is one of:
  password_reset, hardware_issue, software_bug, network_issue, access_request, etc.
"""

IT_REQUEST_TEMPLATE = (
    "Thank you for contacting the IT Support team.\n\n"
    "Your request has been logged under Case Reference: {case_id}.\n\n"
    "Ticket Type  : {ticket_type}\n"
    "Priority     : {priority}\n"
    "Expected SLA : {sla_bucket}\n\n"
    "{resolution_hint}"
    "\n\n"
    "Our team will follow up with you shortly. For urgent production issues, "
    "please also call the IT Hotline at ext. 999.\n\n"
    "Case Reference: {case_id}"
)

_RESOLUTION_HINTS = {
    "password_reset": (
        "In the meantime, you can self-serve a password reset via the IT portal at "
        "https://itportal.internal/reset"
    ),
    "hardware_issue": (
        "If possible, please note the asset tag (found on a sticker on the device) "
        "and include it in any follow-up reply."
    ),
    "software_bug": (
        "Please provide the exact error message and steps to reproduce when our engineer "
        "follows up."
    ),
    "network_issue": (
        "Please try restarting your network adapter and router as a first step. "
        "Note your current IP address (run: ipconfig) for our diagnostics."
    ),
    "access_request": (
        "Access requests require manager approval. Please ensure your line manager has "
        "submitted an approval via the IT portal before we can proceed."
    ),
}


def build_it_request_response(
    case_id: str,
    category: str = "technical_issue",
    priority: str = "medium",
    sla_bucket: str = "8 hours",
    ticket_type: str = "service_request",
    customer_name: str = "",
) -> str:
    """
    Render an IT support request acknowledgement.

    Args:
        case_id:       Unique case reference ID.
        category:      Email category (used to select resolution hint).
        priority:      Priority level (high / medium / low).
        sla_bucket:    Expected response window.
        ticket_type:   ITSM ticket type (incident / service_request).
        customer_name: Optional requester name for personalisation.

    Returns:
        Formatted IT ACK string ready to send.
    """
    greeting = f"Dear {customer_name},\n\n" if customer_name else ""
    resolution_hint = _RESOLUTION_HINTS.get(category, "Our team will be in touch soon.")
    body = IT_REQUEST_TEMPLATE.format(
        case_id=case_id,
        ticket_type=ticket_type.replace("_", " ").title(),
        priority=priority.upper(),
        sla_bucket=sla_bucket,
        resolution_hint=resolution_hint,
    )
    return greeting + body
