---
name: FastAPI REST API Design
description: "Use when designing new API endpoints, reviewing existing routes, creating Pydantic schemas, handling errors consistently, planning API versioning, or evaluating REST conventions. Triggers on: new endpoint, API design, REST, route, schema, status code, error handling, request model, response model, FastAPI route, versioning."
---

# FastAPI REST API Design

## URL Design

- Resources are **plural nouns**: `/todos`, `/users`, `/tokens`
- Nested for ownership relationships: `/users/{user_id}/todos`
- Sub-resource actions: POST to a descriptive path → `/todos/{id}/complete`
- No verbs in URLs: `/getTodo` ❌, `/todo/list` ❌
- Hyphens for multi-word paths: `/refresh-tokens` not `/refresh_tokens`
- IDs as path params for single resources, query params for filters:
  ```
  GET /todos/{id}           ← single resource by ID
  GET /todos?completed=true ← filtered collection
  ```

## HTTP Methods and Status Codes

| Operation        | Method | Success Code | Notes                                   |
| ---------------- | ------ | ------------ | --------------------------------------- |
| List collection  | GET    | 200          | Return array, with pagination metadata  |
| Get one resource | GET    | 200          | 404 if not found                        |
| Create resource  | POST   | 201          | Include `Location:` header with new URL |
| Full replace     | PUT    | 200          | Idempotent                              |
| Partial update   | PATCH  | 200          | Only specified fields change            |
| Delete           | DELETE | 204          | Empty body                              |
| Trigger action   | POST   | 200          | e.g. POST /todos/{id}/complete          |

## Consistent Error Responses

```python
# Use FastAPI's HTTPException — serializes to {"detail": "..."}
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Todo not found",          # String — client-displayable
)

raise HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="You do not own this todo", # Specific enough to be actionable
)
```

Common status codes to use correctly:

- `401 Unauthorized` — not authenticated (missing/invalid token)
- `403 Forbidden` — authenticated but not authorized (wrong user, missing role)
- `404 Not Found` — resource does not exist (or caller isn't allowed to know it does)
- `409 Conflict` — state conflict (duplicate email, invalid state transition)
- `422 Unprocessable Entity` — Pydantic validation failure (automatic)

## Pydantic Schema Design

```python
# Separate schema for each HTTP "direction"
class TodoCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None

class TodoUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    completed: bool | None = None

class TodoResponse(BaseModel):
    id: int
    title: str
    description: str | None
    completed: bool
    created_at: datetime
    owner_id: int

    model_config = ConfigDict(from_attributes=True)
```

Rules:

- Create, Update, and Response schemas are always separate — never reuse
- Response schemas include only what callers need (no internal fields, no passwords)
- Use `Field(...)` with constraints for validation at the boundary
- `model_config = ConfigDict(from_attributes=True)` on any schema that reads from ORM

## Route Handler Rules

```python
@router.post(
    "/todos/",
    response_model=TodoResponse,         # Always declare response_model
    status_code=status.HTTP_201_CREATED, # Always declare explicit status code
    summary="Create a new todo",         # Shows in OpenAPI docs
)
async def create_todo(
    todo_in: TodoCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TodoResponse:
    # Route handler is THIN: validate → call service/repo → return
    todo = await todo_repository.create(session, todo_in, owner_id=current_user.id)
    return TodoResponse.model_validate(todo)
```

- Handlers are thin — no business logic, no direct DB queries
- Delegate to repository functions or service layer
- Every parameter is a dependency injection or a Pydantic model
- No raw `dict` returns — always `response_model` with explicit schema

## Pagination (for list endpoints)

```python
@router.get("/todos/", response_model=list[TodoResponse])
async def list_todos(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),  # Hard cap at 100
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[TodoResponse]:
    ...
```

Always place a hard `le=100` cap on `limit` — never allow unlimited queries.

## Authentication Pattern (this project)

- JWT in `Authorization: Bearer <token>` header
- Dependency: `current_user: User = Depends(get_current_user)`
- Object-level authorization: always verify `resource.owner_id == current_user.id`
- Never trust the user to tell you who they are via the request body
