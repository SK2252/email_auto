"""
prompts/templates/__init__.py
Template registry — maps classification category to the correct template module.
Used by response_agent.py to pick the right template before calling Gemini.
"""
from prompts.templates.query_response_template import (
    QUERY_TEMPLATE,          FILL_PROMPT as QUERY_FILL_PROMPT,
    REQUIRED_SLOTS as QUERY_SLOTS,
)
from prompts.templates.billing_ack_template import (
    BILLING_ACK_TEMPLATE,    FILL_PROMPT as BILLING_FILL_PROMPT,
    REQUIRED_SLOTS as BILLING_SLOTS,
)
from prompts.templates.it_request_template import (
    IT_REQUEST_TEMPLATE,     FILL_PROMPT as IT_FILL_PROMPT,
    REQUIRED_SLOTS as IT_SLOTS,
)
from prompts.templates.hr_query_template import (
    HR_QUERY_TEMPLATE,       FILL_PROMPT as HR_FILL_PROMPT,
    REQUIRED_SLOTS as HR_SLOTS,
)

# Registry: classification category → (template_str, fill_prompt, required_slots)
TEMPLATE_REGISTRY = {
    "inquiry":      (QUERY_TEMPLATE,      QUERY_FILL_PROMPT,   QUERY_SLOTS),
    "info_request": (QUERY_TEMPLATE,      QUERY_FILL_PROMPT,   QUERY_SLOTS),
    "billing":      (BILLING_ACK_TEMPLATE, BILLING_FILL_PROMPT, BILLING_SLOTS),
    "technical_issue": (IT_REQUEST_TEMPLATE, IT_FILL_PROMPT,   IT_SLOTS),
    "password_reset":  (IT_REQUEST_TEMPLATE, IT_FILL_PROMPT,   IT_SLOTS),
    "hardware_issue":  (IT_REQUEST_TEMPLATE, IT_FILL_PROMPT,   IT_SLOTS),
    "software_bug":    (IT_REQUEST_TEMPLATE, IT_FILL_PROMPT,   IT_SLOTS),
    "network_issue":   (IT_REQUEST_TEMPLATE, IT_FILL_PROMPT,   IT_SLOTS),
    "access_request":  (IT_REQUEST_TEMPLATE, IT_FILL_PROMPT,   IT_SLOTS),
    "hr_query":     (HR_QUERY_TEMPLATE,   HR_FILL_PROMPT,      HR_SLOTS),
    "general_query": (QUERY_TEMPLATE,      QUERY_FILL_PROMPT,   QUERY_SLOTS),
    "query":         (QUERY_TEMPLATE,      QUERY_FILL_PROMPT,   QUERY_SLOTS),
}


def get_template(category: str):
    """
    Returns (template_str, fill_prompt, required_slots) for the given category.
    Falls back to the generic query template if category has no specific template.
    """
    return TEMPLATE_REGISTRY.get(category, (QUERY_TEMPLATE, QUERY_FILL_PROMPT, QUERY_SLOTS))
