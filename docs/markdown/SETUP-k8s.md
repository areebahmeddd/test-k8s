# Setup Guide for Kubernetes

## Prerequisites

- [kubectl](https://kubernetes.io/docs/tasks/tools/) — Kubernetes CLI
- [minikube](https://minikube.sigs.k8s.io/docs/start/) — local single-node cluster
- [kustomize](https://kubectl.docs.kubernetes.io/installation/kustomize/) — manifest templating
- [SOPS](https://github.com/getsops/sops) + [age](https://github.com/FiloSottile/age) — secret encryption
- Docker — to build the API image

## Cluster Layout

Four namespaces:

| Namespace    | What lives there                                                                        |
| ------------ | --------------------------------------------------------------------------------------- |
| `argocd`     | ArgoCD server, application controller, repo server, dex, redis                          |
| `traefik`    | Traefik ingress controller (LoadBalancer service)                                       |
| `todo-app`   | `todo-api` Deployment + HPA, `todo-db` StatefulSet, Services, ConfigMap, ServiceAccount |
| `monitoring` | Prometheus, Alertmanager, Grafana, Loki, Alloy, Tempo                                   |

Two Kustomize overlays share the same base:

```text
k8s/
  base/
    app/          namespace + all todo-app resources
    monitoring/   namespace + all monitoring resources
    traefik/      namespace + traefik deployment and service
  overlays/
    dev/          replica/resource patches, SOPS-encrypted secrets
    prod/         imagePullPolicy Always, HPA, SOPS-encrypted secrets
```

## Overlay Differences

|                            | `dev`          | `prod`         |
| -------------------------- | -------------- | -------------- |
| `todo-api` replicas        | 1 (static)     | 2–4 via HPA    |
| `todo-api` imagePullPolicy | `IfNotPresent` | `Always`       |
| Secrets                    | SOPS-encrypted | SOPS-encrypted |

## Quick Start

### 1. Create the local cluster

```bash
make minikube-create
```

### 2. Build the API image

```bash
make k8s-build
```

### 3. Load all images into minikube

minikube runs its own internal Docker daemon — images on your host are not visible inside the cluster without loading them explicitly.

```bash
make minikube-load
```

### 4. Set the AGE private key

SOPS uses your AGE private key to decrypt secrets at deploy time. The key lives on your machine (never in the cluster) and is only needed when running `sops -d` locally.

```powershell
$env:SOPS_AGE_KEY_FILE = "$(Get-Location)\age.key"   # PowerShell
```

```bash
export SOPS_AGE_KEY_FILE="$(pwd)/age.key"             # bash / zsh
```

### 5. Deploy

```bash
make k8s-deploy              # ArgoCD + dev overlay + secrets
make k8s-deploy OVERLAY=prod
```

What `k8s-deploy` does in order:

1. Applies ArgoCD twice with `--server-side` — first pass registers CRDs, second pass applies the `Application` resources that depend on those CRDs.
2. Renders the overlay with `kustomize build` and pipes it to `kubectl apply`.
3. Decrypts each secret file with `sops -d` and applies it directly — plaintext never touches disk.

### 6. Enable `*.localhost` routing

> **Dev overlay only** — this step is specific to minikube. A prod cluster with a real domain and DNS does not need it.

#### 6a. Add hosts file entries

Each `*.localhost` hostname must resolve to `127.0.0.1` on your machine. Add the following block to your hosts file if it is not already there:

```text
127.0.0.1  todo.localhost
127.0.0.1  argocd.localhost
127.0.0.1  grafana.localhost
127.0.0.1  prometheus.localhost
127.0.0.1  alloy.localhost
127.0.0.1  traefik.localhost
```

| OS      | Hosts file path                         |
| ------- | --------------------------------------- |
| Windows | `C:\Windows\System32\drivers\etc\hosts` |
| macOS   | `/etc/hosts`                            |
| Linux   | `/etc/hosts`                            |

On Windows, open your editor as **Administrator** before editing the file.

#### 6b. Start minikube tunnel

Traefik is a `LoadBalancer` service. In minikube, `LoadBalancer` services have `EXTERNAL-IP: <pending>` by default. `minikube tunnel` assigns `127.0.0.1` as the external IP so all `*.localhost` hostnames route through Traefik on port 80.

Run this **once in a dedicated elevated window and leave it open**:

```powershell
# PowerShell — accepts a UAC prompt
Start-Process powershell -ArgumentList "-NoExit", "-Command", "minikube tunnel" -Verb RunAs
```

```bash
# bash
sudo minikube tunnel
```

Confirm it worked:

```bash
kubectl get svc -n traefik
# EXTERNAL-IP should show 127.0.0.1, not <pending>
```

### 7. Verify

```bash
make k8s-status
```

| Service    | URL                                   | Credentials      |
| ---------- | ------------------------------------- | ---------------- |
| todo-api   | `http://todo.localhost`               | —                |
| ArgoCD     | `http://argocd.localhost`             | admin / admin123 |
| Grafana    | `http://grafana.localhost`            | admin / admin123 |
| Prometheus | `http://prometheus.localhost`         | —                |
| Alloy      | `http://alloy.localhost`              | —                |
| Traefik    | `http://traefik.localhost/dashboard/` | —                |

### 8. Tear down

```bash
make k8s-delete          # remove all deployed resources
make minikube-delete     # destroy the cluster
```

## Secrets

All secrets in both overlays are SOPS-encrypted with age. The AGE public key is committed in `.sops.yaml`. The private key (`age.key`) must never be committed.

```text
k8s/overlays/dev/secrets/           k8s/overlays/prod/secrets/
  todo-api-secret.yaml                todo-api-secret.yaml
  todo-db-secret.yaml                 todo-db-secret.yaml
  grafana-secret.yaml                 grafana-secret.yaml
  alertmanager-secret.yaml            alertmanager-secret.yaml
```

Each file holds `stringData` fields encrypted with `ENC[AES256_GCM,...]`. Running `sops -d <file>` decrypts it in memory — nothing is written to disk.

```bash
# Update a single field in an encrypted file (no full decrypt needed)
sops --set '["stringData"]["ADMIN_PASSWORD"] "newvalue"' k8s/overlays/dev/secrets/grafana-secret.yaml

# Open an encrypted file in your editor
sops k8s/overlays/dev/secrets/grafana-secret.yaml
```

## ArgoCD

ArgoCD is configured to run in HTTP mode (`server.insecure: "true"` in `argocd-cmd-params-cm`) so the plain-HTTP Traefik Ingress can route to it without TLS passthrough. In production with a real domain you would remove that patch and terminate TLS at Traefik with cert-manager instead.

The initial admin password is auto-generated on first install and stored in a cluster Secret:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d
```

Change it after first login:

```bash
argocd login argocd.localhost:80 --username admin --insecure
argocd account update-password
```

Then delete the auto-generated secret — it is no longer needed and should not remain in the cluster:

```bash
kubectl -n argocd delete secret argocd-initial-admin-secret
```

## Autoscaling (prod only)

`todo-api` has an HPA configured in `k8s/overlays/prod/hpa-todo-api.yaml`:

- `minReplicas: 2` — always at least two pods for availability
- `maxReplicas: 4` — ceiling to keep costs bounded
- CPU target: `70%` of the `100m` request — scales up when average CPU exceeds 70m per pod

The Deployment `spec.replicas` field is intentionally absent from the prod overlay — HPA owns replica count entirely. Setting both would cause a conflict on every deployment.

## Validation

```bash
make validate           # runs all four checks below in sequence

make validate-k8s       # kustomize build dry-run against dev overlay
make validate-sops      # verifies all secrets are SOPS-encrypted
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

Configuration files are stored in ConfigMaps under `k8s/base/monitoring/` and loaded into pods as volume mounts, equivalent to the bind mounts used in the Docker Compose setup.

## Resource Usage

All resource requests and limits are declared in `k8s/base/`. The dev overlay does not override them — these figures apply to both overlays.

**Totals across all pods (single replica each):**

- CPU requests: `800m` · CPU limits: `3000m`
- Memory requests: `2432Mi (~2.4 GiB)` · Memory limits: `4972Mi (~4.9 GiB)`

### Per-container breakdown

| Component      | Namespace    | CPU Request | Mem Request | CPU Limit | Mem Limit |
| -------------- | ------------ | ----------- | ----------- | --------- | --------- |
| `todo-api`     | `todo-app`   | 100m        | 256Mi       | 500m      | 512Mi     |
| `todo-db`      | `todo-app`   | 250m        | 512Mi       | 500m      | 1Gi       |
| `pgbouncer`    | `todo-app`   | 50m         | 64Mi        | 200m      | 256Mi     |
| `traefik`      | `traefik`    | 100m        | 128Mi       | 500m      | 256Mi     |
| `prometheus`   | `monitoring` | 100m        | 512Mi       | 500m      | 1Gi       |
| `grafana`      | `monitoring` | 50m         | 256Mi       | 200m      | 512Mi     |
| `loki`         | `monitoring` | 50m         | 256Mi       | 200m      | 512Mi     |
| `tempo`        | `monitoring` | 50m         | 256Mi       | 200m      | 512Mi     |
| `alloy`        | `monitoring` | 25m         | 128Mi       | 100m      | 256Mi     |
| `alertmanager` | `monitoring` | 25m         | 64Mi        | 100m      | 128Mi     |

> ArgoCD system pods (`argocd-server`, `application-controller`, `repo-server`, `dex`, `redis`) do not declare resource limits in this project — they use ArgoCD's upstream defaults.

### Recommended host resources

| Local cluster | Min RAM | Min CPU | Notes                                            |
| ------------- | ------- | ------- | ------------------------------------------------ |
| minikube      | 8 GiB   | 4 cores | Matches `make minikube-create` flags             |
| kind          | 6 GiB   | 2 cores | No separate VM overhead — Docker containers only |
