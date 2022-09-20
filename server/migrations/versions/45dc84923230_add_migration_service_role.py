"""add migration service role

Revision ID: 45dc84923230
Revises: 067f450caa29
Create Date: 2022-09-15 20:33:00.945693

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = '45dc84923230'
down_revision = '067f450caa29'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE role ADD VALUE 'Migration'")


def downgrade():
    # can't remove a value from an enum in postgres
    raise Exception("Cannot reverse migration.")
