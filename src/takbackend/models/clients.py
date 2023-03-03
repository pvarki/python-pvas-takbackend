"""tak client instances book-keeping"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as saUUID

from .base import BaseModel
from .instance import TAKInstance

DEFAULT_MAX_CLIENTS = 100


class ClientSequence(BaseModel):  # pylint: disable=R0903
    """Used to grab the next client name and redirect to unique url for that"""

    __tablename__ = "clientsequences"

    server = sa.Column(saUUID(), sa.ForeignKey(TAKInstance.pk))
    prefix = sa.Column(sa.Unicode(), nullable=False)
    max_clients = sa.Column(sa.Integer, nullable=False, default=DEFAULT_MAX_CLIENTS)
    next_client_no = sa.Column(sa.Integer, nullable=False, default=1)

    _idx = sa.Index("server_prefix_unique", "server", "prefix", unique=True)


class Client(BaseModel):  # pylint: disable=R0903
    """Keep track of assigned clients so we can offer unique urls for the users to fetch their info"""

    __tablename__ = "clients"

    server = sa.Column(saUUID(), sa.ForeignKey(TAKInstance.pk))
    sequence = sa.Column(saUUID(), sa.ForeignKey(ClientSequence.pk))
    name = sa.Column(sa.Unicode(), nullable=False)

    _idx = sa.Index("server_name_unique", "server", "name", unique=True)
