"""
Gmail Label Manager — 2-Level Type/Priority Classification.
Sprint 10: Robust Idempotency & Duplicate Prevention.

Labels: 7 categories x 4 labels each = 28 total.
Structure: {Category}/{Priority}
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
import redis

# Use app.core.config if available (Server context) or fallback
try:
    from app.core.config import settings
except ImportError:
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

TYPE_MAP = {
    "billing":      "Billing",
    "it":           "IT Support",
    "hr":           "HR",
    "complaint":    "Complaint",
    "query":        "Query",
    "info_request": "Query",
    "escalation":   "Escalation",
    "other":        "Other"
}

PRIORITY_MAP = {
    "high":     "High",
    "medium":   "Medium",
    "low":      "Low",
}

# ---------------------------------------------------------------------------
# In-Process Cache: label_name → label_id
# ---------------------------------------------------------------------------

_label_cache: Dict[str, str] = {}
_managed_label_ids: List[str] = []

def get_managed_label_ids() -> List[str]:
    """Return all label IDs that this system manages (for stripping)."""
    return _managed_label_ids


def get_ai_label_ids() -> List[str]:
    """Alias for auto_organize worker compatibility."""
    return get_managed_label_ids()


def get_label_name(category_key: str, priority_key: str) -> str:
    """
    Compatibility function for organize worker.
    Maps LLM keys to Sprint 10 '{Type}/{Priority}' format.
    """
    target_type = TYPE_MAP.get(category_key.lower(), "Other")
    target_prio = PRIORITY_MAP.get(priority_key.lower(), "Medium")
    return f"{target_type}/{target_prio}"


async def ensure_label(label_name: str, service: Any, user_id: str = "me") -> str:
    """
    Compatibility function. Returns ID for label_name, 
    fetching from Gmail if cache is cold.
    """
    from app.infrastructure.external.gmail_client import execute_gmail_api

    # Check cache first
    lbl_id = _label_cache.get(label_name)
    if lbl_id:
        return lbl_id
    
    # Cache miss: fetch from Gmail
    resp = execute_gmail_api(service.users().labels().list(userId=user_id))
    for lbl in resp.get("labels", []):
        _label_cache[lbl["name"]] = lbl["id"]
        if lbl["name"] not in _managed_label_ids and (
            lbl["name"] in CATEGORIES or "/" in lbl["name"]
        ):
             # Heuristic to re-populate managed list if needed
             _managed_label_ids.append(lbl["id"])
             
    return _label_cache.get(label_name, "")

# ---------------------------------------------------------------------------
# Bootstrap — Call once at startup (main.py)
# ---------------------------------------------------------------------------

async def bootstrap_labels(gmail_user_id: str = "me") -> None:
    """
    Ensure all 28 labels exist in Gmail.
    Safe to call multiple times — skips already-existing labels.
    """
    from app.infrastructure.external.gmail_client import (
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

    total_created = 0
    # Collect IDs for all labels we manage (even those already existing)
    for cat in CATEGORIES:
        # Parent labels
        if cat not in existing:
            lbl = execute_gmail_api(service.users().labels().create(
                userId=gmail_user_id, body={"name": cat}
            ))
            _label_cache[cat] = lbl["id"]
            total_created += 1
        _managed_label_ids.append(_label_cache[cat])

        # Child labels (Type/Priority)
        for prio in PRIORITIES:
            full_name = f"{cat}/{prio}"
            if full_name not in existing:
                lbl = execute_gmail_api(service.users().labels().create(
                    userId=gmail_user_id, body={"name": full_name}
                ))
                _label_cache[full_name] = lbl["id"]
                total_created += 1
            _managed_label_ids.append(_label_cache[full_name])

    logger.info(json.dumps({
        "event": "bootstrap_labels_complete",
        "labels_created": total_created,
        "total_managed": len(_managed_label_ids)
    }))

# ---------------------------------------------------------------------------
# Apply Label — Used in orchestrator.py
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
    Applies the correct classification label with 3-layer duplicate prevention.
    """
    from app.infrastructure.external.gmail_client import execute_gmail_api

    # Normalized Target Label
    target_type = TYPE_MAP.get(email_type.lower(), "Other")
    target_prio = PRIORITY_MAP.get(priority.lower(), "Medium")
    target_label_name = f"{target_type}/{target_prio}"
    
    target_label_id = _label_cache.get(target_label_name)
    if not target_label_id:
        logger.error(f"Target label '{target_label_name}' not found in cache. Run bootstrap.")
        return False

    # LAYER 1: Redis Lock (Distributed Guard)
    lock_key = f"label_lock:{message_id}"
    if not redis_client.set(lock_key, "locked", nx=True, ex=30):
        # Already being processed by another worker
        logger.info(json.dumps({"event": "label_apply_locked", "message_id": message_id}))
        return False

    try:
        # Fetch current labels for this message
        msg = execute_gmail_api(service.users().messages().get(
            userId=user_id, id=message_id, format="minimal"
        ))
        current_labels = msg.get("labelIds", [])

        # LAYER 3: Idempotency Check
        # If it has the target label AND no other managed labels, we are done
        managed_on_msg = [l for l in current_labels if l in _managed_label_ids]
        if len(managed_on_msg) == 1 and target_label_id in managed_on_msg:
            return True

        # LAYER 2: Remove ALL managed labels before applying
        # This prevents an email from ever having two AI labels
        remove_ids = managed_on_msg
        add_ids = [target_label_id]

        execute_gmail_api(service.users().messages().batchModify(
            userId=user_id,
            body={
                "ids": [message_id],
                "addLabelIds": add_ids,
                "removeLabelIds": remove_ids
            }
        ))

        logger.info(json.dumps({
            "event": "label_applied",
            "message_id": message_id,
            "label": target_label_name
        }))
        return True

    except Exception as e:
        logger.error(json.dumps({
            "event": "label_apply_failed",
            "message_id": message_id,
            "error": str(e)
        }))
        return False
    finally:
        # Note: We let the lock expire naturally or delete it if we succeeded early
        # For simplicity, let it expire (30s) to guard against rapid re-runs
        pass
