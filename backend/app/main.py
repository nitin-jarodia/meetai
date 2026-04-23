"""Application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401 — register SQLAlchemy metadata
from app.api.v1 import action_items, ai, auth, meetings, transcripts, websocket as ws_routes
from app.core.config import settings
from app.core.database import Base, engine
from app.core.schema_patches import apply_transcript_storage_columns
from app.services.processing_service import get_processing_runtime
from app.services.reminder_scheduler import get_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(apply_transcript_storage_columns)

    scheduler = get_scheduler()
    await scheduler.start()

    try:
        yield
    finally:
        await scheduler.stop()
        await get_processing_runtime().close()
        await engine.dispose()


app = FastAPI(
    title="MeetAI API",
    description="AI Meeting Assistant — foundation API",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(meetings.router, prefix="/api/v1")
app.include_router(transcripts.router, prefix="/api/v1")
app.include_router(action_items.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")
app.include_router(ws_routes.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "meetai-backend"}
