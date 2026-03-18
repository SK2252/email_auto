"""
Health check logic for liveness and readiness probes.
Used by Kubernetes and monitoring systems.
"""

from typing import Any, Dict

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def check_liveness() -> Dict[str, Any]:
    """
    Liveness probe — is the process alive?
    Always returns healthy if the server is responding.
    """
    return {
        "status": "alive",
        "environment": settings.environment,
    }


async def check_readiness() -> Dict[str, Any]:
    """
    Readiness probe — can the server handle requests?
    Checks connectivity to PostgreSQL and Redis.
    """
    checks: Dict[str, Any] = {}
    overall_ready = True

    # Check PostgreSQL
    try:
        from sqlalchemy import text as sa_text
        from app.infrastructure.database.engine import engine

        async with engine.connect() as conn:
            await conn.execute(sa_text("SELECT 1"))
        checks["postgresql"] = "connected"
    except Exception as e:
        checks["postgresql"] = f"unavailable: {str(e)}"
        overall_ready = False
        logger.warning("PostgreSQL health check failed", error=str(e))

    # Check Redis
    try:
        from app.infrastructure.cache.redis_client import check_redis_health

        redis_ok = await check_redis_health()
        checks["redis"] = "connected" if redis_ok else "unavailable"
        if not redis_ok:
            overall_ready = False
    except Exception as e:
        checks["redis"] = f"unavailable: {str(e)}"
        overall_ready = False
        logger.warning("Redis health check failed", error=str(e))

    return {
        "status": "ready" if overall_ready else "not_ready",
        "checks": checks,
        "environment": settings.environment,
    }
