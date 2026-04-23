"""Shared pytest fixtures.

Forces an in-memory SQLite URL before the FastAPI app + SQLAlchemy engine are
imported, so tests run hermetically without needing Postgres/Redis/SMTP.
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from pathlib import Path

import pytest
import pytest_asyncio


_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

# Hermetic defaults (override if the developer already has values set).
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-hex-32-chars-1234567890abcdef")
os.environ.setdefault("GROQ_API_KEY", "")
os.environ.setdefault("ARQ_REDIS_URL", "")
os.environ.setdefault("SMTP_HOST", "")
os.environ.setdefault("PERSIST_AUDIO", "false")
os.environ.setdefault("EMBEDDING_BACKEND", "hash")


@pytest.fixture(scope="session")
def event_loop():
    """Per-session event loop so async fixtures share state."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session():
    """Yield a clean in-memory SQLite AsyncSession with schema created."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    import app.models  # noqa: F401  ensure all models are registered
    from app.core.database import Base

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def sample_user(db_session):
    """Insert and return a ready-to-use User."""
    from datetime import datetime, timezone
    from app.models.user import User

    user = User(
        id=uuid.uuid4(),
        email=f"test-{uuid.uuid4().hex[:8]}@meetai.test",
        full_name="Test User",
        hashed_password="not-a-real-hash",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user
