"""
Admin API router — API key lifecycle management.
All endpoints require admin scope (enforced by RBAC).
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.engine import get_session
from app.infrastructure.database.repositories.base import ApiKeyRepository
from app.models.schemas import Identity
from app.domains.auth.admin import (
    AdminService,
    CreateKeyRequest,
    CreateKeyResponse,
    KeyResponse,
    RevokeKeyRequest,
    RotateKeyRequest,
    UpdateKeyRequest,
)
from app.domains.auth.api_key import validate_api_key

router = APIRouter(prefix="/admin", tags=["admin"])


def _get_admin_service(session: AsyncSession = Depends(get_session)) -> AdminService:
    return AdminService(ApiKeyRepository(session))


def _require_admin(identity: Identity = Depends(validate_api_key)) -> Identity:
    """Enforce admin scope for all admin endpoints."""
    if "admin" not in identity.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "E_AUTHZ_200",
                "message": "Admin scope is required for this endpoint.",
            },
        )
    return identity


# ─── Create ──────────────────────────────────────────────────────────────────


@router.post(
    "/keys",
    response_model=CreateKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key",
)
async def create_key(
    req: CreateKeyRequest,
    identity: Identity = Depends(_require_admin),
    admin_svc: AdminService = Depends(_get_admin_service),
) -> CreateKeyResponse:
    """
    Generate a new API key with specified scopes and rate limit.
    The raw key is returned only once — store it securely.
    """
    return await admin_svc.create_key(req, granted_by=identity.owner)


# ─── List ────────────────────────────────────────────────────────────────────


@router.get(
    "/keys",
    response_model=List[KeyResponse],
    summary="List API keys",
)
async def list_keys(
    owner: Optional[str] = Query(None),
    key_status: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    identity: Identity = Depends(_require_admin),
    admin_svc: AdminService = Depends(_get_admin_service),
) -> List[KeyResponse]:
    """List API keys with optional filtering by owner and status."""
    return await admin_svc.list_keys(
        owner=owner, status=key_status, limit=limit, offset=offset
    )


# ─── Get ─────────────────────────────────────────────────────────────────────


@router.get(
    "/keys/{key_id}",
    response_model=KeyResponse,
    summary="Get API key details",
)
async def get_key(
    key_id: str,
    identity: Identity = Depends(_require_admin),
    admin_svc: AdminService = Depends(_get_admin_service),
) -> KeyResponse:
    """Get detailed information about a specific API key."""
    result = await admin_svc.get_key(key_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "E_KEY_400",
                "message": f"API key '{key_id}' not found.",
            },
        )
    return result


# ─── Update ──────────────────────────────────────────────────────────────────


@router.patch(
    "/keys/{key_id}",
    response_model=KeyResponse,
    summary="Update API key permissions or rate limit",
)
async def update_key(
    key_id: str,
    req: UpdateKeyRequest,
    identity: Identity = Depends(_require_admin),
    admin_svc: AdminService = Depends(_get_admin_service),
) -> KeyResponse:
    """Update scopes and/or rate limit for an existing API key."""
    result = await admin_svc.update_key(key_id, req, granted_by=identity.owner)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "E_KEY_400",
                "message": f"API key '{key_id}' not found.",
            },
        )
    return result


# ─── Revoke ──────────────────────────────────────────────────────────────────


@router.post(
    "/keys/{key_id}/revoke",
    response_model=KeyResponse,
    summary="Revoke an API key",
)
async def revoke_key(
    key_id: str,
    req: RevokeKeyRequest = RevokeKeyRequest(),
    identity: Identity = Depends(_require_admin),
    admin_svc: AdminService = Depends(_get_admin_service),
) -> KeyResponse:
    """Revoke an API key immediately. Cannot be undone."""
    result = await admin_svc.revoke_key(key_id, req.reason)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "E_KEY_400",
                "message": f"API key '{key_id}' not found.",
            },
        )
    return result


# ─── Rotate ──────────────────────────────────────────────────────────────────


@router.post(
    "/keys/{key_id}/rotate",
    response_model=CreateKeyResponse,
    summary="Rotate an API key",
)
async def rotate_key(
    key_id: str,
    req: RotateKeyRequest = RotateKeyRequest(),
    identity: Identity = Depends(_require_admin),
    admin_svc: AdminService = Depends(_get_admin_service),
) -> CreateKeyResponse:
    """
    Create a replacement key and set the old key to 'rotating' status.
    Both keys are valid during the grace window.
    """
    result = await admin_svc.rotate_key(
        key_id, req.grace_hours, granted_by=identity.owner
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "E_KEY_401",
                "message": f"API key '{key_id}' not found or not active.",
            },
        )
    return result
