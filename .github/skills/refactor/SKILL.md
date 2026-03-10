---
name: refactor
description: "Use when improving code structure without changing behavior: extracting functions, reducing cyclomatic complexity, applying design patterns, renaming for clarity, eliminating duplication, breaking apart god classes, or reducing coupling. Triggers on: refactor, cleanup, restructure, simplify, extract function, reduce complexity, technical debt, code smell, hard to maintain, hard to read."
argument-hint: "Paste the code to refactor, or describe the smell or structural problem"
---

# Refactor

Surgical code improvement that preserves external behavior. The goal is to make the next change easier, not to show off.

## The Golden Rule

**Never change behavior and structure at the same time.**

1. Get tests green (write characterization tests if none exist)
2. Refactor (behavior unchanged — tests still green)
3. Commit the refactoring
4. Then (in a SEPARATE commit) add new behavior if needed

This makes every commit reviewable, every rollback trivial.

## Procedure

### Step 1: Read Before Touching

- Read the ENTIRE function/class before modifying a single line
- Identify all callers — grep for usages before renaming or changing signatures
- Run existing tests to confirm they pass — these are your safety net
- **If there are no tests**: write characterization tests first that document current behavior (even weird behavior)

### Step 2: Identify the Smell

| Smell                   | Diagnostic                                   | Refactoring                         |
| ----------------------- | -------------------------------------------- | ----------------------------------- |
| Long Method             | >20 lines, >2 indentation levels             | Extract Method                      |
| Duplicate Code          | "copy-paste with edits"                      | Extract + DRY                       |
| Long Parameter List     | >3 params                                    | Introduce Parameter Object          |
| Data Clumps             | Same 3 vars travel together                  | Extract Class / dataclass           |
| Feature Envy            | Method uses more of other class than its own | Move Method                         |
| Temporary Field         | Instance var only set in some paths          | Extract Class                       |
| Switch/if-chain on type | `if isinstance(x, Foo): ...` repetition      | Replace with Polymorphism           |
| Nested Control Flow     | depth >2                                     | Early return / extract guard clause |
| Magic Literals          | `86400`, `"admin"`, `0.08`                   | Named Constants                     |
| God Class               | >200 lines, does many unrelated things       | Extract by Responsibility           |
| Inappropriate Intimacy  | Accesses private internals of another class  | Add delegation method               |

### Step 3: Apply One Refactoring at a Time

```
1. Make ONE change (e.g. extract one method)
2. Run tests → must still be green
3. Commit
4. Repeat
```

Never chain multiple refactorings without a commit boundary. Single-step changes make failures trivially debuggable.

### Step 4: Verify Equivalence

- All tests pass — no new test failures
- External API/interface unchanged (same function names, same return types)
- Performance equivalent or better
- If behavior DID change: that was a bug fix — commit it separately with a `fix:` commit message

## Extract Method — Step by Step

The most common and powerful refactoring:

```
1. Identify the fragment with a clear purpose
2. Name it from what it DOES (not how): `validate_email` not `check_string_format`
3. Copy fragment to new method with that name
4. Replace original fragment with a call to the new method
5. Run tests
6. Read the call site: does it read like English now?
7. Adjust name if it doesn't pass the "reads like English" test
```

## Python-Specific Refactorings

| Before                            | After                        | When                 |
| --------------------------------- | ---------------------------- | -------------------- |
| `for x in xs: result.append(...)` | List comprehension           | Simple transform     |
| `(x, y, z)` tuple everywhere      | `@dataclass` or `NamedTuple` | Data clump           |
| `try/finally: f.close()`          | `with open(...) as f:`       | Resource management  |
| Expensive re-computed property    | `@functools.cached_property` | Read-heavy access    |
| `isinstance()` chains             | `Protocol` + dispatch        | Type-based branching |
| Nested `if/else` returning values | Guard clauses (early return) | Readability          |

**Early return over else:**

```python
# BEFORE: nested, hard to follow
def process(user):
    if user is not None:
        if user.is_active:
            if user.has_permission("write"):
                return do_work(user)
            else:
                return PermissionError()

# AFTER: flat, each guard self-explanatory
def process(user):
    if user is None:
        raise ValueError("user required")
    if not user.is_active:
        raise ValueError("user is not active")
    if not user.has_permission("write"):
        raise PermissionError("write permission required")
    return do_work(user)
```

## What NOT to Do

- Do not refactor AND add features in the same PR — reviewers cannot tell what changed
- Do not over-abstract for hypothetical future use cases (YAGNI)
- Do not rename just because of personal style preference — only rename if the name is genuinely misleading
- Do not break the public API without a migration path and version bump
- Do not introduce a new abstraction if it will only be used once
