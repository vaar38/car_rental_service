"""use half-open date range in no_overlapping_bookings

Revision ID: 3cecddc1d840
Revises: 297774f910a1
Create Date: 2026-10-12 16:21:34.106892

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3cecddc1d840'
down_revision: Union[str, Sequence[str], None] = '297774f910a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint("no_overlapping_bookings", "bookings")
    op.execute("""
        ALTER TABLE bookings
        ADD CONSTRAINT no_overlapping_bookings
        EXCLUDE USING gist (
            car_id WITH =,
            daterange(start_date, end_date, '[)') WITH &&
        )
        WHERE (status IN ('pending', 'confirmed', 'active'))
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("no_overlapping_bookings", "bookings")
    op.execute("""
            ALTER TABLE bookings
            ADD CONSTRAINT no_overlapping_bookings
            EXCLUDE USING gist (
                car_id WITH =,
                daterange(start_date, end_date, '[]') WITH &&
            )
            WHERE (status IN ('pending', 'confirmed', 'active'))
        """)
