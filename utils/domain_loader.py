"""
utils/domain_loader.py — Domain Configuration Loader
Loads the correct domain config at runtime based on tenant_id.
Injects domain_config dict into LangGraph state at AG-01 intake.

Design:
  - Tenant → domain_id mapping lives in config/domains/__init__.DOMAIN_REGISTRY
    or, in production, in the DB tenants table (config_overrides JSONB).
  - Deep-merges per-tenant config_overrides on top of the base domain config.
  - Thread-safe, no global mutable state; creates new dict on each call.
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
# ---------------------------------------------------------------------------
_TENANT_DOMAIN_MAP: Dict[str, str] = {
    # Format: "tenant_id": "domain_id"
    "default":             "it_support",
    "acme_hospital":       "healthcare",
    "veridian_law":        "legal",
    "shopfast_ecom":       "ecommerce",
    "edu_central_uni":     "education",
    "payroll_corp":        "billing",
    "global_hr_svc":       "hr",
}


# ---------------------------------------------------------------------------
# DEFAULT_DOMAIN_CONFIG — safe fallback for unknown / unregistered tenants
# CRITICAL RULES (LOCKED — do not change without explicit approval):
#   auto_send_allowed = False ALWAYS for unknown domains
#   All unmatched types route to Team Lead queue
#   SLA = standard 4h / 8h / 24h / 48h buckets
# ---------------------------------------------------------------------------
DEFAULT_DOMAIN_CONFIG: Dict[str, Any] = {
    "domain_id":   "default",
    "taxonomy": [
        "billing", "complaint", "query",
        "info_request", "other",
    ],
    "sla_rules": {
        "high":     {"bucket_seconds": 14400,  "escalate_at": 0.8},  # 4h
        "medium":   {"bucket_seconds": 28800,  "escalate_at": 0.8},  # 8h
        "low":      {"bucket_seconds": 86400,  "escalate_at": 0.8},  # 24h
        "very_low": {"bucket_seconds": 172800, "escalate_at": 0.8},  # 48h
    },
    "routing_teams": {
        "billing":      "Finance Ops",
        "complaint":    "Customer Service Lead",
        "query":        "Customer Service",
        "info_request": "Customer Service",
        "other":        "Team Lead",  # always human
    },
    "compliance": {
        "standards": ["GDPR"],
        "pii_extra":  [],
    },
    "auto_send_allowed": False,   # SAFE DEFAULT — never auto-send to unknown tenant
    "auto_send_types":   [],
    "response_tone": "professional, helpful, neutral",
}


def get_default_domain_config() -> Dict[str, Any]:
    """Return a deep-copy of the DEFAULT_DOMAIN_CONFIG. Thread-safe."""
    return copy.deepcopy(DEFAULT_DOMAIN_CONFIG)


def get_domain_config(
    tenant_id: str,
    config_overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Load and return the domain config for a given tenant.

    Args:
        tenant_id:        Identifier for the tenant (maps to a domain_id).
        config_overrides: Optional per-tenant overrides (from DB tenants table).
                          Deep-merged on top of the base domain config.

    Returns:
        Full domain config dict. Falls back to DEFAULT_DOMAIN_CONFIG for
        unknown tenants — NEVER raises for unknown tenant_id.
    """
    domain_id = _TENANT_DOMAIN_MAP.get(tenant_id)

    if not domain_id:
        logger.warning(
            json.dumps({
                "event":     "unknown_tenant_fallback",
                "tenant_id": tenant_id,
                "action":    "returning DEFAULT_DOMAIN_CONFIG — safe fallback",
                "auto_send_allowed": False,
                "routed_to": "Team Lead queue",
            })
        )
        config = get_default_domain_config()
        if config_overrides:
            config = _deep_merge(config, config_overrides)
        return config

    base_config = DOMAIN_REGISTRY.get(domain_id)
    if not base_config:
        logger.error(
            json.dumps({
                "event":     "domain_registry_miss",
                "domain_id": domain_id,
                "fallback":  "DEFAULT_DOMAIN_CONFIG",
            })
        )
        return get_default_domain_config()

    # Deep-copy so callers can't mutate the shared registry
    config = copy.deepcopy(base_config)

    # Apply per-tenant overrides (shallow merge at top level by default)
    if config_overrides:
        config = _deep_merge(config, config_overrides)

    logger.info(
        json.dumps({
            "event":     "domain_config_loaded",
            "tenant_id": tenant_id,
            "domain_id": domain_id,
            "overrides_applied": bool(config_overrides),
        })
    )

    return config


def build_taxonomy_string(domain_config: Dict[str, Any]) -> str:
    """Convenience: returns taxonomy as a pipe-separated string for prompts."""
    return " | ".join(domain_config.get("taxonomy", []))


def build_sla_bucket_string(domain_config: Dict[str, Any]) -> str:
    """Convenience: returns available SLA bucket names for prompts."""
    return " | ".join(domain_config.get("sla_rules", {}).keys())


def build_teams_string(domain_config: Dict[str, Any]) -> str:
    """Convenience: returns routing teams as a comma-separated string."""
    return ", ".join(domain_config.get("routing_teams", []))


def build_routing_matrix_json(domain_config: Dict[str, Any]) -> str:
    """Convenience: JSON string of routing_rules for Gemini fallback prompt."""
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
    """
    Returns True only when BOTH conditions are met:
      1. domain_config["auto_send_allowed"] is True
      2. category is in domain_config["auto_send_types"]

    SAFE DEFAULT: returns False for None/unknown domain.
    Healthcare and Legal always return False regardless of category.
    """
    if not domain_config:
        return False   # SAFE DEFAULT — never auto-send for unknown domains

    allowed      = domain_config.get("auto_send_allowed", False)
    allowed_cats = set(domain_config.get("auto_send_types", []))

    if not allowed:
        return False

    return category in allowed_cats


def get_extra_pii_patterns(domain_config: Dict[str, Any]) -> Dict[str, str]:
    """
    Returns domain-specific regex PII patterns to be added to the scanner.
    Merges with the base patterns in utils/pii_scanner.py.
    """
    return domain_config.get("compliance", {}).get("pii_extra_patterns", {})


def get_sla_seconds(domain_config: Dict[str, Any], priority: str) -> int:
    """
    Maps a priority string to a SLA bucket duration in seconds.

    Args:
        domain_config: Loaded domain config dict.
        priority:      Priority from classification result (high / medium / low / ...)

    Returns:
        SLA duration in seconds, defaults to 86400 (24h) if not found.
    """
    priority_map = domain_config.get("priority_to_sla", {})
    sla_tier     = priority_map.get(priority, "normal")
    sla_rules    = domain_config.get("sla_rules", {})
    rule         = sla_rules.get(sla_tier, {})
    return rule.get("bucket_seconds", 86400)


def get_escalation_threshold(domain_config: Dict[str, Any], priority: str) -> float:
    """
    Returns the escalation threshold (fraction of SLA elapsed) for a priority tier.
    Defaults to 0.8 if not defined.
    """
    priority_map = domain_config.get("priority_to_sla", {})
    sla_tier     = priority_map.get(priority, "normal")
    sla_rules    = domain_config.get("sla_rules", {})
    rule         = sla_rules.get(sla_tier, {})
    return rule.get("escalate_at", 0.8)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _deep_merge(base: dict, overrides: dict) -> dict:
    """
    Recursively merge `overrides` into `base`.
    Lists are replaced (not appended) by the override value.
    """
    result = copy.deepcopy(base)
    for key, val in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = copy.deepcopy(val)
    return result
