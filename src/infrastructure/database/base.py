"""Base SQLAlchemy models with common functionality.

This module provides:
- Base model with UUID primary key
- Automatic created_at and updated_at timestamps
- Soft delete support with deleted_at
- Common query methods
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        index=True,
    )


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""

    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None, index=True)

    @property
    def is_deleted(self) -> bool:
        """Check if record is soft deleted.

        Returns:
            True if deleted, False otherwise.
        """
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Soft delete the record."""
        self.deleted_at = datetime.utcnow()

    def restore(self) -> None:
        """Restore soft deleted record."""
        self.deleted_at = None


class BaseModel(Base, TimestampMixin, SoftDeleteMixin):
    """Base model with UUID, timestamps, and soft delete.

    All models should inherit from this class to get:
    - UUID primary key (id)
    - created_at timestamp
    - updated_at timestamp (auto-updated)
    - deleted_at timestamp (for soft delete)
    - Soft delete methods
    """

    __abstract__ = True

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
        index=True,
    )

    @declared_attr
    def __tablename__(cls) -> str:
        """Generate __tablename__ automatically from class name.

        Returns:
            Table name in lowercase.
        """
        return cls.__name__.lower()

    def to_dict(self, exclude: set[str] | None = None) -> dict[str, Any]:
        """Convert model to dictionary.

        Args:
            exclude: Set of field names to exclude.

        Returns:
            Dictionary representation of the model.
        """
        exclude = exclude or set()
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
            if column.name not in exclude
        }

    def __repr__(self) -> str:
        """String representation of the model.

        Returns:
            Model representation.
        """
        return f"<{self.__class__.__name__}(id={self.id})>"
