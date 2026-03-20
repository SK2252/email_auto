"""
Enterprise MCP Server — Application Entry Point

Creates the FastAPI application with all middleware, routes, and
startup/shutdown lifecycle hooks.
"""

import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app as prometheus_asgi_app
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.routing import Mount
import asyncio
from app.core.worker import worker_loop, stop_worker
from app.api.routers.v1.mcp import mcp

from app import __version__
from app.api.routers.v1.admin import router as admin_router
from app.api.routers.health import router as health_router
from app.api.routers.v1.gmail import router as gmail_extension_router
from app.api.routers.mlflow import router as mlflow_router
from app.api.middleware.correlation import CorrelationIdMiddleware
from app.api.middleware.error_handler import ErrorHandlerMiddleware
from app.api.middleware.rate_limit import limiter, rate_limit_exceeded_handler
from app.api.middleware.session import SessionMiddleware
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.core.metrics import init_server_info

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """
    Factory function to create and configure the FastAPI application.
    
    Startup order:
      1. Setup structured logging
      2. Create FastAPI app
      3. Register middleware (order matters — outermost runs first)
      4. Mount routes
      5. Register rate limiter
      6. Mount Prometheus metrics endpoint
      7. Register lifecycle hooks (DB + Redis)
    """
    # --- 1. Logging first (before anything else logs) ---
    setup_logging()

    # --- 2. Create app ---
    app = FastAPI(
        title="Enterprise MCP Server",
        description="ISO 42001 Compliant MCP Server wrapping OPN-Agent",
        version=__version__,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    # --- 3. Middleware (outermost first) ---
    # Error handler wraps everything — catches all exceptions
    app.add_middleware(ErrorHandlerMiddleware)

    # Session Middleware (Phase 2.5)
    app.add_middleware(SessionMiddleware)

    # Correlation IDs + request metrics
    app.add_middleware(CorrelationIdMiddleware)

    # CORS (permissive for development, restrictive for prod)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if not settings.is_production else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "X-Correlation-Id",
            "X-Request-Id",
            "Mcp-Session-Id",
        ],
    )

    # --- 4. Routes ---
    app.include_router(health_router)
    app.include_router(admin_router)
    app.include_router(gmail_extension_router)
    app.include_router(mlflow_router)

    # --- 5. Rate limiter ---
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    # --- 6. Prometheus metrics endpoint ---
    metrics_app = prometheus_asgi_app()
    app.mount("/metrics", metrics_app)

    # --- 7. Lifecycle hooks ---
    @app.on_event("startup")
    async def on_startup():
        init_server_info(
            version=__version__,
            environment=settings.environment,
            python_version=sys.version,
        )

        # Verify DB connectivity
        from app.infrastructure.database.engine import check_db_health

        db_ok = await check_db_health()
        logger.info(
            "Database health check",
            status="connected" if db_ok else "unavailable",
        )

        # Connect Redis (graceful — won't crash if unavailable)
        from app.infrastructure.cache.redis_client import get_redis

        redis = await get_redis()
        logger.info(
            "Redis health check",
            status="connected" if redis else "unavailable",
        )

        logger.info(
            "Enterprise MCP Server started",
            version=__version__,
            environment=settings.environment,
            host=settings.mcp_server_host,
            port=settings.mcp_tools_port,
            database="ok" if db_ok else "unavailable",
            redis="ok" if redis else "unavailable",
        )
        
        # Start Orchestrator Worker
        # app.state.worker_task = asyncio.create_task(worker_loop(mcp))

    @app.on_event("shutdown")
    async def on_shutdown():
        from app.infrastructure.database.engine import dispose_engine
        from app.infrastructure.cache.redis_client import dispose_redis

        # Stop Orchestrator Worker
        stop_worker()
        if hasattr(app.state, "worker_task"):
            await app.state.worker_task

        await dispose_engine()
        await dispose_redis()
        logger.info("Enterprise MCP Server shut down")

    # --- Root endpoint ---
    @app.get("/")
    async def root():
        return {
            "service": "Enterprise MCP Server",
            "version": __version__,
            "status": "running",
            "docs": "/docs" if not settings.is_production else None,
        }

    # --- 8. Mount MCP Server (Phase 3A) ---
    from app.api.routers.v1.mcp import mcp
    app.mount("/mcp", mcp.sse_app())

    return app


# Create the app instance (used by uvicorn)
app = create_app()

