---
name: solid-principles
description: "Use when designing classes, reviewing object-oriented code for architectural issues, evaluating inheritance vs composition, detecting SOLID violations, or explaining why code is hard to test, extend, or change. Triggers on: hard to test, too many dependencies, class does too much, ripple changes, cannot extend without modifying, breaking change, dependency injection, design review, architecture review, coupling, OOP design."
argument-hint: "Paste the code to analyze, or describe the design symptom you're seeing"
---

# SOLID Principles

Detection patterns, violation symptoms, and refactoring strategies for each of the five SOLID principles. Applied to Python with concrete examples.

## S — Single Responsibility Principle

**One reason to change.** A class should have exactly one actor whose requests drive its changes.

This is NOT about doing one thing in a narrow sense — it's about cohesion around a single **stakeholder**.

### Violation Symptoms

- Class name contains "And", "Manager", or "Handler" with no specifics
- Two completely different callers use different half of the class methods
- A test requires mocking 4+ unrelated things
- A business rule change also requires changing a persistence query

### Fix

Extract into separate classes grouped by **actor** (who triggers the change), not by topic.

```python
# VIOLATION: UserService handles both business logic AND email
class UserService:
    def register(self, email: str, password: str) -> User: ...
    def send_welcome_email(self, user: User) -> None: ...  # wrong actor

# FIX: split by actor
class UserRegistration:
    def register(self, email: str, password: str) -> User: ...

class WelcomeEmailSender:
    def send(self, user: User) -> None: ...
```

## O — Open/Closed Principle

**Open for extension, closed for modification.** Add new behavior without editing existing code.

### Violation Symptoms

- Every new feature adds an `if type == "X":` branch to an existing function
- Adding a payment method requires editing `PaymentProcessor`
- A `match`/`if-elif` on `type` enums that keeps growing
- Tests for existing behavior break when new behavior is added

### Fix

Use strategy pattern, polymorphism, or callable-based dispatch.

```python
# VIOLATION: grows with every new notification type
def send_notification(user, type: str):
    if type == "email":
        ...
    elif type == "sms":
        ...

# FIX: open for extension via protocol
class Notifier(Protocol):
    def send(self, user: User, message: str) -> None: ...

def notify(user: User, message: str, notifier: Notifier) -> None:
    notifier.send(user, message)
# New types: implement Notifier — no edits to notify()
```

## L — Liskov Substitution Principle

**Subtypes must be substitutable for their base types.** Code using `Base` must work unchanged with any `Derived`.

### Violation Symptoms

- Subclass raises `NotImplementedError` on inherited methods
- Subclass has STRICTER preconditions (rejects inputs the base accepts)
- Code checks `isinstance(x, SpecificSubclass)` before calling a method
- Subclass ignores a parameter that the base class treats as required

### Fix

Prefer composition over inheritance. If you can't substitute freely, the hierarchy is wrong — use a shared interface instead.

```python
# VIOLATION: Square is NOT a valid Liskov substitution for Rectangle
class Rectangle:
    def set_width(self, w: int): self._w = w
    def set_height(self, h: int): self._h = h

class Square(Rectangle):
    def set_width(self, w: int):   # Breaks: caller expects independent w/h
        self._w = self._h = w

# FIX: use a common Shape interface instead of inheritance
class Shape(Protocol):
    def area(self) -> float: ...
```

## I — Interface Segregation Principle

**Many specific interfaces over one large general interface.** Clients should not depend on methods they don't use.

### Violation Symptoms

- Implementation class has many `pass` or `raise NotImplementedError` methods
- A caller imports a class just to use 1 of its 10 methods
- Mocking a dependency in tests requires implementing 8 unused methods

### Fix

Split fat interfaces into smaller, focused `Protocol` classes in Python.

```python
# VIOLATION: implementors are forced to implement unneeded methods
class DataStore(Protocol):
    def read(self, key: str) -> bytes: ...
    def write(self, key: str, data: bytes) -> None: ...
    def delete(self, key: str) -> None: ...
    def list_keys(self) -> list[str]: ...
    def get_metadata(self, key: str) -> dict: ...

# FIX: segregated by use case
class Readable(Protocol):
    def read(self, key: str) -> bytes: ...

class Writable(Protocol):
    def write(self, key: str, data: bytes) -> None: ...

# ReadOnlyCache only depends on Readable — no write methods in scope
class ReadOnlyCache:
    def __init__(self, store: Readable) -> None: ...
```

## D — Dependency Inversion Principle

**Depend on abstractions, not concretions.** High-level policy must not depend on low-level details.

### Violation Symptoms

- Business logic directly instantiates database or HTTP client classes
- Unit test requires a real database, real filesystem, or real network
- Changing the database library forces changes in business logic
- Class creates its own dependencies with `__init__` that calls `SomeConcreteClass()`

### Fix

Inject dependencies at construction time. Define `Protocol` abstractions for infrastructure. This is also what makes unit testing fast.

```python
# VIOLATION: business logic depends on SQLAlchemy concretely
class TodoService:
    def __init__(self) -> None:
        self._db = AsyncSession(engine)  # direct dependency on infrastructure

# FIX: depend on a protocol (abstraction)
class TodoRepository(Protocol):
    async def get_by_id(self, todo_id: int) -> Todo | None: ...
    async def save(self, todo: Todo) -> Todo: ...
    async def delete(self, todo_id: int) -> None: ...

class TodoService:
    def __init__(self, repo: TodoRepository) -> None:  # injected
        self._repo = repo

# In tests: inject a fake/mock. In production: inject the SQLAlchemy implementation.
```

## Quick Diagnosis Guide

| Symptom                                                                 | Likely Violation | First Fix                                  |
| ----------------------------------------------------------------------- | ---------------- | ------------------------------------------ |
| Can't unit-test without spinning up a DB                                | D: DIP           | Inject a repository protocol               |
| Adding a new feature breaks existing tests                              | O: OCP           | Extract a strategy or plugin               |
| Subclass override raises `NotImplementedError`                          | L: LSP           | Replace inheritance with composition       |
| Had to stub 8 methods to test 1                                         | I: ISP           | Split the interface into smaller protocols |
| Two different teams request changes to the same class                   | S: SRP           | Split by actor                             |
| Class name ends in `Manager` or `Service` and no one knows what it does | S: SRP           | Name the actual responsibilities           |
