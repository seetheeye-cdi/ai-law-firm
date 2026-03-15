"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slack_team_id", sa.String(64), nullable=False),
        sa.Column("slack_team_name", sa.String(255), nullable=False),
        sa.Column("slack_bot_token", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slack_team_id"),
    )
    op.create_index("ix_clients_slack_team_id", "clients", ["slack_team_id"])

    op.create_table(
        "review_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("slack_channel_id", sa.String(64), nullable=False),
        sa.Column("slack_thread_ts", sa.String(64), nullable=False),
        sa.Column("slack_message_ts", sa.String(64), nullable=False),
        sa.Column("slack_user_id", sa.String(64), nullable=False),
        sa.Column("original_message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "ai_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("review_request_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model_used", sa.String(64), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["review_request_id"], ["review_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("review_request_id"),
    )

    op.create_table(
        "lawyer_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("review_request_id", sa.Uuid(), nullable=False),
        sa.Column("lawyer_id", sa.String(128), nullable=False),
        sa.Column("final_content", sa.Text(), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["review_request_id"], ["review_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("review_request_id"),
    )


def downgrade() -> None:
    op.drop_table("lawyer_reviews")
    op.drop_table("ai_reviews")
    op.drop_table("review_requests")
    op.drop_table("clients")
