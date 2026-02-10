"""Async SQLAlchemy engine and session management."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import Settings, get_settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models."""

    pass


_engine: Optional[AsyncEngine] = None
_async_session: Optional[async_sessionmaker[AsyncSession]] = None


def _get_engine(settings: Optional[Settings] = None) -> AsyncEngine:
    """Get or create the async engine (lazy singleton)."""
    global _engine
    if _engine is None:
        s = settings or get_settings()
        _engine = create_async_engine(
            s.database_url,
            echo=s.debug,
            pool_pre_ping=True,
        )
    return _engine


def _get_session_factory(
    settings: Optional[Settings] = None,
) -> async_sessionmaker[AsyncSession]:
    """Get or create the session factory (lazy singleton)."""
    global _async_session
    if _async_session is None:
        _async_session = async_sessionmaker(
            _get_engine(settings),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for FastAPI Depends() injection."""
    factory = _get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db(settings: Optional[Settings] = None) -> None:
    """Create all tables. For development only — production uses Alembic."""
    engine = _get_engine(settings)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine() -> None:
    """Dispose the engine on shutdown."""
    global _engine, _async_session
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _async_session = None
