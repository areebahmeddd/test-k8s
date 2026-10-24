# Kubernetes manifests

Kustomize bases with `dev` and `prod` overlays, deployed by ArgoCD for GitOps or by Tilt for local
development. Setup, access and networking are covered in [docs/KUBERNETES.md](../docs/KUBERNETES.md).

```text
k8s/
├── argocd/                 ArgoCD bootstrap
│   ├── base/               ArgoCD install (v3.5.6), server ingress, NetworkPolicies
│   │   └── applications/   The cloudnativepg (Helm chart) and todo-app Applications
│   ├── dev/                todo-app tracks branch dev and k8s/overlays/dev; host argocd.localhost
│   └── prod/               todo-app tracks branch prod and k8s/overlays/prod; host argocd.1mindlabs.org
├── base/                   Resources shared by both environments
│   ├── app/                todo-api Deployment with its migrate init container, Service, Ingress,
│   │                       ConfigMap, ServiceAccount and the namespace's NetworkPolicies
│   ├── postgres/           CloudNativePG Cluster and PgBouncer Pooler
│   ├── traefik/            Traefik Deployment, Service, IngressClass, RBAC and dashboard Ingress
│   └── monitoring/         alloy, loki, tempo, prometheus, alertmanager, grafana and NetworkPolicies
└── overlays/
    ├── dev/                *.localhost ingress hosts, plus secrets/
    └── prod/               *.1mindlabs.org hosts, HPA, more database and pooler instances, plus secrets/
```

## Overlay differences

|                      | dev                                  | prod                                 |
| -------------------- | ------------------------------------ | ------------------------------------ |
| Ingress hosts        | `*.localhost`                        | `*.1mindlabs.org`                    |
| `todo-api` replicas  | 1                                    | 2 to 4, set by the HPA               |
| PostgreSQL instances | 1, with 5Gi data, 1Gi WAL and no PDB | 3, with 50Gi data, 5Gi WAL and a PDB |
| PgBouncer instances  | 1                                    | 2                                    |

Each overlay's `secrets/` folder holds SOPS-encrypted Secrets. They are deliberately left out of
`kustomization.yaml`; `make k8s-secrets` decrypts and applies them.

## Commands

```bash
kubectl kustomize k8s/overlays/dev      # render an overlay
make validate                           # build, schema check, SOPS check and policies
make k8s-deploy OVERLAY=dev             # ArgoCD bootstrap plus secrets
```
