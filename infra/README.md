# infra

A Pulumi program that bootstraps a cluster for GitOps. It is an alternative to `make k8s-deploy` that takes
the Kubernetes Secrets from encrypted Pulumi config instead of the SOPS files.

| What it manages                                        | Source                                                       |
| ------------------------------------------------------ | ------------------------------------------------------------ |
| ArgoCD, its ingress and policies, and the Applications | `k8s/argocd/<overlay>`, rendered by `kustomize.v2.Directory` |
| The `todo-app` and `monitoring` namespaces and Secrets | `src/cluster_secrets.py`                                     |
| Everything else (CNPG, the app, monitoring)            | ArgoCD, syncing `k8s/overlays/<overlay>`                     |

The namespaces and Secrets are created first, so ArgoCD's first sync finds them in place. ArgoCD is then
applied without waiting for its resources to become ready, because ArgoCD reconciles them itself and its
Ingress only gets an address once Traefik is running. The stack name selects the overlay through
`Pulumi.dev.yaml` and `Pulumi.prod.yaml`.

## Setup

You need the Pulumi CLI and `kubectl` access to the target cluster. Dependencies are managed with uv, through
`runtime.options.toolchain: uv` in `Pulumi.yaml`.

```bash
make pulumi-install          # runs `pulumi install`, which creates infra/.venv from uv.lock
cd infra
pulumi stack init dev        # or prod

# db_username must match the owner in k8s/base/postgres/cluster.yaml.
pulumi config set --secret db_username admin
pulumi config set --secret db_password "$(openssl rand -hex 16)"
pulumi config set --secret api_secret_key "$(openssl rand -hex 32)"
pulumi config set --secret grafana_admin_user admin
pulumi config set --secret grafana_admin_password "$(openssl rand -hex 16)"
pulumi config set --secret slack_webhook_url https://hooks.slack.com/services/...
```

## Usage

```bash
pulumi preview --stack dev
make pulumi-up OVERLAY=dev
make pulumi-destroy OVERLAY=dev
```

## Config

| Key                      | Type   | Description                                                             |
| ------------------------ | ------ | ----------------------------------------------------------------------- |
| `overlay`                | string | `dev` or `prod`, set in the stack file                                  |
| `db_username`            | secret | PostgreSQL owner created by CloudNativePG; must be `admin`              |
| `db_password`            | secret | Password for that owner; the API uses both to connect through PgBouncer |
| `api_secret_key`         | secret | Key used to sign JWTs                                                   |
| `grafana_admin_user`     | secret | Grafana admin user                                                      |
| `grafana_admin_password` | secret | Grafana admin password                                                  |
| `slack_webhook_url`      | secret | Slack webhook that Alertmanager posts to                                |
