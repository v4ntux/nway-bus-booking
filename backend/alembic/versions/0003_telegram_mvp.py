"""Durable Telegram booking flow and idempotent ticket delivery.

Revision ID: 0003_telegram_mvp
Revises: 0002_seat_women_only
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_telegram_mvp"
down_revision = "0002_seat_women_only"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("reservations", sa.Column("booking_request_key", sa.String(100)))
    op.create_unique_constraint("uq_reservations_booking_request_key", "reservations", ["booking_request_key"])
    op.add_column("reservations", sa.Column("telegram_chat_id", sa.BigInteger()))
    op.create_index("ix_reservations_telegram_chat_id", "reservations", ["telegram_chat_id"])
    op.create_table(
        "telegram_chats",
        sa.Column("chat_id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("phone", sa.String(32)),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "telegram_updates",
        sa.Column("update_id", sa.BigInteger(), primary_key=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.String(100)),
    )
    op.create_index("ix_telegram_updates_available_at", "telegram_updates", ["available_at"])
    op.create_table(
        "telegram_deliveries",
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tickets.id"), primary_key=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_error", sa.String(100)),
    )


def downgrade():
    op.drop_table("telegram_deliveries")
    op.drop_table("telegram_updates")
    op.drop_table("telegram_chats")
    op.drop_index("ix_reservations_telegram_chat_id", table_name="reservations")
    op.drop_column("reservations", "telegram_chat_id")
    op.drop_constraint("uq_reservations_booking_request_key", "reservations", type_="unique")
    op.drop_column("reservations", "booking_request_key")
