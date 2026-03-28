"""
app/api/routers/v1/rules.py
REST endpoints for the rules engine UI.
PUT invalidates Redis so next email picks up new rules immediately.
"""
from __future__ import annotations
import json
import logging
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.engine import get_session
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rules", tags=["rules"])

VALID_OPERATORS = {
    "is","is_not","in","not_in",
    "contains","starts_with",
    "greater_than","less_than",
}
VALID_ACTIONS = {
    "route_to","set_sla","send_ack",
    "notify_slack","notify_email",
    "hold_for_review","apply_label",
}

class Condition(BaseModel):
    field:    str
    operator: str
    value:    Any

    @field_validator("operator")
    @classmethod
    def valid_op(cls, v: str) -> str:
        if v not in VALID_OPERATORS:
            raise ValueError(f"Invalid operator '{v}'")
        return v

class Action(BaseModel):
    action: str
    value:  Any

    @field_validator("action")
    @classmethod
    def valid_action(cls, v: str) -> str:
        if v not in VALID_ACTIONS:
            raise ValueError(f"Invalid action '{v}'")
        return v

class Rule(BaseModel):
    name:          str
    priority:      str = "medium"
    domain:        str = "any"
    match_mode:    Literal["all", "any"] = "all"
    stop_on_match: bool = True
    active:        bool = True
    conditions:    list[Condition]
    actions:       list[Action]

class RulesPayload(BaseModel):
    rules: list[Rule]


async def _get_redis():
    import redis.asyncio as aioredis
    r = aioredis.from_url(
        f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}",
        decode_responses=True,
    )
    try:
        yield r
    finally:
        await r.aclose()


@router.get("/domains")
async def get_domains():
    from config.domains import DOMAIN_REGISTRY
    options = []
    
    # Map internal domain IDs to the actual Gmail parent labels
    domain_map = {
        "it_support": "IT Support",
        "hr": "HR",
        "billing": "Customer Support"
    }
    
    for d in DOMAIN_REGISTRY.keys():
        if d == "default":
            continue
        formatted = domain_map.get(d, d.replace("_", " ").title())
        options.append(formatted)
        
    return {"domains": options}


@router.get("/{tenant_id}")
async def get_rules(
    tenant_id: str,
    db: AsyncSession = Depends(get_session),
):
    row = (await db.execute(
        text("SELECT id, version, rules_json, created_at, created_by "
             "FROM rules_versions "
             "WHERE tenant_id=:tid AND is_active=TRUE"),
        {"tid": tenant_id},
    )).fetchone()

    if not row:
        return {"tenant_id": tenant_id, "version": 0, "rules": []}

    return {
        "tenant_id":  tenant_id,
        "version":    row.version,
        "created_at": str(row.created_at),
        "created_by": row.created_by,
        "rules":      row.rules_json,
    }


@router.get("/{tenant_id}/versions")
async def get_versions(
    tenant_id: str,
    db: AsyncSession = Depends(get_session),
):
    rows = (await db.execute(
        text("SELECT id, version, created_at, created_by, is_active "
             "FROM rules_versions WHERE tenant_id=:tid ORDER BY version DESC"),
        {"tid": tenant_id},
    )).fetchall()
    return {"versions": [dict(r._mapping) for r in rows]}


@router.put("/{tenant_id}")
async def update_rules(
    tenant_id: str,
    payload: RulesPayload,
    db: AsyncSession = Depends(get_session),
    redis=Depends(_get_redis),
):
    rules_json = json.dumps([r.model_dump() for r in payload.rules])

    async with db.begin():
        # Deactivate current active version
        await db.execute(
            text("UPDATE rules_versions SET is_active=FALSE WHERE tenant_id=:tid"),
            {"tid": tenant_id},
        )
        # Insert new version as active
        await db.execute(
            text("""
                INSERT INTO rules_versions
                    (tenant_id, version, rules_json, created_by, is_active)
                VALUES (
                    :tid,
                    COALESCE(
                        (SELECT MAX(version)+1 FROM rules_versions WHERE tenant_id=:tid),
                        1
                    ),
                    CAST(:rules AS jsonb),
                    'ui',
                    TRUE
                )
            """),
            {"tid": tenant_id, "rules": rules_json},
        )

    # Invalidate Redis — next email auto-reloads from DB
    await redis.delete(f"rules:{tenant_id}")

    logger.info(json.dumps({
        "event":     "rules_updated",
        "tenant_id": tenant_id,
        "count":     len(payload.rules),
    }))
    return {
        "status":  "updated",
        "tenant":  tenant_id,
        "count":   len(payload.rules),
        "message": "Rules are live — next email will use updated rules",
    }


@router.post("/{tenant_id}/rollback/{version}")
async def rollback(
    tenant_id: str,
    version: int,
    db: AsyncSession = Depends(get_session),
    redis=Depends(_get_redis),
):
    async with db.begin():
        await db.execute(
            text("UPDATE rules_versions SET is_active=FALSE WHERE tenant_id=:tid"),
            {"tid": tenant_id},
        )
        result = await db.execute(
            text("UPDATE rules_versions SET is_active=TRUE "
                 "WHERE tenant_id=:tid AND version=:v"),
            {"tid": tenant_id, "v": version},
        )
        if result.rowcount == 0:
            raise HTTPException(404, f"Version {version} not found")

    await redis.delete(f"rules:{tenant_id}")
    return {"status": "rolled_back", "active_version": version}


@router.post("/{tenant_id}/test")
async def test_rules(
    tenant_id: str,
    email_context: dict,
    db: AsyncSession = Depends(get_session),
    redis=Depends(_get_redis),
):
    from app.infrastructure.database.engine import build_engine
    from utils.rules_engine import evaluate
    engine = build_engine()
    result = await evaluate(
        context=email_context,
        tenant_id=tenant_id,
        redis=redis,
        engine=engine,
    )
    return result or {"matched": False, "message": "No rule matched"}
