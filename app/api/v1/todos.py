import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDep
from app.models.todo import Todo
from app.schemas.todo import TodoCreate, TodoRead, TodoUpdate

router = APIRouter(prefix="/todos", tags=["todos"])


@router.get("", response_model=list[TodoRead])
async def list_todos(current_user: CurrentUser, db: DbDep) -> list[Todo]:
    """Return all todos for the authenticated user, newest first."""
    result = await db.execute(
        select(Todo)
        .where(Todo.user_id == current_user.id)
        .order_by(Todo.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=TodoRead, status_code=status.HTTP_201_CREATED)
async def create_todo(
    payload: TodoCreate, current_user: CurrentUser, db: DbDep
) -> Todo:
    """Create a new todo item owned by the authenticated user."""
    todo = Todo(**payload.model_dump(), user_id=current_user.id)
    db.add(todo)
    await db.commit()
    await db.refresh(todo)
    return todo


@router.get("/{todo_id}", response_model=TodoRead)
async def get_todo(todo_id: uuid.UUID, current_user: CurrentUser, db: DbDep) -> Todo:
    """Fetch a single todo by ID, enforcing ownership."""
    todo = await db.get(Todo, todo_id)
    if not todo or todo.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found"
        )

    return todo


@router.patch("/{todo_id}", response_model=TodoRead)
async def update_todo(
    todo_id: uuid.UUID, payload: TodoUpdate, current_user: CurrentUser, db: DbDep
) -> Todo:
    """Partially update a todo, enforcing ownership."""
    todo = await db.get(Todo, todo_id)
    if not todo or todo.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found"
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(todo, field, value)

    await db.commit()
    await db.refresh(todo)
    return todo


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(todo_id: uuid.UUID, current_user: CurrentUser, db: DbDep) -> None:
    """Delete a todo by ID, enforcing ownership."""
    todo = await db.get(Todo, todo_id)
    if not todo or todo.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found"
        )

    await db.delete(todo)
    await db.commit()
