"""expand payment plan & invoice columns"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# === Alembic metadata ===
revision: str = "93da2b239aea"
down_revision = "0910d0548ef8"

branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Увеличиваем длины колонок в payments
    op.alter_column(
        "payments",
        "plan",
        existing_type=sa.String(length=8),
        type_=sa.String(length=32),
        existing_nullable=False,
    )

    op.alter_column(
        "payments",
        "provider_invoice_id",
        existing_type=sa.String(length=8),
        type_=sa.String(length=64),
        existing_nullable=False,
    )

    op.alter_column(
        "payments",
        "provider",
        existing_type=sa.String(length=8),
        type_=sa.String(length=16),
        existing_nullable=False,
    )

    op.alter_column(
        "payments",
        "status",
        existing_type=sa.String(length=8),
        type_=sa.String(length=16),
        existing_nullable=False,
    )


def downgrade() -> None:
    # ⚠ Возможна обрезка данных при даунгрейде
    op.alter_column(
        "payments",
        "status",
        existing_type=sa.String(length=16),
        type_=sa.String(length=8),
        existing_nullable=False,
    )

    op.alter_column(
        "payments",
        "provider",
        existing_type=sa.String(length=16),
        type_=sa.String(length=8),
        existing_nullable=False,
    )

    op.alter_column(
        "payments",
        "provider_invoice_id",
        existing_type=sa.String(length=64),
        type_=sa.String(length=8),
        existing_nullable=False,
    )

    op.alter_column(
        "payments",
        "plan",
        existing_type=sa.String(length=32),
        type_=sa.String(length=8),
        existing_nullable=False,
    )
