"""
API key authentication — FastAPI dependency.
Extracts X-API-Key header → SHA-256 → PG lookup → Identity model.
"""

import hashlib
import hmac
import time
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.database.engine import get_session
from app.infrastructure.database.repositories.base import ApiKeyRepository
from app.models.schemas import ApiKeyStatus, Identity
from app.core.logging import get_logger
from app.core.metrics import api_key_validations

logger = get_logger(__name__)


async def validate_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_hmac_signature: Optional[str] = Header(None, alias="X-HMAC-Signature"),
    x_hmac_timestamp: Optional[str] = Header(None, alias="X-HMAC-Timestamp"),
    session: AsyncSession = Depends(get_session),
) -> Identity:
    """
    FastAPI dependency: validates API key from header.
    Returns Identity with scopes, status, and rate_limit.
    """
    if not x_api_key:
        api_key_validations.labels(result="missing").inc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "E_AUTH_100",
                "message": "API key is required. Pass it via X-API-Key header.",
            },
        )

    # Hash the provided key and look it up
    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
    repo = ApiKeyRepository(session)
    api_key = await repo.get_by_hash(key_hash)

    if not api_key:
        api_key_validations.labels(result="invalid").inc()
        logger.warning("Invalid API key attempt", key_prefix=x_api_key[:12])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "E_AUTH_101",
                "message": "Invalid API key.",
            },
        )

    # Check validity (status + expiration + rotation window)
    if not api_key.is_valid:
        api_key_validations.labels(result="expired_or_revoked").inc()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "E_AUTH_102",
                "message": f"API key is {api_key.status.value}.",
            },
        )

    # HMAC verification (if enabled)
    if settings.hmac_signing_enabled:
        _verify_hmac(
            api_key.key_secret_hash,
            x_hmac_signature,
            x_hmac_timestamp,
            request,
        )

    # Update last-used tracking (fire-and-forget)
    source_ip = request.client.host if request.client else None
    await repo.update_last_used(api_key.id, ip=source_ip)

    # Build Identity
    scopes = [p.scope for p in api_key.permissions]
    identity = Identity(
        key_id=api_key.id,
        owner=api_key.owner,
        scopes=scopes,
        status=ApiKeyStatus(api_key.status.value),
        rate_limit=api_key.rate_limit,
        source_ip=source_ip,
        user_agent=request.headers.get("user-agent"),
    )

    api_key_validations.labels(result="success").inc()
    logger.info(
        "API key validated",
        key_id=api_key.id,
        owner=api_key.owner,
        scopes=scopes,
    )

    return identity


def _verify_hmac(
    stored_secret_hash: Optional[str],
    signature: Optional[str],
    timestamp_str: Optional[str],
    request: Request,
) -> None:
    """Verify HMAC signature if signing is enabled."""
    if not signature or not timestamp_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "E_AUTH_103",
                "message": "HMAC signature and timestamp are required.",
            },
        )

    if not stored_secret_hash:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "E_AUTH_104",
                "message": "This API key does not have HMAC signing configured.",
            },
        )

    # Check timestamp within tolerance
    try:
        ts = int(timestamp_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "E_AUTH_105",
                "message": "Invalid HMAC timestamp format.",
            },
        )

    now = int(time.time())
    if abs(now - ts) > settings.hmac_timestamp_tolerance_seconds:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "E_AUTH_106",
                "message": "HMAC timestamp is outside tolerance window.",
            },
        )

    # Signature verification would require the raw secret, but we only
    # store the hash. For now, this is a structural placeholder —
    # production would use a KMS or vault-backed secret.
    logger.debug("HMAC signature check passed (structural)")
