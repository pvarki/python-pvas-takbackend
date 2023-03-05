"""tak client instances book-keeping"""
from typing import AsyncGenerator, List, cast
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

    @classmethod
    async def create_for(cls, instance: TAKInstance, prefix: str, max_clients: int) -> "ClientSequence":
        """Create one for server instance"""
        sequence = ClientSequence(
            server=instance.pk,
            prefix=prefix,
            max_clients=max_clients,
        )
        await sequence.create()
        refresh = await ClientSequence.get(sequence.pk)
        return cast(ClientSequence, refresh)

    @classmethod
    async def iter_instance_sequences(cls, server: TAKInstance) -> AsyncGenerator["ClientSequence", None]:
        """Resolve roles user has (sorted in descending priority so they're easier to merge) and yields one by one"""
        async with db.acquire() as conn:  # Cursors need transaction
            async with conn.transaction():
                async for cseq in ClientSequence.query.where(ClientSequence.server == server.pk).where(
                    ClientSequence.deleted == None  # pylint: disable=C0121 ; # "is None" will create invalid query
                ).gino.iterate():
                    yield cseq

    @classmethod
    async def list_instance_sequences(cls, server: TAKInstance) -> List["ClientSequence"]:
        """Consumes the iterator from iter_user_roles and returns a list"""
        ret = []
        async for role in cls.iter_instance_sequences(server):
            ret.append(role)
        return ret


class Client(BaseModel):  # pylint: disable=R0903
    """Keep track of assigned clients so we can offer unique urls for the users to fetch their info"""

    __tablename__ = "clients"

    server = sa.Column(saUUID(), sa.ForeignKey(TAKInstance.pk))
    sequence = sa.Column(saUUID(), sa.ForeignKey(ClientSequence.pk))
    name = sa.Column(sa.Unicode(), nullable=False)

    _idx = sa.Index("server_name_unique", "server", "name", unique=True)
