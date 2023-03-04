"""tak client instances book-keeping"""
from typing import cast
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as saUUID

from .base import BaseModel, db
from .instance import TAKInstance


DEFAULT_MAX_CLIENTS = 100


class MaxclientsError(ValueError):
    """Specific error for max_clients exceeded"""


class ClientSequence(BaseModel):  # pylint: disable=R0903
    """Used to grab the next client name and redirect to unique url for that"""

    __tablename__ = "clientsequences"

    server = sa.Column(saUUID(), sa.ForeignKey(TAKInstance.pk))
    prefix = sa.Column(sa.Unicode(), nullable=False)
    max_clients = sa.Column(sa.Integer, nullable=False, default=DEFAULT_MAX_CLIENTS)
    next_client_no = sa.Column(sa.Integer, nullable=False, default=1)

    _idx = sa.Index("server_prefix_unique", "server", "prefix", unique=True)

    async def next_client(self) -> "Client":
        """Atomic creation of next client"""
        async with db.transaction():
            refresh = await ClientSequence.query.where(ClientSequence.pk == self.pk).with_for_update().gino.first()
            if refresh.next_client_no > refresh.max_clients:
                raise MaxclientsError("max_clients exceeded")
            zeros_count = len(f"{refresh.max_clients}")
            name_fmt = f"{refresh.prefix}{refresh.next_client_no:0{zeros_count}}"
            client = Client(server=self.server, sequence=self.pk, name=name_fmt)
            await client.create()
            client_refresh = await Client.get(client.pk)
            await refresh.update(next_client_no=refresh.next_client_no + 1).apply()
        return cast(Client, client_refresh)


class Client(BaseModel):  # pylint: disable=R0903
    """Keep track of assigned clients so we can offer unique urls for the users to fetch their info"""

    __tablename__ = "clients"

    server = sa.Column(saUUID(), sa.ForeignKey(TAKInstance.pk))
    sequence = sa.Column(saUUID(), sa.ForeignKey(ClientSequence.pk))
    name = sa.Column(sa.Unicode(), nullable=False)

    _idx = sa.Index("server_name_unique", "server", "name", unique=True)
