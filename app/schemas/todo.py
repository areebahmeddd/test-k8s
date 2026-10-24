import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.todo import Priority


class TodoCreate(BaseModel):
    """Request schema for creating a new todo item."""

    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    priority: Priority = Priority.medium
    due_date: datetime | None = None


class TodoUpdate(BaseModel):
    """Partial-update schema for an existing todo item; all fields are optional."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    completed: bool | None = None
    priority: Priority | None = None
    due_date: datetime | None = None

    @field_validator("title", "completed", "priority")
    @classmethod
    def reject_explicit_null(cls, v: object) -> object:
        """Allow omitting required columns, but not clearing them with null."""
        if v is None:
            raise ValueError("Field cannot be null")
        return v


class TodoRead(BaseModel):
    """Response schema for a todo item."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None
    completed: bool
    priority: Priority
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime
