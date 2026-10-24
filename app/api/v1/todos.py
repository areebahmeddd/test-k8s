import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbDep
from app.models.todo import Todo
from app.models.user import User
from app.schemas.todo import TodoCreate, TodoRead, TodoUpdate

router = APIRouter(prefix="/todos", tags=["todos"])


async def _get_owned_todo(db: AsyncSession, todo_id: uuid.UUID, user: User) -> Todo:
    """Return the todo if it exists and belongs to the user; 404 otherwise."""
    todo = await db.get(Todo, todo_id)
    if todo is None or todo.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
    return todo


@router.get("", response_model=list[TodoRead])
async def list_todos(
    current_user: CurrentUser,
    db: DbDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[Todo]:
    """Return a page of the caller's todos, newest first."""
    result = await db.execute(
        select(Todo)
        .where(Todo.user_id == current_user.id)
        .order_by(Todo.created_at.desc(), Todo.id)
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars())


@router.post("", response_model=TodoRead, status_code=status.HTTP_201_CREATED)
async def create_todo(payload: TodoCreate, current_user: CurrentUser, db: DbDep) -> Todo:
    """Create a todo owned by the caller."""
    todo = Todo(**payload.model_dump(), user_id=current_user.id)
    db.add(todo)
    await db.commit()
    await db.refresh(todo)
    return todo


@router.get("/{todo_id}", response_model=TodoRead)
async def get_todo(todo_id: uuid.UUID, current_user: CurrentUser, db: DbDep) -> Todo:
    """Fetch one of the caller's todos by id."""
    return await _get_owned_todo(db, todo_id, current_user)


@router.patch("/{todo_id}", response_model=TodoRead)
async def update_todo(
    todo_id: uuid.UUID, payload: TodoUpdate, current_user: CurrentUser, db: DbDep
) -> Todo:
    """Update only the fields present in the request body."""
    todo = await _get_owned_todo(db, todo_id, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(todo, field, value)
    await db.commit()
    await db.refresh(todo)
    return todo


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(todo_id: uuid.UUID, current_user: CurrentUser, db: DbDep) -> None:
    """Delete one of the caller's todos."""
    todo = await _get_owned_todo(db, todo_id, current_user)
    await db.delete(todo)
    await db.commit()
