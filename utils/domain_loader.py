"""
utils/domain_loader.py — Domain Configuration Loader
Loads the correct domain config at runtime based on tenant_id.
Injects domain_config dict into LangGraph state at AG-01 intake.

UPDATED: Added content-based domain detection.
The system now detects domain from email subject+body keywords
when tenant_id is "default" — so the correct domain prompt fires
for IT, HR, and Customer Support emails automatically.

Gmail label structure (3 domains):
  IT Support/*       → domain_id: it_support  → prompts/it_support_prompt.py
  HR/*               → domain_id: hr          → prompts/hr_prompt.py
  Customer Support/* → domain_id: billing     → prompts/customer_support_prompt.py
  Others/*           → domain_id: default     → generic fallback prompt
"""
from __future__ import annotations

import copy
import json
import logging
from typing import Any, Dict, Optional

from config.domains import DOMAIN_REGISTRY

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hardcoded tenant → domain mapping
# In production this comes from the DB tenants table.
# "default" intentionally removed — content detection handles it now.
# ---------------------------------------------------------------------------
_TENANT_DOMAIN_MAP: Dict[str, str] = {
    "acme_hospital":   "healthcare",
    "veridian_law":    "legal",
    "shopfast_ecom":   "ecommerce",
    "edu_central_uni": "education",
    "payroll_corp":    "billing",
    "global_hr_svc":   "hr",
}

# ---------------------------------------------------------------------------
# CONTENT-BASED DOMAIN DETECTION
# Detects domain from email subject + body keywords.
# Called when tenant_id is "default" or unknown.
#
# Maps directly to your 3 Gmail label groups:
#   IT Support/*       → "it_support"
#   HR/*               → "hr"
#   Customer Support/* → "billing"
# ---------------------------------------------------------------------------

_HR_KEYWORDS = {
    # Payroll / salary
    "salary", "payslip", "pay slip", "pay-slip", "payroll",
    "tds", "form 16", "reimbursement", "incentive", "bonus",
    "ctc", "compensation", "wage", "wages", "hrms payroll",
    "payroll cycle", "payslip not", "salary not credited",
    "salary credited", "salary delayed",
    # Leave
    "leave", "annual leave", "sick leave", "casual leave",
    "wfh", "work from home", "attendance",
    # Recruitment
    "headcount", "hiring", "interview", "recruitment", "candidate",
    "offer letter", "joining date", "bgv", "background verification",
    "referral program",
    # Employee relations
    "appraisal", "performance review", "promotion",
    "grievance", "harassment", "misconduct", "disciplinary",
    # General HR
    "hr team", "hr department", "human resource",
    "employee policy", "benefits", "provident fund",
    "esi", "hr policy", "onboarding", "offboarding",
}

_CUSTOMER_SUPPORT_KEYWORDS = {
    # Billing / financial
    "invoice", "billing", "overcharge", "duplicate charge",
    "refund", "payment failed", "subscription", "gst invoice",
    "gstin", "tax invoice", "credit note", "account balance",
    "charged twice", "wrong charge", "receipt",
    # Complaints / escalation
    "legal action", "consumer court", "sla breach",
    "unacceptable", "very disappointed", "furious",
    # Product support
    "webhook", "api integration", "configure", "integration",
    "how to use", "feature request", "product documentation",
    "product not working", "product bug",
    # Warranty / physical product
    "warranty", "warranty claim", "damaged product",
    "defective", "replacement", "return request",
    "product arrived", "cracked", "broken product",
}

_IT_KEYWORDS = {
    "vpn", "password reset", "reset password", "otp",
    "cannot login", "login failed", "access denied",
    "network issue", "connectivity", "wifi", "firewall",
    "vpn error", "error code", "system down", "system crash",
    "software bug", "hardware issue", "laptop slow",
    "laptop not working", "printer", "monitor",
    "application crash", "blue screen", "mfa",
    "phishing", "security incident", "data breach",
    "certificate", "it support", "helpdesk",
    "slow to boot", "takes to boot", "freezing",
}


