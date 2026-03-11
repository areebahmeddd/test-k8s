---
name: quasi-coder
description: "Use when you want to describe code in natural language, shorthand, pseudo-code, or abbreviated notation and have it transformed into production-quality implementation that matches this project's conventions. Triggers on: implement this idea, convert this pseudo-code, write this properly, turn this into Python, my rough idea is, implement this logic, here's what I want to happen, sketch this out."
argument-hint: "Write your pseudo-code, shorthand, or natural language description of the logic"
---

# Quasi-Coder

Transforms pseudo-code, rough ideas, shorthand, and natural language into production-quality implementation that matches the existing codebase's patterns.

## What This Handles

- Pseudo-code (language-agnostic) → idiomatic Python
- Domain-expert shorthand → complete implementation
- English descriptions of business logic → correct code with edge cases
- Abbreviated snippets → full function with types, error handling, tests
- Architecture sketches → concrete implementation plan

## Procedure

### Step 1: Parse Intent

Before writing any code:

- Restate what the requester wants in one sentence
- Identify: **inputs**, **outputs**, **side effects**, **error conditions**
- Flag any ambiguities that would affect correctness (don't guess on these — ask)

Common ambiguities to surface:

- What happens when the input is empty/null/zero?
- Should errors be raised, returned, or logged?
- Is this synchronous or called in an async context?
- Does this touch the database? Which model?

### Step 2: Infer Context from Codebase

Before writing, check what already exists:

- **Naming conventions**: look at adjacent functions in the same file
- **Error handling patterns**: how do nearby functions handle failures?
- **Existing utilities**: search for similar operations already implemented
- **Framework patterns**: how routes, queries, and schemas are structured in adjacent code

The best code is consistent code — it should look like it belonged here from the start.

### Step 3: Implement to Production Standard

Apply the full quality bar:

- **Type annotations**: every parameter and return type
- **Error handling**: all failure modes are handled explicitly
- **No magic literals**: named constants for any hardcoded value
- **Async**: if the context is async, use `async def` and `await` correctly
- **Minimal**: no speculative complexity, no parameters that aren't used
- **Idiomatic**: uses the language/framework feature that was designed for this case

### Step 4: Annotate Decisions

After the implementation, always provide:

```
## What I implemented
[One sentence summary]

## Key decisions
- [Decision 1: why you chose X over Y]
- [Decision 2: assumption made about Z]

## Not handled (would need extending)
- [Edge case 1]
- [Edge case 2]
```

## Quality Checklist

Before delivering any implementation:

- [ ] Type annotations on every parameter and return value
- [ ] All error paths are explicitly handled (not silently swallowed)
- [ ] No hardcoded configuration values — environment variables or settings
- [ ] No N+1 database patterns
- [ ] Naming is accurate to what the code actually does (not what was sketched)
- [ ] No over-engineering: YAGNI applies — implement what was asked, not what might be needed
- [ ] Async context is correct: `async def` if called from async context, `await` is present

## Example Transformation

**Input (pseudo-code):**

```
get all todos for user
only completed ones
sorted by when they were done
return as list
```

**Output:**

```python
async def get_completed_todos(
    user_id: int,
    session: AsyncSession,
) -> list[Todo]:
    """Return completed todos for a user, ordered by completion time (newest first)."""
    result = await session.execute(
        select(Todo)
        .where(Todo.user_id == user_id, Todo.completed == True)  # noqa: E712
        .order_by(Todo.updated_at.desc())
    )
    return list(result.scalars().all())
```

**Annotations:**

- `updated_at` used as proxy for completion time — if you add a `completed_at` field, use that instead
- Returns empty list (not `None`) when no todos found — callers don't need to null-check
- Not handled: pagination — add `.limit()` / `.offset()` if this list can grow large
