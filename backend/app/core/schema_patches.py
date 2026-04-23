"""Lightweight additive migrations for dev DBs without running Alembic.

These are intentionally idempotent ALTER TABLEs so an existing database (SQLite
during `run-api.ps1` dev, or a shared Postgres) picks up new columns without a
formal migration step. Production should run `alembic upgrade head`.
"""

from sqlalchemy import text
from sqlalchemy.engine import Connection


def _sqlite_columns(connection: Connection, table: str) -> set[str]:
    rows = connection.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows}


def _sqlite_tables(connection: Connection) -> set[str]:
    rows = connection.execute(
        text("SELECT name FROM sqlite_master WHERE type='table'")
    ).fetchall()
    return {row[0] for row in rows}


def _postgres_columns(connection: Connection, table: str) -> set[str]:
    rows = connection.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = :t
            """
        ),
        {"t": table},
    ).fetchall()
    return {row[0] for row in rows}


def _add_column_if_missing(
    connection: Connection, table: str, column: str, sql_type: str, *, default: str | None = None
) -> None:
    dialect = connection.dialect.name
    if dialect == "sqlite":
        cols = _sqlite_columns(connection, table)
        if column in cols:
            return
        stmt = f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"
        if default is not None:
            stmt += f" DEFAULT {default}"
        connection.execute(text(stmt))
    elif dialect in ("postgresql", "postgres"):
        cols = _postgres_columns(connection, table)
        if column in cols:
            return
        stmt = f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {sql_type}"
        if default is not None:
            stmt += f" DEFAULT {default}"
        connection.execute(text(stmt))


def apply_transcript_storage_columns(connection: Connection) -> None:
    """Add structured transcript / segment / action-item columns when missing."""
    dialect = connection.dialect.name
    if dialect not in ("sqlite", "postgresql", "postgres"):
        return

    if dialect in ("postgresql", "postgres"):
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    json_type = "JSON" if dialect == "sqlite" else "JSONB"
    json_default = "'[]'" if dialect == "sqlite" else "'[]'::jsonb"
    text_type = "TEXT"
    ts_type = "TIMESTAMPTZ" if dialect != "sqlite" else "DATETIME"

    # --- transcripts ---
    _add_column_if_missing(connection, "transcripts", "summary", text_type)
    _add_column_if_missing(connection, "transcripts", "transcript_text", text_type)
    _add_column_if_missing(connection, "transcripts", "cleaned_transcript", text_type)
    _add_column_if_missing(connection, "transcripts", "translated_text", text_type)
    _add_column_if_missing(
        connection, "transcripts", "translated_language", "VARCHAR(16)"
    )
    _add_column_if_missing(
        connection, "transcripts", "key_points", json_type, default=json_default
    )
    _add_column_if_missing(
        connection, "transcripts", "action_items", json_type, default=json_default
    )
    _add_column_if_missing(connection, "transcripts", "language", "VARCHAR(16)")
    _add_column_if_missing(connection, "transcripts", "duration_ms", "INTEGER")
    _add_column_if_missing(connection, "transcripts", "audio_path", "VARCHAR(1024)")
    _add_column_if_missing(connection, "transcripts", "audio_mime_type", "VARCHAR(128)")

    # --- meeting_action_items ---
    _add_column_if_missing(connection, "meeting_action_items", "due_at", ts_type)
    _add_column_if_missing(
        connection, "meeting_action_items", "last_reminded_at", ts_type
    )

    # --- meeting_search_chunks ---
    _add_column_if_missing(
        connection, "meeting_search_chunks", "embedding_version", "VARCHAR(64)"
    )

    # Backfill legacy content column
    if dialect == "sqlite":
        cols = _sqlite_columns(connection, "transcripts")
    else:
        cols = _postgres_columns(connection, "transcripts")
    if "content" in cols and "transcript_text" in cols:
        connection.execute(
            text(
                """
                UPDATE transcripts
                SET transcript_text = content
                WHERE (transcript_text IS NULL OR transcript_text = '')
                  AND content IS NOT NULL
                """
            )
        )
    if "cleaned_transcript" in cols and "transcript_text" in cols:
        connection.execute(
            text(
                """
                UPDATE transcripts
                SET cleaned_transcript = transcript_text
                WHERE (cleaned_transcript IS NULL OR cleaned_transcript = '')
                  AND transcript_text IS NOT NULL
                """
            )
        )
    if "key_points" in cols:
        connection.execute(
            text("UPDATE transcripts SET key_points = '[]' WHERE key_points IS NULL")
        )
    if "action_items" in cols:
        connection.execute(
            text(
                "UPDATE transcripts SET action_items = '[]' WHERE action_items IS NULL"
            )
        )
