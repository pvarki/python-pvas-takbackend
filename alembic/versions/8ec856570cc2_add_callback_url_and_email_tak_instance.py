"""Add callback url and email tak-instance

Revision ID: 8ec856570cc2
Revises: 9cf2239fc992
Create Date: 2023-03-05 19:23:42.399451

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8ec856570cc2"  # pragma: allowlist secret
down_revision = "9cf2239fc992"  # pragma: allowlist secret
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("takinstances", sa.Column("ready_email", sa.String(), nullable=True), schema="takbackend")
    op.add_column("takinstances", sa.Column("ready_callback_url", sa.String(), nullable=True), schema="takbackend")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("takinstances", "ready_callback_url", schema="takbackend")
    op.drop_column("takinstances", "ready_email", schema="takbackend")
    # ### end Alembic commands ###
