from __future__ import annotations

import uuid
from enum import StrEnum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Priority(StrEnum):
    """Enumeration of valid priority levels for a todo item."""

    low = "low"
    medium = "medium"
    high = "high"


class Todo(Base, TimestampMixin):
    """ORM model representing a user-owned todo item with priority and completion state."""

    __tablename__ = "todos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed: Mapped[bool] = mapped_column(default=False)
    priority: Mapped[Priority] = mapped_column(
        SAEnum(Priority), default=Priority.medium
    )
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    owner: Mapped[User] = relationship(back_populates="todos")
