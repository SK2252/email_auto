"""
utils/gmail_label_manager.py — Gmail Label Manager
AI-Powered Inbox Management System

All label configuration (hierarchy, colours, aliases, stale prefixes)
is defined in:  config/gmail_label.json

To add, rename, or remove labels — edit that JSON file only.
No changes needed in this file.

HOW GMAIL NESTING WORKS:
  Gmail builds visual nesting purely from "/" in label names.
  "IT Support/HR Team" appears as a child of "IT Support".
  Parent labels MUST be created before children — handled automatically.
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# JSON CONFIG PATH
# Resolved relative to this file so it works regardless of cwd.
# ---------------------------------------------------------------------------
_HERE        = os.path.dirname(os.path.abspath(__file__))
_CONFIG_PATH = os.path.join(_HERE, "..", "config", "gmail_label.json")

# ---------------------------------------------------------------------------
# CONFIG LOADER
# Parsed once at import time and cached — no repeated file I/O.
# ---------------------------------------------------------------------------
def _load_config() -> dict:
    """Load and return the parsed gmail_labels.json config."""
    path = os.path.normpath(_CONFIG_PATH)
    if not os.path.exists(path):
        # Fallback: look next to this file (for tests / flat layouts)
        path = os.path.join(_HERE, "gmail_labels.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        logger.debug(json.dumps({"event": "label_config_loaded", "path": path}))
        return cfg
    except FileNotFoundError:
        raise FileNotFoundError(
            f"gmail_label.json not found at {path}. "
            "Create config/gmail_label.json or place gmail_label.json next to this file."
        )
    except json.JSONDecodeError as exc:
        raise ValueError(f"gmail_labels.json contains invalid JSON: {exc}") from exc


_CFG = _load_config()


# ---------------------------------------------------------------------------
# BUILD FLAT STRUCTURES FROM JSON
# These mirror the old hardcoded dicts so all downstream code is unchanged.
# ---------------------------------------------------------------------------

def _build_hierarchy(labels: list) -> List[Tuple[str, List[str]]]:
    """
    Recursively flatten the nested JSON label tree into an ordered list of
    (parent_name, [child_names]) tuples.

    Order: parent always before its children, intermediate before leaves.
    This is the order Gmail requires for correct nesting.
    """
    result: List[Tuple[str, List[str]]] = []

    def walk(nodes: list) -> None:
        for node in nodes:
            name      = node["name"]
            children  = node.get("children", [])
            child_names = [c["name"] for c in children]
            result.append((name, child_names))
            if children:
                walk(children)          # recurse for grandchildren

    walk(labels)
    return result


def _build_color_map(labels: list) -> Dict[str, Dict[str, str]]:
    """Flatten nested JSON into {label_name: {backgroundColor, textColor}}."""
    colors: Dict[str, Dict[str, str]] = {}

    def walk(nodes: list) -> None:
        for node in nodes:
            if "color" in node:
                colors[node["name"]] = node["color"]
            if "children" in node:
                walk(node["children"])

    walk(labels)
    return colors


# Build once at import — used by all functions below
LABEL_HIERARCHY: List[Tuple[str, List[str]]] = _build_hierarchy(_CFG["labels"])
LABEL_COLORS:    Dict[str, Dict[str, str]]   = _build_color_map(_CFG["labels"])
_LABEL_ALIAS:    Dict[str, str]              = {
    k: v for k, v in _CFG.get("alias_map", {}).items()
    if not k.startswith("_")            # skip _comment keys
}
_MANAGED_PREFIXES: Tuple[str, ...] = tuple(_CFG.get("stale_label_prefixes", []))


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

def bootstrap_labels(service: Any) -> Dict[str, str]:
    """
    Called once at startup from main.py.

    1. Reload config from JSON (picks up any edits since last boot).
    2. Delete all stale / previously-managed labels.
    3. Create parents → children → grandchildren in correct order.
    4. Return {label_name: gmail_label_id}.
    """
    # Reload config so hot-edits to gmail_labels.json take effect on next restart
    global LABEL_HIERARCHY, LABEL_COLORS, _LABEL_ALIAS, _MANAGED_PREFIXES
    cfg              = _load_config()
    LABEL_HIERARCHY  = _build_hierarchy(cfg["labels"])
    LABEL_COLORS     = _build_color_map(cfg["labels"])
    _LABEL_ALIAS     = {k: v for k, v in cfg.get("alias_map", {}).items() if not k.startswith("_")}
    _MANAGED_PREFIXES = tuple(cfg.get("stale_label_prefixes", []))

    logger.info(json.dumps({
        "event":          "label_bootstrap_started",
        "config_labels":  len(_all_label_names()),
        "alias_entries":  len(_LABEL_ALIAS),
    }))

    _delete_managed_labels(service)

    # Collect all label names in creation order (parents before children)
    all_labels: List[str] = []
    seen: set = set()
    for parent, children in LABEL_HIERARCHY:
        if parent not in seen:
            all_labels.append(parent)
            seen.add(parent)
        for child in children:
            if child not in seen:
                all_labels.append(child)
                seen.add(child)

    label_map: Dict[str, str] = {}
    for name in all_labels:
        label_id = _create_label(service, name)
        if label_id:
            label_map[name] = label_id
            logger.info(json.dumps({"event": "label_created", "label": name}))
        time.sleep(0.05)   # Gmail API rate-limit safety

    logger.info(json.dumps({
        "event":   "label_bootstrap_complete",
        "created": len(label_map),
    }))
    return label_map


def apply_classification_label(
    message_id: str,
    service: Any,
    email_type: str,
    routing_decision: Optional[str] = None,
    redis_client: Any = None,
) -> bool:
    """
    Apply the correct Gmail label to an email after classification.

    Resolution order:
      1. routing_decision is an exact full label path  → use directly
      2. routing_decision is a partial team name        → suffix-match
      3. email_type in alias_map (from JSON)            → mapped label
      4. email_type directly matches a label name       → use as-is
      5. Fallback                                       → Customer Support/Customer Issues
    """
    # Redis dedup — skip if already labeled in last 30 min
    if redis_client:
        try:
            if redis_client.get(f"label:{message_id}"):
                logger.info(json.dumps({"event": "label_skip_dedup", "message_id": message_id}))
                return True
        except Exception as exc:
            logger.warning(json.dumps({"event": "redis_error", "error": str(exc)}))

    target = _resolve_label(email_type, routing_decision)
    logger.info(json.dumps({
        "event":      "label_apply",
        "message_id": message_id,
        "email_type": email_type,
        "routing":    routing_decision,
        "label":      target,
    }))

    try:
        all_gmail_labels = service.users().labels().list(userId="me").execute().get("labels", [])
        label_id = next(
            (l["id"] for l in all_gmail_labels if l["name"] == target), None
        )

        if not label_id:
            logger.error(json.dumps({
                "event": "label_not_found",
                "label": target,
                "note":  "Run bootstrap_labels() to recreate from gmail_labels.json",
            }))
            return False

        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"addLabelIds": [label_id]},
        ).execute()

        logger.info(json.dumps({
            "event":      "label_applied",
            "message_id": message_id,
            "label":      target,
        }))

        if redis_client:
            try:
                redis_client.setex(f"label:{message_id}", 1800, target)
            except Exception:
                pass

        return True

    except Exception as exc:
        logger.error(json.dumps({
            "event":      "label_apply_failed",
            "message_id": message_id,
            "label":      target,
            "error":      str(exc),
        }))
        return False


def get_label_for_category(
    email_type: str,
    routing_decision: Optional[str] = None,
) -> str:
    """Pure lookup — no API call. Useful for logging and unit tests."""
    return _resolve_label(email_type, routing_decision)


def setup_gmail_labels(service: Any, redis_client: Any = None) -> Dict[str, str]:
    """
    Entry point called from main.py at startup:

        from utils.gmail_label_manager import setup_gmail_labels
        label_map = setup_gmail_labels(gmail_service, redis_client)
    """
    return bootstrap_labels(service)


def reload_config() -> None:
    """
    Force-reload gmail_labels.json without restarting.
    Call this after editing the JSON file while the server is running.
    """
    global LABEL_HIERARCHY, LABEL_COLORS, _LABEL_ALIAS, _MANAGED_PREFIXES
    cfg               = _load_config()
    LABEL_HIERARCHY   = _build_hierarchy(cfg["labels"])
    LABEL_COLORS      = _build_color_map(cfg["labels"])
    _LABEL_ALIAS      = {k: v for k, v in cfg.get("alias_map", {}).items() if not k.startswith("_")}
    _MANAGED_PREFIXES = tuple(cfg.get("stale_label_prefixes", []))
    logger.info(json.dumps({
        "event":   "label_config_reloaded",
        "labels":  len(_all_label_names()),
        "aliases": len(_LABEL_ALIAS),
    }))


# ---------------------------------------------------------------------------
# INTERNAL HELPERS
# ---------------------------------------------------------------------------

def _resolve_label(email_type: str, routing_decision: Optional[str]) -> str:
    valid = _all_label_names()

    # 1. Exact full path
    if routing_decision and routing_decision in valid:
        return routing_decision

    # 2. Partial suffix match
    if routing_decision:
        for label in valid:
            if label.endswith(routing_decision) and "/" in label:
                return label

    # 3. Alias map lookup (loaded from JSON)
    key = (email_type or "").lower().strip().replace(" ", "_").replace("-", "_")
    if key in _LABEL_ALIAS:
        return _LABEL_ALIAS[key]

    # 4. Direct name match
    if email_type in valid:
        return email_type

    # 5. Fallback
    logger.warning(json.dumps({
        "event":      "label_fallback",
        "email_type": email_type,
        "routing":    routing_decision,
    }))
    return "Customer Support/Customer Issues"


def _all_label_names() -> set:
    names: set = set()
    for parent, children in LABEL_HIERARCHY:
        names.add(parent)
        names.update(children)
    return names


def _create_label(service: Any, label_name: str) -> Optional[str]:
    body: Dict[str, Any] = {
        "name":                  label_name,
        "labelListVisibility":   "labelShow",
        "messageListVisibility": "show",
    }
    if label_name in LABEL_COLORS:
        body["color"] = LABEL_COLORS[label_name]

    try:
        return service.users().labels().create(
            userId="me", body=body
        ).execute().get("id")
    except Exception as exc:
        err = str(exc)
        if "already exists" in err.lower() or "409" in err:
            return _get_existing_label_id(service, label_name)
        logger.error(json.dumps({
            "event": "label_create_failed",
            "label": label_name,
            "error": err,
        }))
        return None


def _get_existing_label_id(service: Any, label_name: str) -> Optional[str]:
    try:
        for label in service.users().labels().list(userId="me").execute().get("labels", []):
            if label["name"] == label_name:
                return label["id"]
    except Exception as exc:
        logger.error(json.dumps({
            "event": "label_lookup_failed",
            "label": label_name,
            "error": str(exc),
        }))
    return None


def _delete_managed_labels(service: Any) -> int:
    """
    Delete all labels whose names start with a managed prefix.
    Sorted deepest-first to avoid Gmail's 'parent has children' error.
    """
    try:
        all_labels = service.users().labels().list(userId="me").execute().get("labels", [])
    except Exception as exc:
        logger.error(json.dumps({"event": "label_list_failed", "error": str(exc)}))
        return 0

    managed = [
        l for l in all_labels
        if any(l["name"].startswith(p) for p in _MANAGED_PREFIXES)
        and l.get("type") != "system"
    ]
    managed.sort(key=lambda l: l["name"].count("/"), reverse=True)

    deleted = 0
    for label in managed:
        try:
            service.users().labels().delete(userId="me", id=label["id"]).execute()
            deleted += 1
            logger.info(json.dumps({"event": "label_deleted", "label": label["name"]}))
            time.sleep(0.05)
        except Exception as exc:
            logger.warning(json.dumps({
                "event": "label_delete_failed",
                "label": label["name"],
                "error": str(exc),
            }))

    logger.info(json.dumps({"event": "cleanup_done", "deleted": deleted}))
    return deleted