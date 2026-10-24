---
name: API design
description: Conventions for FastAPI route handlers under app/api.
applyTo: "app/api/**/*.py"
---

# API design

- Routes live under `/api/v1`, one router per resource (`auth.py`, `todos.py`), registered in `router.py`.
- Collections are plural nouns without trailing slashes: `GET /api/v1/todos`, `GET /api/v1/todos/{todo_id}`.
- Every route declares `response_model` (or returns `None` with `204`) and an explicit `status_code` when it isn't 200.
- Use the shared dependencies from `app/api/deps.py`: `DbDep` for the session, `CurrentUser` for authentication.
- Separate Create / Update / Read schemas in `app/schemas/`. Update schemas are partial: apply
  `model_dump(exclude_unset=True)` and reject explicit `null` for non-nullable columns.
- List endpoints paginate with `offset` and `limit` (`le=100`).
- Status codes: 401 unauthenticated, 403 authenticated but not allowed (for example, an inactive user),
  404 missing **or owned by someone else**, 409 uniqueness conflict, 422 validation (automatic).
- Errors use `HTTPException(status_code=status.HTTP_..., detail="Human-readable message")`.
- Rely on database constraints for uniqueness (catch `IntegrityError` and return 409) rather than checking first and then inserting.
