"""
Session Dependency for FastAPI Routes.
Ensures a session exists for the current request context.
Auto-creates a session if one does not exist (lazy initialization).
"""

from typing import Dict

from fastapi import Depends, Request

from app.infrastructure.cache.session_manager import session_manager
from app.models.schemas import Identity
from app.core.logging import get_logger
from app.domains.auth.api_key import validate_api_key

logger = get_logger(__name__)


async def get_current_session(
    request: Request,
    identity: Identity = Depends(validate_api_key),
) -> Dict:
    """
    FastAPI Dependency:
    Returns the current session for the authenticated user.
    
    If the session was already loaded by middleware (via X-Session-Id), returns it.
    If no session exists, creates a new one for the identity.owner.
    
    This ensures that:
    1. Authenticated routes always have a session.
    2. New sessions are created lazily only when needed.
    """
    
    # Check if middleware already loaded a session
    if hasattr(request.state, "session") and request.state.session:
        # Validate ownership (security check)
        # Prevents hijacking another user's valid session ID
        if request.state.session.get("user_id") != identity.owner:
            logger.warning(
                "Session owner mismatch",
                session_user=request.state.session.get("user_id"),
                auth_user=identity.owner
            )
            # Should we raise 403? Or just force new session?
            # Safer to fail fast or overwrite. Let's create a new one for the correct user.
            logger.info("Creating new session due to owner mismatch")
            pass
        else:
            return request.state.session

    # No valid session exists -> Create new one
    # Note: agent_capabilities will be loaded from registry in Phase 3B
    # For now, we initialize with empty dict or placeholder
    
    session = await session_manager.create_session(
        user_id=identity.owner,
        agent_capabilities={}  # Will be populated Phase 3B
    )
    
    # Attach to request state so middleware can add the header to response
    request.state.session = session
    
    logger.info("Session auto-created", user_id=identity.owner)
    return session
