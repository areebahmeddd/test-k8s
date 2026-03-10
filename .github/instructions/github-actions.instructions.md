---
name: GitHub Actions Best Practices
description: "Use when writing or reviewing GitHub Actions workflow YAML files. Covers security hardening, permission scoping, concurrency groups, dependency caching, secret handling, and CI/CD pipeline structure."
applyTo: ".github/workflows/**"
---

# GitHub Actions Best Practices

## Security: Pin Actions to Commit SHA

```yaml
# BAD — mutable tag, vulnerable to tag hijacking
- uses: actions/checkout@v4

# GOOD — immutable SHA with version comment
- uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
```

Pin ALL third-party actions (`actions/*`, `astral-sh/*`, etc.) to a full commit SHA with the version in a comment. This prevents supply chain attacks via mutable tags.

## Permissions: Principle of Least Privilege

```yaml
# Workflow-level default: deny all
permissions: {}

jobs:
  build:
    permissions:
      contents: read # Only what this specific job needs

  publish:
    permissions:
      contents: read
      packages: write # Only on the job that publishes
```

- Set `permissions: {}` at the workflow level to deny all by default
- Grant the minimum needed permissions at the job level
- Never use `write-all` — prefer explicit per-permission grants

## Concurrency: Cancel Stale Runs

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

Prevents multiple simultaneous runs for the same branch/PR. Essential for fast-moving branches.

## Dependency Caching (uv)

```yaml
- name: Cache uv packages
  uses: actions/cache@<sha> # v4
  with:
    path: ~/.cache/uv
    key: ${{ runner.os }}-uv-${{ hashFiles('uv.lock') }}
    restore-keys: |
      ${{ runner.os }}-uv-
```

The `uv.lock` hash ensures the cache is invalidated when dependencies change.

## Secrets

- Never `echo ${{ secrets.MY_SECRET }}` — it will be masked but sets a bad pattern
- Pass secrets via `env:` on a step, not inline in `run:` commands:
  ```yaml
  - name: Deploy
    env:
      API_KEY: ${{ secrets.API_KEY }}
    run: ./deploy.sh # uses $API_KEY from env, not from YAML
  ```
- Store secrets in repository secrets (Settings → Secrets and variables → Actions)
- Use environment-scoped secrets for production deployments with approval gates

## Job Design

- **One concern per job**: lint, test, build, deploy as separate jobs
- **`needs:`** to express explicit dependencies: `needs: [lint, test]`
- **`timeout-minutes:`** on every job — prevents runaway billing from hanging tests
- **`if:` conditions** for environment-gated steps:
  ```yaml
  if: github.ref == 'refs/heads/prod' && github.event_name == 'push'
  ```
- **Matrix strategy** for multi-version testing:
  ```yaml
  strategy:
    matrix:
      python-version: ["3.11", "3.12"]
  ```

## Environment Variables

```yaml
env:
  PYTHON_VERSION: "3.11" # Define once at workflow level, reference everywhere
  UV_VERSION: "0.10.5"
```

Pin tool versions as workflow-level env vars — single place to update.

## Workflow Naming Convention

| Filename        | Purpose                                   | Trigger                        |
| --------------- | ----------------------------------------- | ------------------------------ |
| `ci.yaml`       | Tests, linting, coverage                  | Push to any branch, PRs        |
| `validate.yaml` | Infrastructure validation (OPA, k8s lint) | Push affecting k8s/ or policy/ |
| `deploy.yaml`   | Build image, push, deploy                 | Merge to `prod` branch         |
| `release.yaml`  | Semantic release, changelog               | Tag push                       |
