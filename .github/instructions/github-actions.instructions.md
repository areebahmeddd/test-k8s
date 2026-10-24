---
name: GitHub Actions
description: Conventions for CI workflows.
applyTo: ".github/workflows/**"
---

# GitHub Actions

- Pin third-party actions to a full commit SHA, with the version in a trailing comment.
- Set `permissions: contents: read` for the workflow, and widen it per job only when a job needs more.
- Give every job a `name` and a `timeout-minutes`, and every step a short `name`. Workflows share
  `concurrency: ${{ github.workflow }}-${{ github.ref }}`.
- Pin tool versions in one place (`with: version:` or the workflow `env:`), and call `make` targets so CI and
  local runs execute the same commands.
- `ci.yaml` lints and tests the API (Ruff, `alembic check`, pytest) and builds the image. `validate.yaml`
  checks the manifests with the `make validate-*` targets.
- Pass secrets through `env:` on the step that needs them, and never echo them.
