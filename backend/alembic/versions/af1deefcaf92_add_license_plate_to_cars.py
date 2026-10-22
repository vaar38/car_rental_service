"""add license_plate to cars

Revision ID: af1deefcaf92
Revises: 3cecddc1d840
Create Date: 2026-10-22 14:45:52.482038

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'af1deefcaf92'
down_revision: Union[str, Sequence[str], None] = '3cecddc1d840'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Сначала колонка может быть пустой, чтобы миграция прошла на базе,
    # где машины уже есть. Им ставим временный уникальный номер.
    op.add_column("cars", sa.Column("license_plate", sa.String(20), nullable=True))
    op.execute("UPDATE cars SET license_plate = 'TEMP-' || id WHERE license_plate IS NULL")
    op.alter_column("cars", "license_plate", nullable=False)
    op.create_unique_constraint("uq_cars_license_plate", "cars", ["license_plate"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_cars_license_plate", "cars")
    op.drop_column("cars", "license_plate")
