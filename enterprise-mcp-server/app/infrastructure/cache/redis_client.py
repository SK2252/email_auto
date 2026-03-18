"""
Async Redis client with connection pooling.
Singleton pattern — import `redis_client` from this module.
Graceful degradation if Redis is unavailable.
"""

from typing import Optional

import redis.asyncio as aioredis
import json

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_pool: Optional[aioredis.ConnectionPool] = None
_client: Optional[aioredis.Redis] = None


def _build_url() -> str:
    """Construct Redis URL from settings."""
    auth = f":{settings.redis_password}@" if settings.redis_password else ""
    return f"redis://{auth}{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"


async def get_redis() -> Optional[aioredis.Redis]:
    """
    Get the Redis client singleton. Creates pool on first call.
    Returns None if Redis connection fails (graceful degradation).
    """
    global _pool, _client

    if _client is not None:
        return _client

    try:
        _pool = aioredis.ConnectionPool.from_url(
            _build_url(),
            max_connections=20,
            decode_responses=True,
        )
        _client = aioredis.Redis(connection_pool=_pool)
        # Verify connection
        await _client.ping()
        logger.info("Redis connected", host=settings.redis_host, port=settings.redis_port)
        return _client
    except Exception as e:
        logger.warning(
            "Redis unavailable — rate limiting will use in-memory fallback",
            error=str(e),
        )
        _client = None
        return None


async def check_redis_health() -> bool:
    """Readiness probe: verify Redis is reachable."""
    try:
        client = await get_redis()
        if client is None:
            return False
        pong = await client.ping()
        return pong is True
    except Exception:
        return False


async def dispose_redis() -> None:
    """Shutdown hook: close Redis pool."""
    global _pool, _client
    if _client:
        await _client.close()
        _client = None
    if _pool:
        await _pool.disconnect()
        _pool = None
    logger.info("Redis connection pool disposed")

async def publish_email_update(event_type: str = "emails_organized", data: dict = None):
    """Publish an event to the email_events Redis channel."""
    try:
        client = await get_redis()
        if client:
            message = {"event": event_type}
            if data:
                message.update(data)
            await client.publish("email_events", json.dumps(message))
            logger.info(f"Published event '{event_type}' to email_events channel")
    except Exception as e:
        logger.error(f"Failed to publish email update: {e}")
