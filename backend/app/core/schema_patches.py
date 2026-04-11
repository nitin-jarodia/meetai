"""Lightweight additive migrations for dev DBs without Alembic."""

from sqlalchemy import text
from sqlalchemy.engine import Connection


def _get_transcript_columns(connection: Connection) -> set[str]:
    dialect = connection.dialect.name
    if dialect == "sqlite":
        rows = connection.execute(text("PRAGMA table_info(transcripts)")).fetchall()
        return {row[1] for row in rows}
    if dialect in ("postgresql", "postgres"):
        rows = connection.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'transcripts'
                """
            )
        ).fetchall()
        return {row[0] for row in rows}
    return set()


def apply_transcript_storage_columns(connection: Connection) -> None:
    """Add structured transcript columns when missing and backfill old data."""
    dialect = connection.dialect.name
    cols = _get_transcript_columns(connection)

    if dialect == "sqlite":
        if "summary" not in cols:
            connection.execute(text("ALTER TABLE transcripts ADD COLUMN summary TEXT"))
        if "transcript_text" not in cols:
            connection.execute(
                text("ALTER TABLE transcripts ADD COLUMN transcript_text TEXT")
            )
        if "key_points" not in cols:
            connection.execute(
                text(
                    "ALTER TABLE transcripts "
                    "ADD COLUMN key_points JSON DEFAULT '[]' NOT NULL"
                )
            )
        if "action_items" not in cols:
            connection.execute(
                text(
                    "ALTER TABLE transcripts "
                    "ADD COLUMN action_items JSON DEFAULT '[]' NOT NULL"
                )
            )
    elif dialect in ("postgresql", "postgres"):
        connection.execute(
            text("ALTER TABLE transcripts ADD COLUMN IF NOT EXISTS summary TEXT")
        )
        connection.execute(
            text("ALTER TABLE transcripts ADD COLUMN IF NOT EXISTS transcript_text TEXT")
        )
        connection.execute(
            text(
                "ALTER TABLE transcripts "
                "ADD COLUMN IF NOT EXISTS key_points JSONB DEFAULT '[]'::jsonb NOT NULL"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE transcripts "
                "ADD COLUMN IF NOT EXISTS action_items JSONB DEFAULT '[]'::jsonb NOT NULL"
            )
        )
    else:
        return

    cols = _get_transcript_columns(connection)
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
