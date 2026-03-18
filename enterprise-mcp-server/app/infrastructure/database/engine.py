"""
Async SQLAlchemy engine with connection pooling.
Uses asyncpg driver for PostgreSQL.
"""

from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def build_engine() -> AsyncEngine:
    """Create the async engine with connection pool settings from config."""
    return create_async_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_recycle=settings.database_pool_recycle,
        pool_pre_ping=True,
        echo=settings.debug,
    )


engine: AsyncEngine = build_engine()

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields a transactional session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_db_health() -> bool:
    """Readiness probe: verify PostgreSQL is reachable."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning("PostgreSQL health check failed", error=str(e))
        return False


async def dispose_engine() -> None:
    """Shutdown hook: close all pooled connections."""
    await engine.dispose()
    logger.info("Database engine disposed")
