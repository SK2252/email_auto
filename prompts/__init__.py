"""
prompts/__init__.py — Prompt Package Registry
Centralised exports for all prompt builders and domain-specific prompts.
"""

# ---------------------------------------------------------------------------
# Generic / domain-aware prompts (used by agents when domain_config available)
# ---------------------------------------------------------------------------
from .classification_prompt import (
    VALID_TICKET_TYPES,
    build_classification_prompts,
    CLASSIFICATION_SYSTEM_PROMPT,
    CLASSIFICATION_USER_PROMPT,
)
from .routing_prompt import (
    build_routing_prompts,
    ROUTING_SYSTEM_PROMPT,
    ROUTING_USER_PROMPT,
)
from .response_draft_prompt import (
    build_response_prompts,
    RESPONSE_SYSTEM_PROMPT,
    RESPONSE_USER_PROMPT,
)
from .sentiment_prompt import SENTIMENT_SYSTEM_PROMPT, SENTIMENT_USER_PROMPT
from .pii_scan_prompt import PII_SCAN_SYSTEM_PROMPT, PII_SCAN_USER_PROMPT
from .analytics_insight_prompt import ANALYTICS_SYSTEM_PROMPT, ANALYTICS_USER_PROMPT

# ---------------------------------------------------------------------------
# Domain-specific prompts
# ---------------------------------------------------------------------------
from .it_support_prompt import (
    build_it_support_prompts,
    IT_SUPPORT_SYSTEM_PROMPT,
    IT_SUPPORT_USER_PROMPT,
)
from .hr_prompt import (
    build_hr_prompts,
    HR_SYSTEM_PROMPT,
    HR_USER_PROMPT,
)
from .customer_support_prompt import (
    build_customer_support_prompts,
    CUSTOMER_SUPPORT_SYSTEM_PROMPT,
    CUSTOMER_SUPPORT_USER_PROMPT,
)

# ---------------------------------------------------------------------------
# Response templates (structured, non-LLM fallback templates)
# ---------------------------------------------------------------------------
from .templates import build_template

__all__ = [
    # Generic
    "VALID_TICKET_TYPES",
    "build_classification_prompts",
    "CLASSIFICATION_SYSTEM_PROMPT",
    "CLASSIFICATION_USER_PROMPT",
    "build_routing_prompts",
    "ROUTING_SYSTEM_PROMPT",
    "ROUTING_USER_PROMPT",
    "build_response_prompts",
    "RESPONSE_SYSTEM_PROMPT",
    "RESPONSE_USER_PROMPT",
    # Domain-specific — IT Support
    "build_it_support_prompts",
    "IT_SUPPORT_SYSTEM_PROMPT",
    "IT_SUPPORT_USER_PROMPT",
    # Domain-specific — HR
    "build_hr_prompts",
    "HR_SYSTEM_PROMPT",
    "HR_USER_PROMPT",
    # Domain-specific — Customer Support
    "build_customer_support_prompts",
    "CUSTOMER_SUPPORT_SYSTEM_PROMPT",
    "CUSTOMER_SUPPORT_USER_PROMPT",
    # Templates
    "build_template",
]
