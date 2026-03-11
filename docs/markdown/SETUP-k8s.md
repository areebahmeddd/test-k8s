# Setup Guide for Kubernetes

## Prerequisites

- [kubectl](https://kubernetes.io/docs/tasks/tools/) — Kubernetes CLI
- [kind](https://kind.sigs.k8s.io/) — local cluster via Docker
- [kustomize](https://kubectl.docs.kubernetes.io/installation/kustomize/) — manifest templating
- [SOPS](https://github.com/getsops/sops) + [age](https://github.com/FiloSottile/age) — secret encryption
- Docker — to build the API image and run kind nodes

## Cluster Layout

Two namespaces, no cross-namespace network policies:

| Namespace    | What lives there                                                                        |
| ------------ | --------------------------------------------------------------------------------------- |
| `todo-app`   | `todo-api` Deployment + HPA, `todo-db` StatefulSet, Services, ConfigMap, ServiceAccount |
| `monitoring` | Prometheus, Alertmanager, Grafana, Loki, Promtail, Tempo, OTel Collector                |

Two Kustomize overlays share the same base:

```
k8s/
  base/
    app/          namespace + all todo-app resources
    monitoring/   namespace + all monitoring resources
  overlays/
    dev/          NodePort patches, plaintext secrets
    prod/         imagePullPolicy patch, HPA, SOPS-encrypted secrets
```

## Overlay Differences

|                            | `dev`                            | `prod`                  |
| -------------------------- | -------------------------------- | ----------------------- |
| Service access             | NodePort (30800 / 30300 / 30090) | ClusterIP only          |
| `todo-api` replicas        | 1 (static)                       | 2–4 via HPA             |
| `todo-api` imagePullPolicy | `IfNotPresent`                   | `Always`                |
| Secrets                    | Plaintext YAML                   | SOPS-encrypted with age |

## Quick Start

### 1. Create the local cluster

```bash
make kind-create
```

### 2. Build and load the API image

```bash
docker build -t todo-api:latest .
make k8s-build          # kind load docker-image todo-api:latest --name todo-k8s
```

### 3. Deploy

```bash
make k8s-deploy         # deploys the dev overlay by default
make k8s-deploy OVERLAY=prod
```

### 4. Verify

```bash
make k8s-status
# kubectl get all -n todo-app
# kubectl get all -n monitoring
```

### 5. Access services (dev)

NodePort is preconfigured — services are reachable directly:

| Service    | URL                    |
| ---------- | ---------------------- |
| todo-api   | http://localhost:30800 |
| Grafana    | http://localhost:30300 |
| Prometheus | http://localhost:30090 |

Or use port-forward (works in both dev and prod):

```bash
make k8s-pf
# todo-api  → localhost:8000
# Grafana   → localhost:3000
# Prometheus → localhost:9090
```

### 6. Tear down

```bash
make k8s-delete         # remove deployed resources
make kind-delete        # destroy the cluster
```

## Secrets

### Dev

Secrets are plaintext YAML files committed to the repository for local convenience:

```
k8s/overlays/dev/secrets/
  todo-api-secret.yaml      DATABASE_URL, SECRET_KEY
  todo-db-secret.yaml       POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
  grafana-secret.yaml       ADMIN_USER, ADMIN_PASSWORD
  alertmanager-secret.yaml  SLACK_WEBHOOK_URL
```

### Prod

All prod secrets are SOPS-encrypted with age. The public key is committed in `.sops.yaml`. The private key must never be committed.

```bash
# Encrypt a secret in-place
sops --encrypt --in-place k8s/overlays/prod/secrets/<file>.yaml

# Edit an already-encrypted secret
sops k8s/overlays/prod/secrets/<file>.yaml
```

To deploy prod, make the private key available:

```bash
export SOPS_AGE_KEY_FILE=age.key
make k8s-deploy OVERLAY=prod
```

SOPS decrypts secrets at deploy time. No plaintext ever reaches the cluster manifest pipeline.

## Autoscaling (prod only)

`todo-api` has an HPA configured in `k8s/overlays/prod/hpa-todo-api.yaml`:

- `minReplicas: 2` — always at least two pods for availability
- `maxReplicas: 4` — ceiling to keep costs bounded
- CPU target: `70%` of the `100m` request — scales up when average CPU exceeds 70m per pod

The Deployment `spec.replicas` field is intentionally absent from the prod overlay — HPA owns replica count entirely. Setting both would cause a conflict on every deployment.

## Validation

```bash
make validate           # runs all four checks below in sequence

make validate-k8s       # kubectl dry-run against rendered dev manifests
make validate-sops      # verifies all prod secrets are SOPS-encrypted
make validate-schema    # kubeconform schema validation
make validate-policies  # OPA/conftest policy checks (resource limits, labels, image tags, probes)
```

Conftest policies live in `policy/` and enforce:

| Policy            | Rule                                                            |
| ----------------- | --------------------------------------------------------------- |
| `resource-limits` | Every container must declare CPU and memory limits              |
| `required-labels` | Every workload must carry the four `app.kubernetes.io/*` labels |
| `image-tags`      | Registry images (containing `/`) must not use `:latest`         |
| `health-probes`   | Every Deployment must define readiness and liveness probes      |

## Database Migrations

Migrations run via Alembic inside the `todo-api` pod:

```bash
kubectl exec -n todo-app deploy/todo-api -- uv run alembic upgrade head
```

## Logs

```bash
make k8s-logs           # tail todo-api logs (last 50 lines, follow)

# Individual services
kubectl logs -n monitoring deploy/grafana --tail=50
kubectl logs -n monitoring deploy/prometheus --tail=50
```

## Monitoring

See [MONITORING.md](MONITORING.md) for the full observability stack documentation — signal flow, configuration, alert rules, and Grafana dashboards.

The Kubernetes stack uses the same services and configuration as Docker Compose. The only difference is that configuration files are stored in ConfigMaps (under `k8s/base/monitoring/`) instead of bind-mounted from `monitoring/`.
