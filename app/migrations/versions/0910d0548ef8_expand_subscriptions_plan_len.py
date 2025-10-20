from alembic import op
import sqlalchemy as sa

revision = "0910d0548ef8"
down_revision = "2981e2aafc94"



def upgrade():
    op.execute("SET lock_timeout TO '5s'")
    op.alter_column(
        "subscriptions",
        "plan",
        existing_type=sa.String(length=3),
        type_=sa.String(length=32),
        existing_nullable=False,
    )
    op.execute("RESET lock_timeout")

def downgrade():
    op.execute("SET lock_timeout TO '5s'")
    op.alter_column(
        "subscriptions",
        "plan",
        existing_type=sa.String(length=32),
        type_=sa.String(length=3),
        existing_nullable=False,
    )
    op.execute("RESET lock_timeout")
