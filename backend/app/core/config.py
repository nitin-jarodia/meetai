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

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def uploads_path(self) -> Path:
        return _BACKEND_ROOT / self.uploads_dir

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
