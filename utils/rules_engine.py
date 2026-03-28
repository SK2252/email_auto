"""
utils/rules_engine.py — Dynamic Rules Engine
Evaluates tenant rules from Redis/Postgres before static routing matrix.
Read order: Redis (fast) → Postgres (miss) → cache in Redis for 1 hour.
Returns None if no rules configured — zero impact on existing behaviour.
"""
from __future__ import annotations
import json
import logging
from typing import Any

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import text

logger = logging.getLogger(__name__)

VALID_OPERATORS = {
    "is", "is_not", "in", "not_in",
    "contains", "starts_with",
    "greater_than", "less_than",
}

VALID_ACTIONS = {
    "route_to", "set_sla", "send_ack",
    "notify_slack", "notify_email",
    "hold_for_review", "apply_label",
}


def _match_condition(cond: dict, ctx: dict) -> bool:
    field    = cond.get("field", "")
    operator = cond.get("operator", "is")
    expected = cond.get("value")
    actual   = ctx.get(field)

    if actual is None:
        return False

    match operator:
        case "is":
            return str(actual).lower() == str(expected).lower()
        case "is_not":
            return str(actual).lower() != str(expected).lower()
        case "in":
            return str(actual).lower() in [str(v).lower() for v in expected]
        case "not_in":
            return str(actual).lower() not in [str(v).lower() for v in expected]
        case "contains":
            return str(expected).lower() in str(actual).lower()
        case "starts_with":
            return str(actual).lower().startswith(str(expected).lower())
        case "greater_than":
            return float(actual) > float(expected)
        case "less_than":
            return float(actual) < float(expected)
        case _:
            logger.warning(json.dumps({
                "event":    "rules_engine_unknown_operator",
                "operator": operator,
            }))
            return False


async def load_rules(
    tenant_id: str,
    redis: aioredis.Redis,
    engine: AsyncEngine,
) -> list[dict]:
    cache_key = f"rules:{tenant_id}"

    try:
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning(json.dumps({
            "event": "rules_engine_redis_error", "error": str(e),
        }))

    try:
        async with engine.begin() as conn:
            row = (await conn.execute(
                text(
                    "SELECT rules_json FROM rules_versions "
                    "WHERE tenant_id = :tid AND is_active = TRUE LIMIT 1"
                ),
                {"tid": tenant_id},
            )).fetchone()
    except Exception as e:
        logger.error(json.dumps({
            "event": "rules_engine_db_error", "error": str(e),
        }))
        return []

    if not row:
        return []

    rules = row[0] if isinstance(row[0], list) else json.loads(row[0])

    try:
        await redis.setex(cache_key, 3600, json.dumps(rules))
    except Exception:
        pass

    return rules


async def evaluate(
    context: dict,
    tenant_id: str,
    redis: aioredis.Redis,
    engine: AsyncEngine,
) -> dict | None:
    rules = await load_rules(tenant_id, redis, engine)
    if not rules:
        return None

    priority_map = {"high": 0, "medium": 1, "low": 2}
    active_rules = sorted(
        [r for r in rules if r.get("active", True)],
        key=lambda r: priority_map.get(str(r.get("priority")).lower(), 3),
    )

    for rule in active_rules:
        conditions = rule.get("conditions", [])
        mode       = rule.get("match_mode", "all")
        results    = [_match_condition(c, context) for c in conditions]
        matched    = all(results) if mode == "all" else any(results)

        if matched:
            logger.info(json.dumps({
                "event":     "rules_engine_match",
                "rule":      rule["name"],
                "priority":  rule.get("priority", 99),
                "tenant_id": tenant_id,
                "category":  context.get("category"),
            }))
            return {
                "rule_name": rule["name"],
                "actions":   rule.get("actions", []),
                "stop":      rule.get("stop_on_match", True),
            }

    return None
