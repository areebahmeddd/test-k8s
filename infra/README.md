# infra

Pulumi program that bootstraps the todo-k8s cluster before ArgoCD takes over.

## Responsibility split

| Layer                                   | Tool            | Source of truth                           |
| --------------------------------------- | --------------- | ----------------------------------------- |
| CNPG operator (Helm Release)            | Pulumi          | `infra/src/cnpg.py`                       |
| ArgoCD install + patches                | Pulumi          | `k8s/argocd/` (rendered at plan time)     |
| Application namespaces + Secrets        | Pulumi          | `infra/src/secrets.py`                    |
| todo-api, postgres, traefik, monitoring | ArgoCD (GitOps) | `k8s/overlays/dev` or `k8s/overlays/prod` |

CNPG is installed as a direct Helm Release rather than an ArgoCD Application so
that CNPG CRDs are registered synchronously before ArgoCD syncs the cluster
overlay, which contains `Cluster` and `Pooler` CRs.

## Prerequisites

- Python >= 3.11
- [Pulumi CLI](https://pulumi.com/docs/install/) >= 3.240.0
- `kubectl` configured to target the cluster
- `kustomize` on PATH (invoked by `src/argocd.py` at plan time)

## Setup

### 1. Install dependencies

```bash
make pulumi-init
```

Creates `infra/venv` and installs `requirements.txt`.

### 2. Initialise a stack

```bash
cd infra
pulumi stack init dev   # or: prod
```

### 3. Set required secrets

All secret values are stored encrypted in Pulumi state and are never written to disk or committed to the repository.

```bash
cd infra

pulumi config set --secret todo-k8s-infra:db_username admin
pulumi config set --secret todo-k8s-infra:db_password <value>
pulumi config set --secret todo-k8s-infra:api_database_url \
  "postgresql+asyncpg://admin:<pw>@todo-db-rw.todo-app.svc.cluster.local:5432/todos"
pulumi config set --secret todo-k8s-infra:api_secret_key <hex-32-bytes>
pulumi config set --secret todo-k8s-infra:grafana_admin_user admin
pulumi config set --secret todo-k8s-infra:grafana_admin_password <value>
pulumi config set --secret todo-k8s-infra:slack_webhook_url https://hooks.slack.com/...
```

Generate values where needed:

```bash
# db_password / grafana_admin_password
openssl rand -hex 16

# api_secret_key
python -c "import secrets; print(secrets.token_hex(32))"
```

## Usage

```bash
# Deploy (shows diff, prompts for confirmation)
make pulumi-up OVERLAY=dev

# Preview without applying
cd infra && pulumi preview --stack dev

# Tear down all Pulumi-managed resources
make pulumi-destroy OVERLAY=dev
```

## Resource graph

CNPG and ArgoCD run in parallel. Secrets depend on ArgoCD completing so
namespaces exist before secrets are created.

```
pulumi up
  +-- cloudnative-pg    Helm Release  (atomic, waits for CRDs)
  +-- argocd            ConfigGroup   (kustomize build k8s/argocd/)
        |
        v
  +-- todo-app-ns       Namespace
  +-- monitoring-ns     Namespace
        |
        v
  +-- todo-api-secret, todo-db-secret         (todo-app namespace)
  +-- grafana-secret, alertmanager-secret     (monitoring namespace)
```

After `pulumi up` completes, ArgoCD auto-syncs the selected overlay from Git
and deploys the full application stack.

## Stack config reference

| Key                      | Type   | Description                                         |
| ------------------------ | ------ | --------------------------------------------------- |
| `overlay`                | string | Kustomize overlay: `dev` or `prod`. Default: `dev`  |
| `db_username`            | secret | PostgreSQL admin username (CloudNativePG bootstrap) |
| `db_password`            | secret | PostgreSQL admin password                           |
| `api_database_url`       | secret | Full asyncpg connection URL for todo-api            |
| `api_secret_key`         | secret | 32-byte hex JWT signing key                         |
| `grafana_admin_user`     | secret | Grafana admin username                              |
| `grafana_admin_password` | secret | Grafana admin password                              |
| `slack_webhook_url`      | secret | Alertmanager Slack incoming webhook URL             |
