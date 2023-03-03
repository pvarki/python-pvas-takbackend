"""The Gino baseclass with db connection wrapping"""
from typing import Any
import uuid

from gino import Gino
from sqlalchemy.dialects.postgresql import UUID as saUUID
import sqlalchemy as sa


utcnow = sa.func.current_timestamp()
db = Gino()
DBModel: Any = db.Model  # workaround mypy being unhappy about using @property as baseclass


class BaseModel(DBModel):  # pylint: disable=R0903
    """Baseclass with common fields"""

    __table_args__ = {"schema": "takbackend"}

    pk = sa.Column(saUUID(), primary_key=True, default=uuid.uuid4)
    created = sa.Column(sa.DateTime(timezone=True), default=utcnow, nullable=False)
    updated = sa.Column(sa.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    deleted = sa.Column(sa.DateTime(timezone=True), nullable=True)
