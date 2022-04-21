"""create publisher table

Revision ID: cedc71e8ee67
Revises: 
Create Date: 2022-04-12 13:55:49.937972

"""
import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "cedc71e8ee67"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "publisher",
        sa.Column("id", sqlmodel.sql.sqltypes.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_edited", sa.DateTime(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("is_account_admin", sa.Boolean(), nullable=False),
        sa.Column("is_repo_admin", sa.Boolean(), nullable=False),
        sa.Column("is_package_admin", sa.Boolean(), nullable=False),
        sa.Column("icm_service", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("icm_team", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("contact_email", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_publisher_id"), "publisher", ["id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_publisher_id"), table_name="publisher")
    op.drop_table("publisher")
