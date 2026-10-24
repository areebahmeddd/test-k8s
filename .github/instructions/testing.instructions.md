---
name: Testing
description: pytest conventions for unit and integration tests.
applyTo: "tests/**/*.py"
---

# Testing

- `tests/unit/` holds pure logic with no I/O. `tests/integration/` drives the app through the `client` fixture.
- `asyncio_mode = "auto"` is set, so write `async def test_...` without markers.
- Shared fixtures in `tests/conftest.py`: `client`, `db_session` (direct database access to arrange state),
  `registered_user`, `tokens` and `auth_headers`. Each test gets a fresh SQLite database.
- Name tests `test_<subject>_<behavior>` and give each one a one-line docstring that states the expectation.
- Group tests by endpoint or function, and use `pytest.mark.parametrize` with readable `ids` instead of
  copying a test for each input.
- Assert the HTTP contract (status code, response body, state change), not implementation details.
- Cover the failure paths on purpose: 401, 404 (including another user's resource), 409 and 422.
- Code that installs process-wide state, such as tracing, is tested in a subprocess (see `test_telemetry.py`).
- Never call real external services. Tests must pass offline and in any order.
- Rego policies are tested in `policy/policies_test.rego` and run with `conftest verify`.
