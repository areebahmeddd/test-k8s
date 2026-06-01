# GitHub Actions Best Practices

## Pin Actions to Commit SHA

```yaml
# Wrong — mutable tag, vulnerable to supply chain attacks
- uses: actions/checkout@v4

# Correct — immutable SHA with version comment
- uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
```

## Principle of Least Privilege

```yaml
permissions: {} # deny all at workflow level

jobs:
  build:
    permissions:
      contents: read # only what this job needs

  publish:
    permissions:
      contents: read
      packages: write
```

## Cancel Stale Runs

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

## uv Setup

```yaml
- name: Install uv
  uses: astral-sh/setup-uv@<sha> # v7
  with:
    version: ${{ env.UV_VERSION }}
    enable-cache: true # keyed on uv.lock automatically
```

## Rules

- Secrets via `${{ secrets.NAME }}` only — never hardcode or echo to logs
- Use `environment:` for deploy jobs requiring manual approval gates
- Cache dependencies using `enable-cache: true` on `setup-uv` — do not roll your own cache key
- Run `uv run ruff check` and `uv run pytest` as separate named steps (not combined in one)