def _detect_domain_from_content(
    subject: str = "",
    body: str = "",
) -> str:
    """
    Detect domain from email subject + body keyword matching.
    Returns one of: "hr", "billing", "it_support", "default"

    Scoring approach:
    - HR keywords are very specific → wins if any match
    - Customer Support keywords are specific (billing, warranty, product)
    - IT Support is the technical fallback
    - "default" = no clear signal → generic prompt with all categories
    """
    text = (subject + " " + body).lower()

    hr_hits = sum(1 for kw in _HR_KEYWORDS if kw in text)
    cs_hits = sum(1 for kw in _CUSTOMER_SUPPORT_KEYWORDS if kw in text)
    it_hits = sum(1 for kw in _IT_KEYWORDS if kw in text)

    logger.info(json.dumps({
        "event":   "domain_content_detection",
        "subject": subject[:60],
        "scores":  {"hr": hr_hits, "cs": cs_hits, "it": it_hits},
    }))

    # HR wins if it has hits — payroll/HR keywords are highly specific
    if hr_hits > 0 and hr_hits >= cs_hits:
        return "hr"

    # Customer Support wins over IT if more specific hits
    if cs_hits > 0 and cs_hits >= it_hits:
        return "billing"

    # IT Support — technical issues
    if it_hits > 0:
        return "it_support"

    # No clear signal — use generic fallback (handles all 9 categories)
    return "default"


# ---------------------------------------------------------------------------
# DEFAULT_DOMAIN_CONFIG — safe fallback for unknown tenants
# ---------------------------------------------------------------------------
DEFAULT_DOMAIN_CONFIG: Dict[str, Any] = {
    "domain_id":   "default",
    "taxonomy": [
        "billing", "it", "hr", "complaint",
        "query", "info_request", "escalation",
        "general_query", "others",
    ],
    "sla_rules": {
        "high":     {"bucket": "4h",  "bucket_seconds": 14400,  "escalate_at": 0.8},
        "medium":   {"bucket": "8h",  "bucket_seconds": 28800,  "escalate_at": 0.8},
        "low":      {"bucket": "24h", "bucket_seconds": 86400,  "escalate_at": 0.8},
        "very_low": {"bucket": "48h", "bucket_seconds": 172800, "escalate_at": 0.8},
    },
    "priority_to_sla": {
        "high":   "high",
        "medium": "medium",
        "low":    "low",
    },
    "routing_teams": [
        "Tier 1 Support",
        "Customer Service",
        "HR Ops",
        "Finance Ops",
        "Team Lead",
    ],
    "routing_rules": {},
    "compliance": {
        "standards": ["GDPR"],
        "pii_extra":  [],
    },
    "auto_send_allowed": False,
    "auto_send_types":   [],
    "response_tone": "professional, helpful, neutral",
}


def get_default_domain_config() -> Dict[str, Any]:
    """Return a deep-copy of the DEFAULT_DOMAIN_CONFIG. Thread-safe."""
    return copy.deepcopy(DEFAULT_DOMAIN_CONFIG)


