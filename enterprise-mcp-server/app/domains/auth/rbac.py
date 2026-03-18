"""
Tool-level RBAC enforcer.
Reads ToolPermission mappings from PostgreSQL, caches in-memory with TTL.
Resolves: identity.scopes → allowed tool names → enforce or deny.
"""

import asyncio
import time
from typing import Dict, List, Optional, Set

from fastapi import HTTPException, status

from app.infrastructure.database.engine import async_session_factory
from app.infrastructure.database.repositories.base import ApiKeyRepository
from app.core.logging import get_logger

logger = get_logger(__name__)

# ─── Cache TTL ────────────────────────────────────────────────────────────────

CACHE_TTL_SECONDS = 300  # 5 minutes


class RBACEnforcer:
    """
    Enforces tool-level access control based on API key scopes.

    Architecture:
      api_key_permissions (per key) → scope → tool_permissions (global mapping) → tool_name

    Cache:
      scope→tools mapping is loaded from PG and cached for 5 min.
      Avoids per-request DB calls.
    """

    def __init__(self):
        self._cache: Dict[str, List[str]] = {}
        self._cache_ts: float = 0.0
        self._lock = asyncio.Lock()

    async def _refresh_cache(self) -> None:
        """Load scope→tool mappings from DB into memory cache."""
        async with async_session_factory() as session:
            repo = ApiKeyRepository(session)
            self._cache = await repo.get_tool_permissions()
            self._cache_ts = time.time()
            logger.info(
                "RBAC cache refreshed",
                scopes=list(self._cache.keys()),
                total_mappings=sum(len(v) for v in self._cache.values()),
            )

    async def _ensure_cache(self) -> None:
        """Refresh cache if expired or empty."""
        if (
            not self._cache
            or (time.time() - self._cache_ts) > CACHE_TTL_SECONDS
        ):
            async with self._lock:
                # Double-check after acquiring lock
                if (
                    not self._cache
                    or (time.time() - self._cache_ts) > CACHE_TTL_SECONDS
                ):
                    await self._refresh_cache()

    def _get_allowed_tools(self, scopes: List[str]) -> Set[str]:
        """Resolve scopes to the set of allowed tool names."""
        allowed: Set[str] = set()
        for scope in scopes:
            tools = self._cache.get(scope, [])
            allowed.update(tools)

            # "admin" scope grants access to everything
            if scope == "admin":
                for tool_list in self._cache.values():
                    allowed.update(tool_list)
                break

        return allowed

    async def enforce(self, scopes: List[str], tool_name: str) -> None:
        """
        Check if the given scopes allow access to the specified tool.
        Raises HTTP 403 if denied.
        """
        await self._ensure_cache()

        allowed_tools = self._get_allowed_tools(scopes)

        if tool_name not in allowed_tools:
            logger.warning(
                "RBAC denied",
                scopes=scopes,
                tool_name=tool_name,
                allowed_tools=list(allowed_tools),
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "E_AUTHZ_201",
                    "message": f"Insufficient permissions for tool '{tool_name}'. "
                    f"Required scope not found in: {', '.join(scopes)}",
                },
            )

        logger.debug(
            "RBAC granted",
            scopes=scopes,
            tool_name=tool_name,
        )

    async def check(self, scopes: List[str], tool_name: str) -> bool:
        """
        Non-throwing check — returns True if allowed, False otherwise.
        Useful for UI/filtering (e.g. show only tools user can access).
        """
        await self._ensure_cache()
        return tool_name in self._get_allowed_tools(scopes)

    async def invalidate_cache(self) -> None:
        """Force cache refresh on next request (e.g. after admin updates)."""
        self._cache.clear()
        self._cache_ts = 0.0
        logger.info("RBAC cache invalidated")


# Singleton
rbac_enforcer = RBACEnforcer()
