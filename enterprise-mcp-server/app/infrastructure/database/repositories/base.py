"""
Data access layer for API key management.
All database operations go through this repository.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.database.models import (
    ApiKey,
    ApiKeyPermission,
    ApiKeyStatusEnum,
    ApiKeyUsage,
    ToolPermission,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

# ─── Helpers ──────────────────────────────────────────────────────────────────

KEY_PREFIX = "mcp_sk_"


def hash_key(raw_key: str) -> str:
    """SHA-256 hash of raw API key."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def generate_raw_key() -> str:
    """Generate a cryptographically secure API key."""
    return KEY_PREFIX + secrets.token_urlsafe(48)


# ─── Repository ──────────────────────────────────────────────────────────────


class ApiKeyRepository:
    """CRUD operations for API keys, permissions, and usage tracking."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ── Lookup ────────────────────────────────────────────────────────────

    async def get_by_hash(self, key_hash: str) -> Optional[ApiKey]:
        """Lookup API key by its hash. Eager-loads permissions."""
        stmt = (
            select(ApiKey)
            .options(selectinload(ApiKey.permissions))
            .where(ApiKey.key_hash == key_hash)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, key_id: str) -> Optional[ApiKey]:
        """Lookup API key by UUID. Eager-loads permissions."""
        stmt = (
            select(ApiKey)
            .options(selectinload(ApiKey.permissions))
            .where(ApiKey.id == key_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ── Create ────────────────────────────────────────────────────────────

    async def create_key(
        self,
        owner: str,
        scopes: List[str],
        description: Optional[str] = None,
        environment: str = "development",
        rate_limit: int = 60,
        expires_in_days: Optional[int] = None,
        granted_by: Optional[str] = None,
    ) -> Tuple[str, ApiKey]:
        """
        Create a new API key.
        Returns (raw_key, db_record). The raw key is shown only once.
        """
        raw_key = generate_raw_key()
        key_hash_value = hash_key(raw_key)
        prefix = raw_key[:12]  # "mcp_sk_" + first 5 chars

        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(
                days=expires_in_days
            )

        api_key = ApiKey(
            key_prefix=prefix,
            key_hash=key_hash_value,
            owner=owner,
            description=description,
            environment=environment,
            rate_limit=rate_limit,
            status=ApiKeyStatusEnum.ACTIVE,
            expires_at=expires_at,
        )

        # Add permissions
        for scope in scopes:
            api_key.permissions.append(
                ApiKeyPermission(
                    scope=scope,
                    granted_by=granted_by or owner,
                )
            )

        self.session.add(api_key)
        await self.session.flush()

        logger.info(
            "API key created",
            key_id=api_key.id,
            owner=owner,
            scopes=scopes,
            environment=environment,
        )

        return raw_key, api_key

    # ── Revoke ────────────────────────────────────────────────────────────

    async def revoke_key(
        self, key_id: str, reason: str = "Manual revocation"
    ) -> Optional[ApiKey]:
        """Revoke an API key. Returns updated key or None if not found."""
        api_key = await self.get_by_id(key_id)
        if not api_key:
            return None

        api_key.status = ApiKeyStatusEnum.REVOKED
        api_key.revoked_at = datetime.now(timezone.utc)
        api_key.revoked_reason = reason

        logger.info(
            "API key revoked",
            key_id=key_id,
            reason=reason,
        )

        return api_key

    # ── Rotate ────────────────────────────────────────────────────────────

    async def rotate_key(
        self,
        old_key_id: str,
        grace_hours: int = 72,
        granted_by: Optional[str] = None,
    ) -> Optional[Tuple[str, ApiKey]]:
        """
        Rotate an API key:
        1. Create a new key with same owner/scopes/rate_limit
        2. Set old key status to 'rotating' with grace window
        Returns (new_raw_key, new_api_key) or None if old key not found.
        """
        old_key = await self.get_by_id(old_key_id)
        if not old_key or old_key.status != ApiKeyStatusEnum.ACTIVE:
            return None

        # Get existing scopes
        existing_scopes = [p.scope for p in old_key.permissions]

        # Create replacement key
        raw_key, new_key = await self.create_key(
            owner=old_key.owner,
            scopes=existing_scopes,
            description=f"Rotation of {old_key.key_prefix}",
            environment=old_key.environment,
            rate_limit=old_key.rate_limit,
            granted_by=granted_by,
        )

        # Mark old key as rotating
        old_key.status = ApiKeyStatusEnum.ROTATING
        old_key.rotation_id = new_key.id
        old_key.rotation_expires_at = datetime.now(
            timezone.utc
        ) + timedelta(hours=grace_hours)

        logger.info(
            "API key rotation started",
            old_key_id=old_key_id,
            new_key_id=new_key.id,
            grace_hours=grace_hours,
        )

        return raw_key, new_key

    # ── List ──────────────────────────────────────────────────────────────

    async def list_keys(
        self,
        owner: Optional[str] = None,
        status: Optional[ApiKeyStatusEnum] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ApiKey]:
        """List API keys with optional filters. Eager-loads permissions."""
        stmt = (
            select(ApiKey)
            .options(selectinload(ApiKey.permissions))
            .order_by(ApiKey.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        if owner:
            stmt = stmt.where(ApiKey.owner == owner)
        if status:
            stmt = stmt.where(ApiKey.status == status)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ── Update ────────────────────────────────────────────────────────────

    async def update_permissions(
        self,
        key_id: str,
        scopes: List[str],
        granted_by: Optional[str] = None,
    ) -> Optional[ApiKey]:
        """Replace all permissions for a key with new scopes."""
        api_key = await self.get_by_id(key_id)
        if not api_key:
            return None

        # Clear existing permissions
        api_key.permissions.clear()

        # Add new permissions
        for scope in scopes:
            api_key.permissions.append(
                ApiKeyPermission(scope=scope, granted_by=granted_by)
            )

        logger.info(
            "API key permissions updated",
            key_id=key_id,
            scopes=scopes,
        )

        return api_key

    async def update_rate_limit(
        self, key_id: str, rate_limit: int
    ) -> Optional[ApiKey]:
        """Update the per-key rate limit."""
        api_key = await self.get_by_id(key_id)
        if not api_key:
            return None

        api_key.rate_limit = rate_limit
        logger.info(
            "API key rate limit updated",
            key_id=key_id,
            rate_limit=rate_limit,
        )

        return api_key

    # ── Usage Tracking ────────────────────────────────────────────────────

    async def track_usage(
        self,
        api_key_id: str,
        endpoint: str,
        status_code: int,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        tool_name: Optional[str] = None,
        response_time_ms: Optional[float] = None,
    ) -> None:
        """Record a usage event. Fire-and-forget (non-blocking)."""
        usage = ApiKeyUsage(
            api_key_id=api_key_id,
            endpoint=endpoint,
            tool_name=tool_name,
            source_ip=source_ip,
            user_agent=user_agent,
            status_code=status_code,
            response_time_ms=response_time_ms,
        )
        self.session.add(usage)

    async def update_last_used(
        self, key_id: str, ip: Optional[str] = None
    ) -> None:
        """Touch last_used_at and last_used_ip for activity tracking."""
        stmt = (
            update(ApiKey)
            .where(ApiKey.id == key_id)
            .values(
                last_used_at=datetime.now(timezone.utc),
                last_used_ip=ip,
            )
        )
        await self.session.execute(stmt)

    # ── Maintenance ───────────────────────────────────────────────────────

    async def expire_rotating_keys(self) -> int:
        """
        Auto-revoke keys whose rotation grace window has expired.
        Returns count of revoked keys.
        """
        now = datetime.now(timezone.utc)
        stmt = (
            update(ApiKey)
            .where(
                ApiKey.status == ApiKeyStatusEnum.ROTATING,
                ApiKey.rotation_expires_at <= now,
            )
            .values(
                status=ApiKeyStatusEnum.REVOKED,
                revoked_at=now,
                revoked_reason="Rotation grace window expired",
            )
        )
        result = await self.session.execute(stmt)
        count = result.rowcount
        if count > 0:
            logger.info("Expired rotating keys", count=count)
        return count

    # ── Tool Permissions ──────────────────────────────────────────────────

    async def get_tool_permissions(self) -> Dict[str, List[str]]:
        """
        Load scope → tool_name mappings.
        Returns dict like {'document': ['merge_template', 'convert_to_pdf'], ...}
        """
        stmt = select(ToolPermission)
        result = await self.session.execute(stmt)
        rows = result.scalars().all()

        mapping: Dict[str, List[str]] = {}
        for row in rows:
            mapping.setdefault(row.scope, []).append(row.tool_name)

        return mapping
