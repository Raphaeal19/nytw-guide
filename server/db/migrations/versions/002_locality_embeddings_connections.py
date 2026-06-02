"""Add locality_score and face_embedding to people, create service_connections table

Revision ID: 002
Revises: 001
Create Date: 2026-06-02 00:00:00.000000

"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("people", sa.Column("locality_score", sa.Float(), nullable=True))
    op.add_column("people", sa.Column("face_embedding", postgresql.JSONB(), nullable=True))

    op.create_table(
        "service_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("service_name", sa.String(), nullable=False, unique=True),
        sa.Column("status", sa.String(), nullable=False, server_default="disconnected"),
        sa.Column("last_connected_at", sa.DateTime()),
        sa.Column("meta", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime()),
    )


def downgrade() -> None:
    op.drop_table("service_connections")
    op.drop_column("people", "face_embedding")
    op.drop_column("people", "locality_score")
