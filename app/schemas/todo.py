import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.todo import Priority


class TodoCreate(BaseModel):
    """Request schema for creating a new todo item."""

    title: str = Field(max_length=255)
    description: str | None = None
    priority: Priority = Priority.medium
    due_date: datetime | None = None


class TodoUpdate(BaseModel):
    """Partial-update schema for modifying an existing todo item; all fields are optional."""

    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    completed: bool | None = None
    priority: Priority | None = None
    due_date: datetime | None = None


class TodoRead(BaseModel):
    """Response schema representing a fully-populated todo item returned from the API."""

    id: uuid.UUID
    title: str
    description: str | None
    completed: bool
    priority: Priority
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
