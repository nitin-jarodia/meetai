"""Environment-driven configuration."""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve `backend/.env` even when the process cwd is not `backend/` (e.g. IDE runners).
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _BACKEND_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "MeetAI"
    debug: bool = False

    # Use PostgreSQL in production / with `docker compose`; SQLite works without Docker.
    database_url: str = "sqlite+aiosqlite:///./meetai.db"

    jwt_secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # Audio upload + local Whisper (model: tiny, base, small, …)
    uploads_dir: str = "uploads"
    whisper_model: str = "base"
    # Optional: path to ffmpeg.exe or its directory. Empty = use bundled ffmpeg (imageio-ffmpeg).
    ffmpeg_path: str = ""
    # Keep the original audio so meetings can be replayed with click-to-seek transcripts.
    persist_audio: bool = True

    # Search tuning: SQLite works with the local fallback; PostgreSQL is the
    # recommended production path and can be paired with pgvector later.
    search_chunk_chars: int = 600
    # 384 matches sentence-transformers/all-MiniLM-L6-v2; hash fallback honors the same size.
    search_embedding_dimensions: int = 384
    search_prefer_pgvector: bool = True
    embedding_backend: str = "auto"  # "auto" | "sentence-transformers" | "hash"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Diarization
    diarization_backend: str = "none"  # "none" | "pyannote"
    huggingface_token: str = ""

    # Reminders
    reminder_poll_interval_seconds: int = 60
    reminder_lead_time_minutes: int = 60

    # Rolling live summary
    live_summary_interval_seconds: int = 45
    live_summary_min_new_chars: int = 400

    # Arq worker
    arq_redis_url: str = ""

    # Email / notifications
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = "meetai@example.com"
    smtp_use_tls: bool = True

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def uploads_path(self) -> Path:
        return _BACKEND_ROOT / self.uploads_dir

    @property
    def audio_path(self) -> Path:
        return self.uploads_path / "audio"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def backend_root(self) -> Path:
        return _BACKEND_ROOT


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
