# FastAPI REST API Design

## URL Conventions

- Resources are **plural nouns**: `/todos`, `/users`, `/tokens`
- Nested for ownership: `/users/{user_id}/todos`
- Sub-resource actions as POST: `/todos/{id}/complete`
- No verbs in URLs · Hyphens for multi-word: `/refresh-tokens`

## HTTP Methods and Status Codes

| Operation        | Method | Success | Notes                        |
| ---------------- | ------ | ------- | ---------------------------- |
| List collection  | GET    | 200     | Array + pagination metadata  |
| Get one resource | GET    | 200     | 404 if not found             |
| Create resource  | POST   | 201     | Include `Location:` header   |
| Full replace     | PUT    | 200     | Idempotent                   |
| Partial update   | PATCH  | 200     | Only specified fields change |
| Delete           | DELETE | 204     | Empty body                   |
| Trigger action   | POST   | 200     | e.g. `/todos/{id}/complete`  |

Status codes to use correctly:

- `401` — not authenticated (missing/invalid token)
- `403` — authenticated but not authorized (wrong user)
- `404` — resource does not exist
- `409` — state conflict (duplicate email, invalid transition)
- `422` — Pydantic validation failure (automatic)

## Pydantic Schema Design

```python
# Separate schema per HTTP direction
class TodoCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None

class TodoResponse(BaseModel):
    id: int
    title: str
    completed: bool
    created_at: datetime
    owner_id: int

    model_config = ConfigDict(from_attributes=True)
```

## Rules

- One schema file per domain area in `app/schemas/`
- `Create` / `Update` / `Response` suffix pattern — no schema for all three directions
- `Update` schemas: all fields optional (partial updates)
- Never return raw ORM objects from route handlers
- Every route must have `response_model=` set
