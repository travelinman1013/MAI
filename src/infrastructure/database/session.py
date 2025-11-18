"""Database session management with async SQLAlchemy.

This module provides:
- Async database engine
- Session factory with context management
- FastAPI dependency for database sessions
- Connection lifecycle management
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from src.core.utils.config import get_settings
from src.core.utils.logging import get_logger_with_context

logger = get_logger_with_context()

# Global engine and session factory
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def create_engine(
    database_url: Optional[str] = None,
    echo: bool = False,
    pool_size: int = 20,
    max_overflow: int = 10,
    pool_timeout: int = 30,
    use_null_pool: bool = False,
) -> AsyncEngine:
    """Create async database engine.

    Args:
        database_url: Database connection URL. If None, uses settings.
        echo: Echo SQL statements for debugging.
        pool_size: Connection pool size.
        max_overflow: Maximum overflow connections.
        pool_timeout: Connection pool timeout in seconds.
        use_null_pool: Use NullPool (for testing).

    Returns:
        Async database engine.
    """
    if database_url is None:
        settings = get_settings()
        database_url = settings.database.url

    # Engine configuration
    engine_kwargs = {
        "url": database_url,
        "echo": echo,
        "future": True,
    }

    # Use NullPool for testing, otherwise use default pool
    if use_null_pool:
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs["pool_size"] = pool_size
        engine_kwargs["max_overflow"] = max_overflow
        engine_kwargs["pool_timeout"] = pool_timeout
        engine_kwargs["pool_pre_ping"] = True  # Verify connections before using

    engine = create_async_engine(**engine_kwargs)
    logger.info("Database engine created", database_url=database_url.split("@")[-1])
    return engine


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create session factory for the given engine.

    Args:
        engine: Async database engine.

    Returns:
        Session factory.
    """
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


def init_db(
    database_url: Optional[str] = None,
    echo: bool = False,
    pool_size: int = 20,
    max_overflow: int = 10,
    pool_timeout: int = 30,
) -> None:
    """Initialize database engine and session factory.

    Args:
        database_url: Database connection URL. If None, uses settings.
        echo: Echo SQL statements for debugging.
        pool_size: Connection pool size.
        max_overflow: Maximum overflow connections.
        pool_timeout: Connection pool timeout in seconds.
    """
    global _engine, _session_factory

    if _engine is not None:
        logger.warning("Database already initialized, skipping")
        return

    # Get settings
    settings = get_settings()
    if database_url is None:
        database_url = settings.database.url
    if not echo:
        echo = settings.database.echo

    # Create engine and session factory
    _engine = create_engine(
        database_url=database_url,
        echo=echo,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
    )
    _session_factory = create_session_factory(_engine)
    logger.info("Database initialized successfully")


async def close_db() -> None:
    """Close database engine and cleanup resources."""
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database connection closed")


def get_engine() -> AsyncEngine:
    """Get the global database engine.

    Returns:
        Async database engine.

    Raises:
        RuntimeError: If database is not initialized.
    """
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get the global session factory.

    Returns:
        Session factory.

    Raises:
        RuntimeError: If database is not initialized.
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session as context manager.

    Yields:
        Database session.

    Example:
        async with get_session() as session:
            result = await session.execute(select(User))
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions.

    Yields:
        Database session.

    Example:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
