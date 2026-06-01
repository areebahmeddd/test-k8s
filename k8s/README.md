# Kubernetes Manifests

Kustomize base/overlay layout, managed in production via [ArgoCD](https://argo-cd.readthedocs.io).

## Directory Layout

```
k8s/
├── argocd/                  # ArgoCD installation + Application CRs
│   ├── applications/        # One Application CR per environment (dev, prod)
│   ├── argocd-server-ingress.yaml
│   ├── kustomization.yaml
│   ├── network-policy.yaml
│   ├── namespace.yaml
│   └── sops-age-secret.yaml # AGE private key for SOPS decryption (gitignored plaintext)
│
├── base/                    # Environment-agnostic resource definitions
│   ├── app/                 # Todo API: Deployment, Service, Ingress, ConfigMap, RBAC
│   ├── monitoring/          # Grafana Alloy, Loki, Tempo, Prometheus, Grafana, Alertmanager
│   ├── postgres/            # CloudNativePG Cluster + PgBouncer Pooler
│   └── traefik/             # Traefik IngressClass, Helm release, dashboard ingress
│
└── overlays/                # Environment-specific patches on top of base
    ├── dev/                 # dev branch → no HPA, no host patches, SQLite-sized PG
    │   ├── kustomization.yaml
    │   ├── postgres-patch.yaml
    │   └── secrets/         # SOPS-encrypted Kubernetes Secrets (never commit plaintext)
    └── prod/                # prod branch → HPA, named hosts (*.1mindlabs.org), pooler
        ├── kustomization.yaml
        ├── hpa-todo-api.yaml
        ├── pooler-patch.yaml
        ├── postgres-patch.yaml
        └── secrets/         # SOPS-encrypted Kubernetes Secrets
```

## How Kustomize Layering Works

```
base/app  +  base/postgres  +  base/monitoring  +  base/traefik
                              │
                    overlays/dev  or  overlays/prod
                    (patches, additional resources, host names)
```

`base/` holds canonical resource definitions with no environment-specific values.  
`overlays/<env>/` patches only what differs (replica counts, ingress hosts, DB sizing).  
Secrets are **never** in base or overlays as plaintext; they are SOPS-encrypted and applied out-of-band:

```bash
sops -d k8s/overlays/dev/secrets/todo-api-secret.yaml | kubectl apply -f -
```

## ArgoCD GitOps Flow

```
GitHub (dev branch)  →  ArgoCD Application: todo-app-dev  →  k8s/overlays/dev
GitHub (prod branch) →  ArgoCD Application: todo-app-prod →  k8s/overlays/prod
```

Both applications use `automated` sync with `prune: true` and `selfHeal: true`.  
ArgoCD itself is bootstrapped via `k8s/argocd/kustomization.yaml` (one-time manual apply).

## Quick Commands

> All `make` targets wrap the commands below. See the root `Makefile` for the full list.

```bash
# Preview rendered manifests (dev)
kubectl kustomize k8s/overlays/dev

# Deploy to dev cluster
kubectl apply -k k8s/overlays/dev

# Deploy ArgoCD bootstrap (once per cluster)
kubectl apply -k k8s/argocd

# Check sync status
kubectl get applications -n argocd
```

## Components

| Base component    | Provides                                                                     |
| ----------------- | ---------------------------------------------------------------------------- |
| `base/app`        | Deployment, Service, Ingress, ConfigMap, ServiceAccount                      |
| `base/postgres`   | CloudNativePG `Cluster` CR (primary database)                                |
| `base/monitoring` | OTEL traces (Tempo), logs (Loki), metrics (Prometheus), dashboards (Grafana) |
| `base/traefik`    | Ingress controller routing external traffic to `todo-api` Service            |

## Further Reading

| Topic                          | Document                                                      |
| ------------------------------ | ------------------------------------------------------------- |
| Full cluster setup walkthrough | [docs/markdown/SETUP-k8s.md](../docs/markdown/SETUP-k8s.md)   |
| Ingress, DNS, and TLS          | [docs/markdown/NETWORKING.md](../docs/markdown/NETWORKING.md) |
| Observability stack            | [docs/markdown/MONITORING.md](../docs/markdown/MONITORING.md) |
| k9s cluster navigation         | [docs/markdown/K9S.md](../docs/markdown/K9S.md)               |
| Infra provisioning (Pulumi)    | [infra/README.md](../infra/README.md)                         |