def get_domain_config(
    tenant_id: str,
    config_overrides: Optional[Dict[str, Any]] = None,
    email_subject: str = "",
    email_body: str = "",
) -> Dict[str, Any]:
    """
    Load and return the domain config for a given tenant.

    For named tenants → explicit domain from _TENANT_DOMAIN_MAP.
    For "default" / unknown tenants → content-based domain detection
    using email_subject and email_body keywords.

    Args:
        tenant_id:        Identifier for the tenant.
        config_overrides: Optional per-tenant overrides (from DB).
        email_subject:    Email subject for content-based detection.
        email_body:       Email body for content-based detection.

    Returns:
        Full domain config dict. Never raises.
    """
    # 1. Named tenant → explicit domain
    domain_id = _TENANT_DOMAIN_MAP.get(tenant_id)

    # 2. Default / unknown tenant → content-based detection
    if not domain_id:
        if email_subject or email_body:
            domain_id = _detect_domain_from_content(email_subject, email_body)
            logger.info(json.dumps({
                "event":     "domain_config_loaded",
                "tenant_id": tenant_id,
                "domain_id": domain_id,
                "method":    "content_detection",
                "overrides_applied": bool(config_overrides),
            }))
        else:
            # No content provided — use default
            domain_id = "default"
            logger.warning(json.dumps({
                "event":     "domain_config_loaded",
                "tenant_id": tenant_id,
                "domain_id": "default",
                "method":    "no_content_fallback",
            }))

    # 3. "default" domain_id → return DEFAULT_DOMAIN_CONFIG
    if domain_id == "default":
        config = get_default_domain_config()
        if config_overrides:
            config = _deep_merge(config, config_overrides)
        return config

    # 4. Look up in registry
    base_config = DOMAIN_REGISTRY.get(domain_id)
    if not base_config:
        logger.error(json.dumps({
            "event":     "domain_registry_miss",
            "domain_id": domain_id,
            "fallback":  "DEFAULT_DOMAIN_CONFIG",
        }))
        return get_default_domain_config()

    config = copy.deepcopy(base_config)
    if config_overrides:
        config = _deep_merge(config, config_overrides)

    logger.info(json.dumps({
        "event":     "domain_config_loaded",
        "tenant_id": tenant_id,
        "domain_id": domain_id,
        "overrides_applied": bool(config_overrides),
    }))

    return config


# ---------------------------------------------------------------------------
# Convenience helpers (unchanged)
# ---------------------------------------------------------------------------

def build_taxonomy_string(domain_config: Dict[str, Any]) -> str:
    return " | ".join(domain_config.get("taxonomy", []))


def build_sla_bucket_string(domain_config: Dict[str, Any]) -> str:
    return " | ".join(domain_config.get("sla_rules", {}).keys())


def build_teams_string(domain_config: Dict[str, Any]) -> str:
    return ", ".join(domain_config.get("routing_teams", []))


def build_routing_matrix_json(domain_config: Dict[str, Any]) -> str:
    rules = domain_config.get("routing_rules", {})
    teams = domain_config.get("routing_teams", [])
    return json.dumps({
        "category_to_team": rules,
        "available_teams":  teams,
    }, indent=2)


def is_auto_send_permitted(
    domain_config: Optional[Dict[str, Any]],
    category: str,
) -> bool:
    if not domain_config:
        return False
    allowed      = domain_config.get("auto_send_allowed", False)
    allowed_cats = set(domain_config.get("auto_send_types", []))
    if not allowed:
        return False
    return category in allowed_cats


def get_extra_pii_patterns(domain_config: Dict[str, Any]) -> Dict[str, str]:
    return domain_config.get("compliance", {}).get("pii_extra_patterns", {})


def get_sla_seconds(domain_config: Dict[str, Any], priority: str) -> int:
    priority_map = domain_config.get("priority_to_sla", {})
    sla_tier     = priority_map.get(priority, "medium")
    sla_rules    = domain_config.get("sla_rules", {})
    rule         = sla_rules.get(sla_tier, {})
    return rule.get("bucket_seconds", 86400)


def get_escalation_threshold(domain_config: Dict[str, Any], priority: str) -> float:
    priority_map = domain_config.get("priority_to_sla", {})
    sla_tier     = priority_map.get(priority, "medium")
    sla_rules    = domain_config.get("sla_rules", {})
    rule         = sla_rules.get(sla_tier, {})
    return rule.get("escalate_at", 0.8)


def _deep_merge(base: dict, overrides: dict) -> dict:
    result = copy.deepcopy(base)
    for key, val in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = copy.deepcopy(val)
    return result
