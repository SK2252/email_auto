"""
MCP Server lifespan context manager.

FastMCP lifespan receives the FastMCP instance (not a Starlette/FastAPI app),
so server.state does NOT exist. Instead, yield a dict — FastMCP stores it and
exposes it to tools via:

    ctx.request_context.lifespan_context["gmail"]
    ctx.request_context.lifespan_context["engine"]
    ctx.request_context.lifespan_context["redis"]

Root cause fix (2026-03-25):
    server.state.gmail = gmail  ← WRONG: FastMCP has no .state attribute
                                   This raised AttributeError silently,
                                   crashing run_server → finally block deleted
                                   the session → 404 "Session not found" on
                                   every subsequent request.

    Fix: yield {"gmail": gmail, "engine": engine, "redis": redis_client}
         FastMCP stores the yielded dict as lifespan_context automatically.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.database.engine import build_engine
from shared.infrastructure.gmail_client import GmailClient

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(server) -> AsyncIterator[dict]:
    """
    FastMCP lifespan context manager.

    Startup: creates GmailClient, SQLAlchemy async engine, Redis client.
    Shutdown: disposes engine and closes Redis connection cleanly.

    Yields a dict — FastMCP exposes it to tools via:
        ctx.request_context.lifespan_context["gmail"]
        ctx.request_context.lifespan_context["engine"]
        ctx.request_context.lifespan_context["redis"]
    """
    logger.info("MCP Server lifespan startup — initialising clients")

    # --- Gmail client (async wrapper around existing OAuth logic) ---
    gmail = GmailClient()
    logger.info("GmailClient initialised")

    # --- SQLAlchemy async engine ---
    engine = build_engine()
    logger.info("Database engine initialised", url=settings.database_url[:30])

    # --- Redis async client ---
    redis_url = (
        f"redis://"
        f"{(':' + settings.redis_password + '@') if settings.redis_password else ''}"
        f"{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
    )
    redis_client = aioredis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=5,
    )
    logger.info(
        "Redis client initialised",
        host=settings.redis_host,
        port=settings.redis_port,
    )

    logger.info("MCP Server lifespan startup complete — all clients ready")

    try:
        # ----------------------------------------------------------------
        # FIX: yield the clients as a dict.
        # FastMCP stores this dict as lifespan_context and passes it to
        # every tool via ctx.request_context.lifespan_context.
        #
        # DO NOT use server.state.gmail = gmail — FastMCP has no .state.
        # ----------------------------------------------------------------
        yield {
            "gmail": gmail,
            "engine": engine,
            "redis": redis_client,
        }
    finally:
        logger.info("MCP Server lifespan shutdown — disposing clients")
        await engine.dispose()
        await redis_client.aclose()
        logger.info("MCP Server lifespan shutdown complete")