"""tak server instance book-keeping"""
from sqlalchemy.dialects.postgresql import JSONB
import sqlalchemy as sa

from .base import BaseModel


class TAKInstance(BaseModel):  # pylint: disable=R0903
    """Instance of TAK server"""

    __tablename__ = "takinstances"

    # usually probably uuids but might not be if a11n backend changed
    ownerid = sa.Column(sa.Unicode(), nullable=False, index=True)
    color = sa.Column(sa.String(), nullable=False, index=True)
    grouping = sa.Column(sa.Unicode(), nullable=False, default="", index=True)

    tfcompleted = sa.Column(sa.DateTime(timezone=True), nullable=True)
    tfinputs = sa.Column(JSONB, nullable=False, server_default="{}")
    tfoutputs = sa.Column(JSONB, nullable=False, server_default="{}")
