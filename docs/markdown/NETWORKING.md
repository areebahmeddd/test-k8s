# Networking & Network Policies

This document describes how inter-pod and inter-namespace traffic is controlled in the cluster.

## CNI: Calico

The default minikube CNI (`kindnet`) does **not** enforce `NetworkPolicy` objects - it accepts them but silently ignores rules.  
Calico is required and is provisioned automatically by `make minikube-create`:

```sh
minikube start --cni=calico --memory=4096 --cpus=4
```

Verify enforcement is active before applying policies:

```sh
kubectl get pods -n kube-system -l k8s-app=calico-node
# Expected: Running
```

## Model: Default-Deny-All + Per-Workload Allow

Every namespace has a baseline `NetworkPolicy` that selects all pods and provides no ingress or egress rules - effectively dropping all traffic:

```yaml
spec:
  podSelector: {} # selects all pods in namespace
  policyTypes: [Ingress, Egress]
  # no ingress: or egress: stanzas → deny all
```

Separate, narrowly-scoped policies then re-open only the paths that are required.  
All policies use `kubernetes.io/metadata.name` namespace label selectors (available since Kubernetes 1.21 - no manual namespace labelling required).

All per-workload egress policies include DNS:

```yaml
egress:
  - ports:
      - port: 53
        protocol: UDP
      - port: 53
        protocol: TCP
    to:
      - namespaceSelector:
          matchLabels:
            kubernetes.io/metadata.name: kube-system
```

## Traffic Matrix

| Source              | Destination                   | Port  | Protocol | Policy                                                                                              |
| ------------------- | ----------------------------- | ----- | -------- | --------------------------------------------------------------------------------------------------- |
| External (hostPort) | traefik                       | 80    | TCP      | `allow-traefik` (no `from:` → open to all)                                                          |
| traefik             | todo-api                      | 8000  | TCP      | `allow-todo-api` ingress                                                                            |
| traefik             | argocd-server                 | 80    | TCP      | `allow-argocd-server` ingress                                                                       |
| traefik             | grafana                       | 3000  | TCP      | `allow-grafana` ingress (prod only)                                                                 |
| traefik             | prometheus                    | 9090  | TCP      | `allow-prometheus` ingress (prod only)                                                              |
| traefik             | alloy                         | 12345 | TCP      | `allow-alloy` ingress (prod only)                                                                   |
| todo-api            | pgbouncer                     | 5432  | TCP      | `allow-pgbouncer` ingress                                                                           |
| pgbouncer           | postgres (primary)            | 5432  | TCP      | `allow-postgres` ingress                                                                            |
| postgres            | postgres (replicas)           | 5432  | TCP      | `allow-postgres` ingress (peer replication)                                                         |
| postgres            | Kubernetes API (`default` ns) | 443   | TCP      | `allow-postgres` egress - CNPG instance manager reads Secrets/ConfigMaps and updates Cluster status |
| todo-api            | alloy                         | 4317  | TCP      | `allow-alloy` ingress (OTLP gRPC traces/metrics)                                                    |
| prometheus          | todo-api                      | 8000  | TCP      | `allow-todo-api` ingress (cross-namespace scrape)                                                   |
| prometheus          | alertmanager                  | 9093  | TCP      | `allow-alertmanager` ingress                                                                        |
| alloy               | loki                          | 3100  | TCP      | `allow-loki` ingress                                                                                |
| alloy               | tempo                         | 4318  | TCP      | `allow-tempo` ingress                                                                               |
| grafana             | prometheus                    | 9090  | TCP      | `allow-prometheus` ingress                                                                          |
| grafana             | loki                          | 3100  | TCP      | `allow-loki` ingress                                                                                |
| grafana             | tempo                         | 3200  | TCP      | `allow-tempo` ingress                                                                               |
| alertmanager        | internet (Slack)              | 443   | TCP      | `allow-alertmanager` egress (`ipBlock` excl. RFC1918)                                               |
| argocd-server       | internet (GitHub / Helm)      | 443   | TCP      | `allow-argocd-server` egress (`ipBlock` excl. RFC1918)                                              |
| All pods            | CoreDNS (`kube-system`)       | 53    | UDP+TCP  | included in every per-workload egress                                                               |

## Policy Inventory

### `todo-app` namespace (`k8s/base/app/network-policy.yaml`)

| Policy             | Selects                              | Ingress from                                            | Egress to                                  |
| ------------------ | ------------------------------------ | ------------------------------------------------------- | ------------------------------------------ |
| `default-deny-all` | all pods                             | -                                                       | -                                          |
| `allow-todo-api`   | `app: todo-api`                      | traefik `:8000`, monitoring (prometheus scrape) `:8000` | DNS, pgbouncer `:5432`, alloy `:4317`      |
| `allow-pgbouncer`  | `cnpg.io/poolerName: todo-db-pooler` | todo-api `:5432`                                        | DNS, postgres `:5432`                      |
| `allow-postgres`   | `cnpg.io/cluster: todo-db`           | pgbouncer `:5432`, peer postgres `:5432`                | DNS, peer postgres `:5432`, k8s-api `:443` |

