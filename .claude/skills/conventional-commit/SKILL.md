---
name: conventional-commit
description: "Use when writing a git commit message, staging changes, preparing a PR description, or generating a changelog entry. Enforces Conventional Commits 1.0.0 spec for structured, machine-readable commit history. Triggers on: write commit message, git commit, commit these changes, what should the commit message be, stage and commit, describe these changes, PR description, changelog."
argument-hint: "Describe what changed, or paste the diff summary"
---

# Conventional Commit

Generates commit messages following [Conventional Commits 1.0.0](https://www.conventionalcommits.org).

Structured commits enable: automated changelogs, semantic versioning, searchable history, and clear PR intent.

## Format

```
<type>(<scope>): <subject>

[optional body]

[optional footer(s)]
```

## Types

| Type       | When to Use                                           |
| ---------- | ----------------------------------------------------- |
| `feat`     | New feature visible to users or API callers           |
| `fix`      | Bug fix visible to users or API callers               |
| `perf`     | Measurable performance improvement                    |
| `refactor` | Code restructuring with no behavior change            |
| `test`     | Adding or improving tests (no production code change) |
| `docs`     | Documentation changes only                            |
| `ci`       | CI/CD pipeline or workflow changes                    |
| `build`    | Build system, dependency, or tool changes             |
| `chore`    | Housekeeping tasks (no production code change)        |
| `style`    | Formatting, whitespace, semicolons (no logic change)  |
| `revert`   | Reverts a previous commit                             |

## Scope (Optional)

The component/module affected. Use consistently:

| Scope        | Covers                                         |
| ------------ | ---------------------------------------------- |
| `api`        | Route handlers, API endpoints                  |
| `auth`       | Authentication, JWT, tokens                    |
| `db`         | Database models, migrations, queries           |
| `k8s`        | Kubernetes manifests, Kustomize overlays       |
| `monitoring` | Prometheus, Grafana, Loki, Tempo, OTel configs |
| `deps`       | Dependency additions or upgrades               |
| `config`     | Application configuration                      |
| `tests`      | Test infrastructure, fixtures, conftest        |
| `ci`         | GitHub Actions workflows                       |
| `docs`       | Documentation files                            |

## Subject Line Rules

- **Imperative mood, present tense**: "add" not "added" / "adds"
- **No capital letter** at the start
- **No period** at the end
- **≤72 characters** total including type and scope
- Describes the **WHAT**, not the HOW
- If you need "and" in the subject, split into two commits

## Body (When to Include)

Only include a body when the WHY isn't obvious from the subject:

- Non-obvious design decisions
- Links to issues or external resources
- Migration notes required for reviewers

Wrap at 72 characters. Blank line between subject and body.

## Breaking Changes

Append `!` after type/scope for breaking changes:

```
feat(auth)!: require refresh token rotation on every use
```

And add footer:

```
BREAKING CHANGE: clients that reuse refresh tokens will receive 401.
Clients must update to store and send the new token returned with each refresh.
```

## Examples

```
feat(auth): add refresh token rotation

On each successful token refresh, the old refresh token is invalidated
and a new one is issued. This limits the window of exposure if a token
is compromised.

Closes #42
```

```
fix(api): return 404 when todo not found instead of 500
```

```
refactor(db): extract repository layer from route handlers

Moves all SQLAlchemy session logic out of api/v1/todos.py into
a dedicated TodoRepository class. No behavior change.
```

```
ci: pin all GitHub Actions to commit SHAs

Prevents supply chain attacks via mutable action tags.
```

```
feat(k8s)!: require resource limits on all containers

BREAKING CHANGE: deployments without cpu/memory limits will now fail
OPA policy validation. Add limits to all containers before upgrading
to the new overlays.
```

## Procedure

1. `git diff --staged` — review exactly what's staged
2. Identify the **primary type** of change (one commit = one type)
3. Identify the **scope** (which subsystem)
4. Write the subject: imperative, ≤72 chars total, no period
5. Add body ONLY if the WHY isn't obvious from the diff
6. Add `BREAKING CHANGE:` footer if any public API or contract changed
7. Verify: would `semantic-release` parse this correctly?

## Atomic Commit Principle

Each commit should:

- Pass CI on its own (not break the build mid-way)
- Be independently reversible with `git revert`
- Represent ONE logical change

If your commit message needs "and" — split it into two commits.
