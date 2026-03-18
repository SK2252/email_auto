"""
Gmail Label Manager — 2-Level Type/Priority Classification.
Sprint 10: Robust Idempotency & Duplicate Prevention.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
import redis

# Centrally managed settings
import os
import sys

# Ensure enterprise-mcp-server is in path for 'app' imports
mcp_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "enterprise-mcp-server")
if mcp_path not in sys.path:
    sys.path.insert(0, mcp_path)

from config.settings import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Label Definitions & Mappings
# ---------------------------------------------------------------------------

CATEGORIES = [
    "Billing", "IT Support", "HR", "Complaint", 
    "Query", "Escalation", "Other"
]

PRIORITIES = ["High", "Medium", "Low"]

TYPE_DISPLAY = {
    "billing":      "Billing",
    "it":           "IT Support",
    "hr":           "HR",
    "complaint":    "Complaint",
    "query":        "Query",
    "info_request": "Query",
    "escalation":   "Escalation",
    "other":        "Other",
}

# Legacy aliases — old LLM category names that no longer exist in taxonomy.
# These map stale LLM responses to correct TYPE_DISPLAY keys
# so they never silently fall through to Other/Medium.
_LEGACY_ALIAS: Dict[str, str] = {
    # Old/stale category names
    "inquiry":         "query",
    "technical_issue": "it",
    "technical":       "it",
    "spam":            "other",
    "general":         "query",
    "hr_issue":        "hr",
    "finance":         "billing",
    "payment":         "billing",
    "refund":          "billing",
    
    # Domain-specific IT Support taxonomy
    "password_reset":      "it",
    "hardware_issue":      "it",
    "software_bug":        "it",
    "access_request":      "it",
    "network_issue":       "it",
    "onboarding":          "it",
    "security_incident":   "it",
    # FIX: general_query was wrongly mapped to "it" — correct is "query"
    "general_query":       "query",
    "general_inquiry":     "query",
    "pricing_inquiry":     "query",
    "product_inquiry":     "query",
    "support_request":     "query",
    "account_query":       "query",
    "service_query":       "query",
    "information_request": "query",
    "follow_up":           "query",
    # Billing extras
    "invoice":             "billing",
    "subscription":        "billing",
    "charge":              "billing",
    "overcharge":          "billing",
    # HR extras
    "leave":               "hr",
    "payroll":             "hr",
    "benefits":            "hr",
    # Complaint extras
    "negative_feedback":   "complaint",
    "dissatisfied":        "complaint",
    
    # Additional common variations and typos
    "tech_support":        "it",
    "technical_support":   "it",
    "it_support":          "it",
    "it_issue":            "it",
    "system_issue":        "it",
    "login_issue":         "it",
    "vpn_issue":           "it",
    "email_issue":         "it",
    
    # Billing variations
    "payment_issue":       "billing",
    "billing_issue":       "billing",
    "invoice_issue":       "billing",
    "charge_issue":        "billing",
    "refund_issue":        "billing",
    
    # HR variations
    "hr_query":            "hr",
    "hr_request":          "hr",
    "employee_issue":      "hr",
    "workplace_issue":     "hr",
    
    # Complaint variations
    "customer_complaint":  "complaint",
    "service_complaint":   "complaint",
    "product_complaint":   "complaint",
    "unhappy":             "complaint",
    "frustrated":          "complaint",
    
    # Query variations
    "question":            "query",
    "inquiry":             "query",
    "request":             "query",
    "help":                "query",
    "assistance":          "query",
    
    # Escalation variations
    "urgent":              "escalation",
    "critical":            "escalation",
    "emergency":           "escalation",
    "ceo_escalation":      "escalation",
    "executive_escalation":"escalation",
}

PRIORITY_DISPLAY = {
    "high":     "High",
    "medium":   "Medium",
    "low":      "Low"
}

# ---------------------------------------------------------------------------
# In-Process Cache
# ---------------------------------------------------------------------------

_label_cache: Dict[str, str] = {}
_managed_label_ids: List[str] = []

# ---------------------------------------------------------------------------
# Helper: Patch Label Colors
# ---------------------------------------------------------------------------

def _patch_label_color(service, user_id: str, label_id: str, label_name: str) -> None:
    """
    Apply color to an existing Gmail label using the patch() method.
    Works for both parent labels (Billing, IT Support, etc.) and existing labels.
    """
    try:
        from app.infrastructure.external.gmail_client import execute_gmail_api
    except ImportError:
        from enterprise_mcp_server.app.infrastructure.external.gmail_client import execute_gmail_api

    LABEL_COLORS = {
        "Billing":    {"backgroundColor": "#4986e7", "textColor": "#ffffff"},
        "IT Support": {"backgroundColor": "#a479e2", "textColor": "#ffffff"},
        "HR":         {"backgroundColor": "#16a765", "textColor": "#ffffff"},
        "Complaint":  {"backgroundColor": "#fb4c2f", "textColor": "#ffffff"},
        "Query":      {"backgroundColor": "#ffad47", "textColor": "#000000"},
        "Escalation": {"backgroundColor": "#cc3a21", "textColor": "#ffffff"},
        "Other":      {"backgroundColor": "#cccccc", "textColor": "#000000"},
    }

    # Extract parent category from label (e.g., "Billing" from "Billing/High")
    parent = label_name.split("/")[0] if "/" in label_name else label_name
    
    if parent not in LABEL_COLORS:
        return

    try:
        execute_gmail_api(
            service.users().labels().patch(
                userId=user_id,
                id=label_id,
                body={"color": LABEL_COLORS[parent]}
            )
        )
        logger.info(f"Color patched for '{label_name}' ({parent})")
    except Exception as e:
        logger.warning(f"Failed to patch color for '{label_name}': {e}")

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

async def bootstrap_labels(gmail_user_id: str = "me") -> None:
    """
    Ensure all 28 labels exist in Gmail and apply colors to all of them.
    """
    # Import here to avoid circular imports
    try:
        from app.infrastructure.external.gmail_client import (
            get_gmail_service,
            execute_gmail_api,
        )
    except ImportError:
        from enterprise_mcp_server.app.infrastructure.external.gmail_client import (
            get_gmail_service,
            execute_gmail_api,
        )

    service = get_gmail_service()
    resp = execute_gmail_api(service.users().labels().list(userId=gmail_user_id))
    existing: Dict[str, str] = {
        lbl["name"]: lbl["id"] for lbl in resp.get("labels", [])
    }
    
    _label_cache.clear()
    _managed_label_ids.clear()
    _label_cache.update(existing)

    for cat in CATEGORIES:
        if cat not in existing:
            body = {"name": cat}
            lbl = execute_gmail_api(service.users().labels().create(
                userId=gmail_user_id, body=body
            ))
            _label_cache[cat] = lbl["id"]
        
        # Apply or patch colors for ALL category labels (both new and existing)
        _patch_label_color(service, gmail_user_id, _label_cache[cat], cat)
        _managed_label_ids.append(_label_cache[cat])

        for prio in PRIORITIES:
            full_name = f"{cat}/{prio}"
            if full_name not in existing:
                lbl = execute_gmail_api(service.users().labels().create(
                    userId=gmail_user_id, body={"name": full_name}
                ))
                _label_cache[full_name] = lbl["id"]
            _managed_label_ids.append(_label_cache[full_name])

    logger.info(f"Bootstrap complete. {len(_managed_label_ids)} labels managed. Colors applied.")

# ---------------------------------------------------------------------------
# Apply Label
# ---------------------------------------------------------------------------

async def apply_classification_label(
    message_id: str,
    service: Any,
    email_type: str,
    priority: str,
    redis_client: redis.Redis,
    user_id: str = "me"
) -> bool:
    """
    Applies classification label with 3-layer prevention.
    """
    try:
        from app.infrastructure.external.gmail_client import execute_gmail_api
    except ImportError:
        from enterprise_mcp_server.app.infrastructure.external.gmail_client import execute_gmail_api

    normalised = email_type.lower().strip()
    if normalised not in TYPE_DISPLAY and normalised in _LEGACY_ALIAS:
        mapped = _LEGACY_ALIAS[normalised]
        logger.warning(json.dumps({
            "event":    "label_category_mapped",
            "original": email_type,
            "mapped":   mapped,
            "action":   "Domain-specific or legacy category mapped to parent domain",
        }))
        normalised = mapped
    elif normalised not in TYPE_DISPLAY:
        logger.error(json.dumps({
            "event":    "label_unknown_category",
            "category": email_type,
            "action":   "falling back to Other — add to TYPE_DISPLAY or fix prompt",
        }))

    target_type       = TYPE_DISPLAY.get(normalised, "Other")
    target_prio       = PRIORITY_DISPLAY.get(priority.lower(), "Medium")
    target_label_name = f"{target_type}/{target_prio}"
    
    target_label_id = _label_cache.get(target_label_name)
    if not target_label_id:
        # On-the-fly fetch if cache missed (e.g. worker restarted)
        resp = execute_gmail_api(service.users().labels().list(userId=user_id))
        for lbl in resp.get("labels", []):
            _label_cache[lbl["name"]] = lbl["id"]
        target_label_id = _label_cache.get(target_label_name)

    if not target_label_id:
        return False

    # LAYER 1: Redis Lock
    lock_key = f"label_lock:{message_id}"
    if not redis_client.set(lock_key, "locked", nx=True, ex=30):
        return False

    try:
        msg = execute_gmail_api(service.users().messages().get(
            userId=user_id, id=message_id, format="minimal"
        ))
        current_labels = msg.get("labelIds", [])

        # LAYER 3: Idempotency
        managed_on_msg = [l for l in current_labels if l in _managed_label_ids]
        if len(managed_on_msg) == 1 and target_label_id in managed_on_msg:
            return True

        # LAYER 2: Strip and Apply
        execute_gmail_api(service.users().messages().modify(
            userId=user_id,
            id=message_id,
            body={
                "addLabelIds":    [target_label_id],
                "removeLabelIds": managed_on_msg,
            }
        ))

        logger.info(json.dumps({
            "event":          "label_applied",
            "message_id":     message_id,
            "label":          target_label_name,
            "email_type_raw": email_type,
            "priority_raw":   priority,
        }))
        return True
    except Exception as e:
        logger.error(f"Failed to apply label {target_label_name} to {message_id}: {e}")
        return False