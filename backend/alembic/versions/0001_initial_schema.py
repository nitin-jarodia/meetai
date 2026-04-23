"""Initial MeetAI schema baseline.

Captures every current table: users, meetings, participants, transcripts,
transcript_segments, meeting_action_items, meeting_qa_entries,
meeting_processing_jobs, meeting_search_chunks, and notification_preferences.

Run once on a fresh database:
    cd backend && alembic upgrade head

Existing dev DBs created by SQLAlchemy's `create_all` + schema_patches should
stamp the current revision instead of running upgrade:
    cd backend && alembic stamp head

Revision ID: 0001
Revises:
Create Date: 2026-04-23
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _json_type(bind) -> sa.types.TypeEngine:
    if bind.dialect.name in ("postgresql", "postgres"):
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def upgrade() -> None:
    bind = op.get_bind()
    json_type = _json_type(bind)

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "meetings",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "host_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "participants",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "meeting_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("meetings.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("role", sa.String(50), nullable=False, server_default="member"),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("meeting_id", "user_id", name="uq_meeting_user"),
    )

    op.create_table(
        "transcripts",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "meeting_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("meetings.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("transcript_text", sa.Text(), nullable=False),
        sa.Column("cleaned_transcript", sa.Text(), nullable=True),
        sa.Column("translated_text", sa.Text(), nullable=True),
        sa.Column("translated_language", sa.String(16), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("key_points", json_type, nullable=False, server_default="[]"),
        sa.Column("action_items", json_type, nullable=False, server_default="[]"),
        sa.Column("language", sa.String(16), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("audio_path", sa.String(1024), nullable=True),
        sa.Column("audio_mime_type", sa.String(128), nullable=True),
        sa.Column("segment_index", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "transcript_segments",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "transcript_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("transcripts.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("start_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("end_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "speaker_label",
            sa.String(64),
            nullable=False,
            server_default="Speaker 1",
        ),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "meeting_action_items",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "meeting_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("meetings.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "transcript_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("transcripts.id"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "created_by_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "assigned_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
            index=True,
        ),
        sa.Column("task", sa.Text(), nullable=False),
        sa.Column("assigned_to_name", sa.String(255), nullable=True),
        sa.Column("deadline", sa.String(255), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("last_reminded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="open"),
        sa.Column("source", sa.String(50), nullable=False, server_default="ai"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "meeting_qa_entries",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "meeting_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("meetings.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "transcript_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("transcripts.id"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "meeting_processing_jobs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "meeting_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("meetings.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "created_by_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("filename", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="queued"),
        sa.Column("stage", sa.String(100), nullable=False, server_default="queued"),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "meeting_search_chunks",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "meeting_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("meetings.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "transcript_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("transcripts.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", json_type, nullable=False, server_default="[]"),
        sa.Column("embedding_version", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column(
            "email_enabled", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column(
            "reminders_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "meeting_ready_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("notification_preferences")
    op.drop_table("meeting_search_chunks")
    op.drop_table("meeting_processing_jobs")
    op.drop_table("meeting_qa_entries")
    op.drop_table("meeting_action_items")
    op.drop_table("transcript_segments")
    op.drop_table("transcripts")
    op.drop_table("participants")
    op.drop_table("meetings")
    op.drop_table("users")
