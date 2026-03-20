"""
prompts/templates/__init__.py
Email response template registry.
Import individual templates or use build_template() for dynamic dispatch.
"""
from .billing_ack_template import BILLING_ACK_TEMPLATE, build_billing_ack
from .hr_query_template import HR_QUERY_TEMPLATE, build_hr_query_response
from .it_request_template import IT_REQUEST_TEMPLATE, build_it_request_response
from .query_response_template import QUERY_RESPONSE_TEMPLATE, build_query_response

__all__ = [
    "BILLING_ACK_TEMPLATE",
    "HR_QUERY_TEMPLATE",
    "IT_REQUEST_TEMPLATE",
    "QUERY_RESPONSE_TEMPLATE",
    "build_billing_ack",
    "build_hr_query_response",
    "build_it_request_response",
    "build_query_response",
]


_TEMPLATE_MAP = {
    "billing":         build_billing_ack,
    "invoice_dispute": build_billing_ack,
    "hr":              build_hr_query_response,
    "leave_request":   build_hr_query_response,
    "payroll_query":   build_hr_query_response,
    "password_reset":  build_it_request_response,
    "hardware_issue":  build_it_request_response,
    "software_bug":    build_it_request_response,
    "network_issue":   build_it_request_response,
    "access_request":  build_it_request_response,
    "query":           build_query_response,
    "general_query":   build_query_response,
    "info_request":    build_query_response,
}


def build_template(category: str, **kwargs) -> str:
    """
    Dispatch to the correct template builder by email category.

    Args:
        category: Classified email category (e.g. 'billing', 'hr').
        **kwargs: Template-specific keyword arguments forwarded to builder.

    Returns:
        Rendered template string.
    """
    builder = _TEMPLATE_MAP.get(category, build_query_response)
    return builder(**kwargs)
