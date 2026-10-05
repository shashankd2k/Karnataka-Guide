"""
SQLAlchemy 2.x Declarative Base with AsyncAttrs.
"""

from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all SQLAlchemy declarative ORM models."""
    pass
