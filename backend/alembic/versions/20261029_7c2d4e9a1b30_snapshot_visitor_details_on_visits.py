"""snapshot visitor details on visits

Revision ID: 7c2d4e9a1b30
Revises: 1618e688acc0
Create Date: 2026-10-29 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "7c2d4e9a1b30"
down_revision: str | None = "1618e688acc0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("visits") as batch_op:
        batch_op.add_column(sa.Column("visitor_full_name", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("visitor_phone", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("visitor_company", sa.String(length=120), nullable=True))

    # Backfill existing visits from the current visitor record (best available history).
    op.execute(
        """
        UPDATE visits SET
            visitor_full_name = (SELECT v.full_name FROM visitors v WHERE v.id = visits.visitor_id),
            visitor_phone = (SELECT v.phone FROM visitors v WHERE v.id = visits.visitor_id),
            visitor_company = (SELECT v.company FROM visitors v WHERE v.id = visits.visitor_id)
        """
    )

    with op.batch_alter_table("visits") as batch_op:
        batch_op.alter_column(
            "visitor_full_name", existing_type=sa.String(length=120), nullable=False
        )
        batch_op.alter_column("visitor_company", existing_type=sa.String(length=120), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("visits") as batch_op:
        batch_op.drop_column("visitor_company")
        batch_op.drop_column("visitor_phone")
        batch_op.drop_column("visitor_full_name")
