"""
prompts/templates/hr_query_template.py
Structured response template for HR-related email queries.
Used by AG-04 (ResponseAgent) when category is hr / leave_request / payroll_query / grievance.
"""

HR_QUERY_TEMPLATE = (
    "Thank you for reaching out to the HR team.\n\n"
    "Your enquiry has been received and logged under Case Reference: {case_id}.\n\n"
    "A member of our {team} will be in touch within {sla_bucket} to assist you\n"
    "with your {issue_type}.\n\n"
    "Please note that all HR matters are handled confidentially in accordance\n"
    "with our company policy and applicable employment law.\n\n"
    "If your matter is urgent, please contact your direct HR Business Partner.\n\n"
    "Case Reference: {case_id}"
)


def build_hr_query_response(
    case_id: str,
    sla_bucket: str = "24 hours",
    team: str = "HR Operations",
    issue_type: str = "HR enquiry",
    customer_name: str = "",
) -> str:
    """
    Render an HR query acknowledgement message.

    Args:
        case_id:       Unique case reference ID.
        sla_bucket:    Expected response window (e.g. '4h', '24h', '48h').
        team:          HR sub-team name (HR Operations, Payroll Team, etc.).
        issue_type:    Short description (leave request, payroll query, etc.).
        customer_name: Optional employee/customer name for personalisation.

    Returns:
        Formatted response string ready to send.
    """
    greeting = f"Dear {customer_name},\n\n" if customer_name else ""
    body = HR_QUERY_TEMPLATE.format(
        case_id=case_id,
        sla_bucket=sla_bucket,
        team=team,
        issue_type=issue_type,
    )
    return greeting + body
