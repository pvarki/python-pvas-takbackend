"""Add client models

Revision ID: 9cf2239fc992
Revises: a424058071b6
Create Date: 2023-03-03 23:16:54.357078

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "9cf2239fc992"  # pragma: allowlist secret
down_revision = "a424058071b6"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "clientsequences",
        sa.Column("server", postgresql.UUID(), nullable=True),
        sa.Column("prefix", sa.Unicode(), nullable=False),
        sa.Column("max_clients", sa.Integer(), nullable=False),
        sa.Column("next_client_no", sa.Integer(), nullable=False),
        sa.Column("pk", postgresql.UUID(), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["server"],
            ["takbackend.takinstances.pk"],
        ),
        sa.PrimaryKeyConstraint("pk"),
        schema="takbackend",
    )
    op.create_index("server_prefix_unique", "clientsequences", ["server", "prefix"], unique=True, schema="takbackend")
    op.create_table(
        "clients",
        sa.Column("server", postgresql.UUID(), nullable=True),
        sa.Column("sequence", postgresql.UUID(), nullable=True),
        sa.Column("name", sa.Unicode(), nullable=False),
        sa.Column("pk", postgresql.UUID(), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["sequence"],
            ["takbackend.clientsequences.pk"],
        ),
        sa.ForeignKeyConstraint(
            ["server"],
            ["takbackend.takinstances.pk"],
        ),
        sa.PrimaryKeyConstraint("pk"),
        schema="takbackend",
    )
    op.create_index("server_name_unique", "clients", ["server", "name"], unique=True, schema="takbackend")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index("server_name_unique", table_name="clients", schema="takbackend")
    op.drop_table("clients", schema="takbackend")
    op.drop_index("server_prefix_unique", table_name="clientsequences", schema="takbackend")
    op.drop_table("clientsequences", schema="takbackend")
    # ### end Alembic commands ###
