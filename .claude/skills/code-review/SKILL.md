---
name: code-review
description: "Use when reviewing code for correctness, security vulnerabilities, performance issues, maintainability, or test coverage before merging. Triggers on: review this code, is this safe, is this correct, find bugs, security audit, pre-merge review, check this function, what's wrong with this, code quality, OWASP check."
argument-hint: "Paste code to review, or reference the file or PR to analyze"
---

# Code Review

Systematic adversarial review across five dimensions. Produces actionable findings, not style opinions.

## Review Order (Highest to Lowest Impact)

1. **Security** — vulnerabilities ship to production and affect real users
2. **Correctness** — logic errors, edge cases, race conditions
3. **Performance** — bottlenecks, N+1 queries, blocking async
4. **Maintainability** — naming, complexity, coupling, dead code
5. **Test Coverage** — missing cases, incorrect assertions

## 1. Security Checklist (OWASP Top 10)

- [ ] **Injection (A03)**: Is any user input ever passed to SQL, shell, template, `eval()`, or subprocess without parameterization?
- [ ] **Broken Auth (A07)**: Are all state-changing endpoints behind authentication checks? Are tokens validated on every request?
- [ ] **Broken AuthZ (A01)**: Does the code verify the **caller** has permission for the **specific resource** (not just "is logged in")?
- [ ] **Sensitive Data (A02)**: Is PII/sensitive data logged, included in error messages, or returned unnecessarily?
- [ ] **Hardcoded Secrets**: Are credentials, API keys, or tokens hardcoded or committed to Git?
- [ ] **Cryptography (A02)**: Is hashing done with bcrypt/argon2 (not MD5/SHA1/SHA256 for passwords)?
- [ ] **Deserialization (A08)**: Is untrusted data deserialized via `pickle`, `yaml.load()`, or `eval()`?
- [ ] **SSRF (A10)**: Does the code make HTTP requests to user-supplied URLs without domain allowlist validation?
- [ ] **Mass Assignment**: Are all input fields explicitly declared? Is `**kwargs` from user input used to update model fields?
- [ ] **Path Traversal**: Are user-supplied file paths sanitized before filesystem operations?

## 2. Correctness Checklist

- [ ] **Edge cases**: empty collections, `None`/`null`, zero, negative numbers, maximum values, off-by-one
- [ ] **Race conditions**: shared mutable state accessed concurrently, check-then-act patterns without locks
- [ ] **Error handling**: exceptions caught at the right level? Errors silently swallowed?
- [ ] **Type safety**: do return types and parameter types match actual behavior?
- [ ] **Async correctness**: is every coroutine `await`-ed? Any fire-and-forget without error handling?
- [ ] **Logic correctness**: does the code actually do what the author intended? Read it line by line.

## 3. Performance Checklist

- [ ] **N+1 queries**: database queries inside loops — should be batch-fetched with `selectinload` / `joinedload`
- [ ] **Unindexed queries**: `WHERE` / `ORDER BY` on columns without indexes
- [ ] **Blocking async**: `requests.get()`, `time.sleep()`, `open()` called in async context without `to_thread()`
- [ ] **Unbounded queries**: no `LIMIT` clause on list endpoints
- [ ] **Repeated expensive calls**: same computation in a loop that should be cached or hoisted

## 4. Maintainability Checklist

- [ ] **Naming**: do names explain intent? Would a new engineer understand without asking?
- [ ] **Complexity**: cyclomatic complexity >10 is a refactoring signal
- [ ] **Coupling**: does adding a feature require changing 5+ files?
- [ ] **Non-obvious decisions**: commented with WHY (business rule, constraint, historical reason)?
- [ ] **Dead code**: unreachable branches, unused imports, unused variables?

## 5. Test Coverage Checklist

- [ ] **Happy path**: tested?
- [ ] **Error paths**: tested? (404, 422, 500 cases)
- [ ] **Edge cases**: boundary values, empty inputs, max inputs?
- [ ] **Test quality**: assertions on behavior, not on implementation details?
- [ ] **Flakiness signals**: `time.sleep()`, real external HTTP calls, order-dependent tests?

## Output Format

```
## Security
🔴 [CRITICAL] app/api/v1/todos.py line 45
  SQL query built via f-string — use SQLAlchemy parameterized queries
  Fix: `session.execute(select(Todo).where(Todo.id == todo_id))`

🟡 [MAJOR] app/api/v1/todos.py line 12
  JWT token value logged in debug line — remove or mask

## Correctness
🟡 [MAJOR] app/api/v1/users.py line 78
  `users[0]` will raise IndexError when list is empty
  Fix: check `if not users:` before indexing

## Performance
🟢 [MINOR] app/api/v1/todos.py lines 23–31
  N+1 query — iterating over todos and querying user for each
  Fix: `.options(selectinload(Todo.user))`

## Maintainability
💡 [INFO] app/core/security.py line 55
  Function `process` operates at three abstraction levels — consider extracting

## Tests
🟡 [MAJOR] tests/integration/test_todos.py
  Error path when authenticated user requests another user's todo is not tested
```

## Severity Legend

| Symbol | Severity | Action                                                             |
| ------ | -------- | ------------------------------------------------------------------ |
| 🔴     | CRITICAL | Must fix before merge — security or data integrity risk            |
| 🟡     | MAJOR    | Should fix before merge — likely bug or significant technical debt |
| 🟢     | MINOR    | Consider fixing — performance or readability improvement           |
| 💡     | INFO     | Worth discussing — design suggestion, future consideration         |
