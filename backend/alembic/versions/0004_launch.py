"""FAQ, support relay, bot language and trip reminders.

Revision ID: 0004_launch
Revises: 0003_telegram_mvp
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_launch"
down_revision = "0003_telegram_mvp"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "faq_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lang", sa.String(2), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("question", sa.String(200), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_faq_items_lang", "faq_items", ["lang"])
    op.create_table(
        "telegram_support_messages",
        sa.Column("group_message_id", sa.BigInteger(), primary_key=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_telegram_support_messages_chat_id", "telegram_support_messages", ["chat_id"])
    op.add_column("telegram_chats", sa.Column("lang", sa.String(2)))
    op.add_column("reservations", sa.Column("reminder_day_sent_at", sa.DateTime(timezone=True)))
    op.add_column("reservations", sa.Column("reminder_soon_sent_at", sa.DateTime(timezone=True)))


def downgrade():
    op.drop_column("reservations", "reminder_soon_sent_at")
    op.drop_column("reservations", "reminder_day_sent_at")
    op.drop_column("telegram_chats", "lang")
    op.drop_index("ix_telegram_support_messages_chat_id", table_name="telegram_support_messages")
    op.drop_table("telegram_support_messages")
    op.drop_index("ix_faq_items_lang", table_name="faq_items")
    op.drop_table("faq_items")
