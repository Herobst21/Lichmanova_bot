from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# Alembic identifiers
revision = "20251012_add_auto_renew"
down_revision = "2981e2aafc94"  # должно идти ПОСЛЕ 0001_initial
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)

    # если таблицы нет — выходим тихо
    if "subscriptions" not in insp.get_table_names():
        return

    cols = {c["name"] for c in insp.get_columns("subscriptions")}
    if "auto_renew" not in cols:
        op.add_column(
            "subscriptions",
            sa.Column("auto_renew", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
        op.alter_column("subscriptions", "auto_renew", server_default=None)


def downgrade():
    bind = op.get_bind()
    insp = inspect(bind)

    if "subscriptions" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("subscriptions")}
        if "auto_renew" in cols:
            op.drop_column("subscriptions", "auto_renew")
