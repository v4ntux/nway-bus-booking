"""seats: women-only flag

Revision ID: 0002_seat_women_only
Revises: 0001_initial
Create Date: 2026-08-14
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_seat_women_only"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "seats",
        sa.Column(
            "is_women_only",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("seats", "is_women_only")
