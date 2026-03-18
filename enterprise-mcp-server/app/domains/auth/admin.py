"""
Admin service for API key lifecycle management.
Key generation, revocation, rotation, and permission CRUD.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.infrastructure.database.models import ApiKey, ApiKeyStatusEnum
from app.infrastructure.database.repositories.base import ApiKeyRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


# ─── Request/Response Schemas ────────────────────────────────────────────────


class CreateKeyRequest(BaseModel):
    owner: str
    scopes: List[str] = Field(min_length=1)
    description: Optional[str] = None
    environment: str = "development"
    rate_limit: int = Field(default=60, ge=1, le=10000)
    expires_in_days: Optional[int] = Field(default=None, ge=1)


class RotateKeyRequest(BaseModel):
    grace_hours: int = Field(default=72, ge=1, le=720)


class UpdateKeyRequest(BaseModel):
    scopes: Optional[List[str]] = None
    rate_limit: Optional[int] = Field(default=None, ge=1, le=10000)
    description: Optional[str] = None


class RevokeKeyRequest(BaseModel):
    reason: str = "Manual revocation"


class KeyResponse(BaseModel):
    id: str
    key_prefix: str
    owner: str
    status: str
    environment: str
    rate_limit: int
    scopes: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    revoked_reason: Optional[str] = None
    rotation_id: Optional[str] = None
    rotation_expires_at: Optional[datetime] = None
    description: Optional[str] = None


class CreateKeyResponse(KeyResponse):
    raw_key: str  # Only shown once


# ─── Admin Service ───────────────────────────────────────────────────────────


class AdminService:
    """Business logic for API key administration."""

    def __init__(self, repo: ApiKeyRepository):
        self.repo = repo

    def _key_to_response(self, api_key: ApiKey) -> KeyResponse:
        """Convert ORM model to response schema."""
        return KeyResponse(
            id=api_key.id,
            key_prefix=api_key.key_prefix,
            owner=api_key.owner,
            status=api_key.status.value,
            environment=api_key.environment,
            rate_limit=api_key.rate_limit,
            scopes=[p.scope for p in api_key.permissions],
            created_at=api_key.created_at,
            expires_at=api_key.expires_at,
            last_used_at=api_key.last_used_at,
            revoked_at=api_key.revoked_at,
            revoked_reason=api_key.revoked_reason,
            rotation_id=api_key.rotation_id,
            rotation_expires_at=api_key.rotation_expires_at,
            description=api_key.description,
        )

    async def create_key(
        self, req: CreateKeyRequest, granted_by: Optional[str] = None
    ) -> CreateKeyResponse:
        """Generate a new API key. Raw key is returned only once."""
        raw_key, api_key = await self.repo.create_key(
            owner=req.owner,
            scopes=req.scopes,
            description=req.description,
            environment=req.environment,
            rate_limit=req.rate_limit,
            expires_in_days=req.expires_in_days,
            granted_by=granted_by,
        )

        return CreateKeyResponse(
            raw_key=raw_key,
            **self._key_to_response(api_key).model_dump(),
        )

    async def revoke_key(
        self, key_id: str, reason: str = "Manual revocation"
    ) -> Optional[KeyResponse]:
        """Revoke an API key."""
        api_key = await self.repo.revoke_key(key_id, reason)
        if not api_key:
            return None
        return self._key_to_response(api_key)

    async def rotate_key(
        self, key_id: str, grace_hours: int = 72, granted_by: Optional[str] = None
    ) -> Optional[CreateKeyResponse]:
        """Rotate an API key. Returns the new key's raw value."""
        result = await self.repo.rotate_key(key_id, grace_hours, granted_by)
        if not result:
            return None

        raw_key, new_key = result
        return CreateKeyResponse(
            raw_key=raw_key,
            **self._key_to_response(new_key).model_dump(),
        )

    async def get_key(self, key_id: str) -> Optional[KeyResponse]:
        """Get key details by ID."""
        api_key = await self.repo.get_by_id(key_id)
        if not api_key:
            return None
        return self._key_to_response(api_key)

    async def list_keys(
        self,
        owner: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[KeyResponse]:
        """List API keys with optional filters."""
        status_enum = None
        if status:
            try:
                status_enum = ApiKeyStatusEnum(status)
            except ValueError:
                pass

        keys = await self.repo.list_keys(
            owner=owner, status=status_enum, limit=limit, offset=offset
        )
        return [self._key_to_response(k) for k in keys]

    async def update_key(
        self, key_id: str, req: UpdateKeyRequest, granted_by: Optional[str] = None
    ) -> Optional[KeyResponse]:
        """Update key permissions and/or rate limit."""
        api_key = None

        if req.scopes is not None:
            api_key = await self.repo.update_permissions(
                key_id, req.scopes, granted_by
            )

        if req.rate_limit is not None:
            api_key = await self.repo.update_rate_limit(key_id, req.rate_limit)

        if api_key is None:
            api_key = await self.repo.get_by_id(key_id)

        if not api_key:
            return None

        return self._key_to_response(api_key)
