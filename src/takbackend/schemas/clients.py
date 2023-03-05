"""Pydantic schemas for clients and sequences"""
from typing import Sequence
import logging
import uuid

from pydantic import Field, validator
from libadvian.binpackers import b64_to_uuid, ensure_str, ensure_utf8

from .base import CreateBase, DBBase
from .pager import PagerBase


# pylint: disable=R0903
LOGGER = logging.getLogger(__name__)


class ClientSequenceCreate(CreateBase):
    """Create ClientSequence objects"""

    server: uuid.UUID = Field(description="UUID of the TAKInstance")
    prefix: str = Field(
        regex=r"^[a-zA-Z0-9_]{3,}$",
        description="Client name prefix, ASCII characters and numbers only, minimum 3 characters",
        example="FOX_",
    )
    max_clients: int = Field(description="Max number of clients for this sequence")

    @classmethod
    @validator("server", pre=True)
    def server_must_be_uuid(cls, pkin: str) -> uuid.UUID:
        """Make sure the given source for UUID can be parsed"""
        try:
            getpk = b64_to_uuid(ensure_utf8(pkin))
        except ValueError:
            getpk = uuid.UUID(ensure_str(pkin))
        return getpk


class ClientSequenceDB(ClientSequenceCreate, DBBase):
    """Display/update ClientSequence objects"""

    next_client_no: int = Field(description="Next client number in sequence")


class ClientSequencePager(PagerBase):
    """List instances (paginated)"""

    items: Sequence[ClientSequenceDB] = Field(default_factory=list, description="The instances on this page")


class ClientDB(DBBase):
    """Display/update Client objects"""
