"""Pydantic schemas for deployed instances"""
from typing import Optional, Sequence, Dict, Any
import datetime
import logging

from pydantic import Field

from .base import CreateBase, DBBase
from .pager import PagerBase


# pylint: disable=R0903
LOGGER = logging.getLogger(__name__)


class TAKInstanceCreate(CreateBase):
    """Create TAKInstance objects"""

    ownerid: str = Field(description="Who owns this, usually should point to 'userid' in JWT")
    color: str = Field(description="Color of this deployment, HTML 6-character RGB code #rrggbb, no alpha")
    grouping: str = Field(description="Arbitrary string to group deployments by", default="_")
    server_name: str = Field(description="TAK-Server name shown to clients")
    sequence_prefix: Optional[str] = Field(
        description="Autogenerate ClientSequence with this prefix for this instance", nullable=True, default=None
    )
    sequence_max: Optional[int] = Field(
        description="Autogenerate ClientSequence with this many clients for this instance", nullable=True, default=None
    )


class TAKDBInstance(DBBase):
    """Display/update TAKInstance objects"""

    ownerid: str = Field(description="Who owns this, usually should point to 'userid' in JWT")
    color: str = Field(description="Color of this deployment, HTML 6-character RGB code #rrggbb, no alpha")
    grouping: str = Field(description="Arbitrary string to group deployments by", default="_")
    server_name: str = Field(description="TAK-Server name shown to clients")

    tfcompleted: Optional[datetime.datetime] = Field(
        description="When was the TerraForm pipeline completed", nullable=True, default=None
    )
    tfinputs: Optional[Dict[str, Any]] = Field(description="Inputs given to TerraForm, only visible to admins")
    tfoutputs: Optional[Dict[str, Any]] = Field(description="Outpust from TerraForm, only visible to admins")
    enduser_instructions: Optional[str] = Field(
        description="URL you can give to end-users of the service, contains instructions and connection info"
    )
    owner_instructions: Optional[str] = Field(
        description="Like enduser_instructions but has more information (like server superuser password)"
    )


class TAKInstancePager(PagerBase):
    """List instances (paginated)"""

    items: Sequence[TAKDBInstance] = Field(default_factory=list, description="The instances on this page")