### `monitoring` namespace (`k8s/base/monitoring/network-policy.yaml`)

| Policy               | Selects                                | Ingress from                       | Egress to                                                        |
| -------------------- | -------------------------------------- | ---------------------------------- | ---------------------------------------------------------------- |
| `default-deny-all`   | all pods                               | -                                  | -                                                                |
| `allow-alloy`        | `app.kubernetes.io/name: alloy`        | todo-api `:4317`, traefik `:12345` | DNS, loki `:3100`, tempo `:4318`, k8s-api `:443` (pod discovery) |
| `allow-prometheus`   | `app.kubernetes.io/name: prometheus`   | grafana `:9090`, traefik `:9090`   | DNS, todo-app `:8000` (cross-ns scrape), alertmanager `:9093`    |
| `allow-grafana`      | `app.kubernetes.io/name: grafana`      | traefik `:3000`                    | DNS, prometheus `:9090`, loki `:3100`, tempo `:3200`             |
| `allow-loki`         | `app.kubernetes.io/name: loki`         | alloy `:3100`, grafana `:3100`     | DNS                                                              |
| `allow-tempo`        | `app.kubernetes.io/name: tempo`        | alloy `:4318`, grafana `:3200`     | DNS                                                              |
| `allow-alertmanager` | `app.kubernetes.io/name: alertmanager` | prometheus `:9093`                 | DNS, internet `:443` (Slack)                                     |

### `traefik` namespace (`k8s/base/traefik/network-policy.yaml`)

| Policy             | Selects                           | Ingress from                                                | Egress to                                                                                   |
| ------------------ | --------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `default-deny-all` | all pods                          | -                                                           | -                                                                                           |
| `allow-traefik`    | `app.kubernetes.io/name: traefik` | `:80` open (no `from:` - node-level hostPort), `:9000` open | DNS, k8s-api `:443`, todo-api `:8000`, argocd-server `:80`, grafana/prometheus/alloy (prod) |

### `argocd` namespace (`k8s/argocd/network-policy.yaml`)

| Policy                  | Selects                                 | Ingress from            | Egress to                                          |
| ----------------------- | --------------------------------------- | ----------------------- | -------------------------------------------------- |
| `default-deny-all`      | all pods                                | -                       | -                                                  |
| `allow-argocd-internal` | all pods                                | within argocd namespace | DNS, within argocd, k8s-api `:443`                 |
| `allow-argocd-server`   | `app.kubernetes.io/name: argocd-server` | traefik `:80`           | DNS, k8s-api `:443`, internet `:443` excl. RFC1918 |

> **Note:** ArgoCD's upstream `install.yaml` ships its own per-component `NetworkPolicy` objects. Our policies are additive - Kubernetes applies the union of all matching policies (most permissive wins per direction).

## Design Decisions

**`allow-argocd-internal` is namespace-wide**  
ArgoCD has many internal components (server, repo-server, application-controller, dex, redis, notification controller) that communicate on ports which shift between upstream releases. A namespace-wide intra-namespace policy avoids constant policy maintenance as ArgoCD is upgraded.

**`allow-traefik` ingress has no `from:` on port 80**  
Traffic arrives from the node's network stack via `hostPort`, not from identifiable pod sources. Omitting `from:` is correct for host-network ingress paths in minikube/KinD.

**`allow-postgres` egress targets `default:443`**  
The CNPG instance manager running inside each postgres pod needs to read Kubernetes Secrets and ConfigMaps and update the `Cluster` CRD status. The Kubernetes API server is reachable via the `kubernetes` ClusterIP service in the `default` namespace - not from `cnpg-system`.

**`allow-alertmanager` and `allow-argocd-server` use `ipBlock` for internet egress**  
These are the only components that legitimately need to reach external endpoints (Slack webhooks, GitHub API, Helm repositories). `ipBlock: 0.0.0.0/0` with RFC1918 exclusions (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) restricts this to true internet addresses only.

## Validation

Confirm all NetworkPolicy objects are present:

```sh
kubectl get networkpolicies -A
```

Expected namespaces with policies: `todo-app`, `monitoring`, `traefik`, `argocd`.

Run OPA/conftest policy checks (from project root):

```sh
uv run conftest test k8s/base/app/ --policy policy/
uv run conftest test k8s/base/monitoring/ --policy policy/
```

Verify no unexpected traffic is allowed by checking pod connectivity:

```sh
# Should be rejected (no policy allows this path)
kubectl exec -n monitoring deploy/prometheus -- \
  curl -s --max-time 3 http://todo-api.todo-app.svc.cluster.local:8000/healthz
# Expected: connection refused or timeout  (ingress allowed, but this is a sanity direction test)

# Should succeed
kubectl exec -n todo-app deploy/todo-api -- \
  curl -s --max-time 3 http://todo-db-pooler.todo-app.svc.cluster.local:5432 || echo "TCP conn"
```
