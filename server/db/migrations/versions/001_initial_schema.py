"""Initial schema: events, people, event_attendances

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("date_start", sa.Date()),
        sa.Column("date_end", sa.Date()),
        sa.Column("location", sa.String()),
        sa.Column("description", sa.Text()),
        sa.Column("tags", postgresql.ARRAY(sa.String())),
        sa.Column("color", sa.String()),
        sa.Column("created_at", sa.DateTime()),
    )

    op.create_table(
        "people",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("company", sa.String()),
        sa.Column("role", sa.String()),
        sa.Column("location", sa.String()),
        sa.Column("photo_url", sa.String()),
        sa.Column("linkedin_url", sa.String()),
        sa.Column("twitter_handle", sa.String()),
        sa.Column("github_handle", sa.String()),
        sa.Column("instagram_handle", sa.String()),
        sa.Column("personal_site", sa.String()),
        sa.Column("email", sa.String()),
        sa.Column("bio_snapshot", sa.Text()),
        sa.Column("talking_points", postgresql.JSONB()),
        sa.Column("recon_sources", postgresql.JSONB()),
        sa.Column("raw_intel", postgresql.JSONB()),
        sa.Column("agent_ran_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime()),
        sa.UniqueConstraint("name", "company", name="uq_person_name_company"),
    )

    op.create_table(
        "event_attendances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("person_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("people.id"), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("events.id"), nullable=False),
        sa.Column("open_roles", postgresql.JSONB()),
        sa.Column("met", sa.Boolean(), server_default="false"),
        sa.Column("met_at", sa.DateTime()),
        sa.Column("met_notes", sa.Text()),
        sa.Column("outreach_sent", sa.Boolean(), server_default="false"),
        sa.Column("outreach_channel", sa.String()),
        sa.Column("outreach_draft", sa.Text()),
        sa.Column("outreach_sent_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime()),
        sa.UniqueConstraint("person_id", "event_id", name="uq_person_event"),
    )


def downgrade() -> None:
    op.drop_table("event_attendances")
    op.drop_table("people")
    op.drop_table("events")
