---
name: clean-code
description: "Use when writing new code, reviewing code for readability, improving naming conventions, reducing function size, eliminating code smells, or applying Robert Martin Clean Code principles. Triggers on: naming, code smell, spaghetti code, function too long, magic numbers, unclear intent, hard to read, clean up this code, simplify, god function, side effects."
argument-hint: "Paste code to clean, or describe the naming or structure problem"
---

# Clean Code

Applies Robert Martin's Clean Code principles systematically. Code should read like well-written prose — intent visible without comments.

> "The ratio of time spent reading versus writing code is well over 10 to 1.  
> We are constantly reading old code as part of the effort to write new code."  
> — Robert C. Martin

## Naming Conventions

### Functions

- Name from the **caller's perspective**: what it does, not how it does it
- Functions that return values: noun phrases → `getUserById`, `calculateTotal`
- Functions with side effects: verb phrases → `sendEmail`, `saveRecord`
- Boolean predicates: `is`, `has`, `can`, `should` prefix → `isAuthenticated`, `hasPermission`
- **Never** encode type in the name: `userList` → `users`, `strName` → `name`
- If you need a comment to explain a function name, rename the function

### Variables

- Single-letter names only for loop counters and math (matching domain notation)
- Replace magic numbers/strings with named constants:
  - `86400` → `SECONDS_PER_DAY`
  - `"admin"` → `ADMIN_ROLE`
  - `0.08` → `SALES_TAX_RATE`
- If a comment is needed to explain a variable name, the name is wrong

### Classes

- Noun, not verb. Describes what it IS, not what it does.
- No generic names: `Manager`, `Handler`, `Processor`, `Helper`, `Utils` — be specific
  - `UserManager` → `UserRegistration` or `UserAuthenticator`
  - `DataHelper` → `CsvExporter` or `ReportFormatter`

## Function Design

- **Do One Thing**: operates at a single level of abstraction, has one reason to change
- **Small**: aim for ≤20 lines; if it needs scrolling, extract
- **No side effects in queries**: functions that return values must not mutate state
- **Command-Query Separation**: a function either answers a question OR changes state — never both
- **Maximum 3 parameters**: >3 is a smell — consider a parameter object or dataclass
- **Avoid boolean flags** as parameters; they mean the function does two things:

  ```python
  # BAD
  def render(use_html: bool): ...

  # GOOD
  def render_html(): ...
  def render_text(): ...
  ```

## Code Smells Checklist

| Smell                  | Diagnostic                                       | Fix                           |
| ---------------------- | ------------------------------------------------ | ----------------------------- |
| Long Method            | >20 lines, multiple levels of indentation        | Extract Method                |
| God Class              | > ~200 lines, does everything                    | Split by responsibility (SRP) |
| Feature Envy           | Method uses more of _another_ class than its own | Move Method                   |
| Data Clumps            | Same 3 variables always travel together          | Create a Value Object         |
| Primitive Obsession    | String for email, int for money                  | Wrap in domain type           |
| Shotgun Surgery        | One change requires edits in 5+ files            | Consolidate                   |
| Duplicate Code         | "Copy-paste with minor edits"                    | Extract shared abstraction    |
| Dead Code              | Never-reached branches, unused variables         | Delete without mercy          |
| Inappropriate Intimacy | Class directly accesses another's internals      | Expose via interface          |
| Long Parameter List    | >3 parameters                                    | Introduce Parameter Object    |

## Error Handling

- Errors are first-class citizens — handle them at the right level, not everywhere
- Use exceptions for exceptional conditions, not for control flow
- Do not return `None` as an error signal — raise or use `Result` type
- Provide context in messages: what was attempted, what failed, what was expected
- Do not swallow exceptions with bare `except:` or `except Exception: pass`

## Comments

| Comment type                                                   | Appropriate?                                   |
| -------------------------------------------------------------- | ---------------------------------------------- |
| Explains WHAT the code does                                    | ❌ — rename or refactor instead                |
| Explains WHY (business rule, regulation, non-obvious decision) | ✅                                             |
| TODO with owner and context                                    | ✅ — `# TODO(name): remove after v2 migration` |
| Commented-out code                                             | ❌ — delete it; version control exists         |
| Javadoc/docstring re-stating the signature                     | ❌ — add only if non-obvious behavior          |

## Review Checklist

- [ ] Every function name is still accurate after reading its body
- [ ] No function does more than one thing at the same level of abstraction
- [ ] No magic literals — every constant has a name
- [ ] No dead code or commented-out code
- [ ] Error handling is present and does not swallow exceptions silently
- [ ] No duplication — not even "similar" logic
- [ ] Boolean flag parameters are split into separate functions
- [ ] Side effects are absent from query functions
