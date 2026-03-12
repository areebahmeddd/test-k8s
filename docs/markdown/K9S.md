# k9s

## Table of Contents

**Getting Started**

1. [Launch](#1-launch)
2. [Navigation Model](#2-navigation-model)

**Workloads**

3. [Pods](#3-pods)
4. [Deployments](#4-deployments)
5. [StatefulSets](#5-statefulsets)

**Operations**

6. [Scale and Restart](#6-scale-and-restart)
7. [Rollout Status](#7-rollout-status)
8. [Logs](#8-logs)
9. [Shell Into a Pod](#9-shell-into-a-pod)

**Networking**

10. [Ingress](#10-ingress)
11. [Port Forwarding](#11-port-forwarding)

**Cluster State**

12. [Events](#12-events)
13. [ConfigMaps and Secrets](#13-configmaps-and-secrets)
14. [Namespace Switching](#14-namespace-switching)

**Reference**

15. [All Resource Commands](#15-all-resource-commands)
16. [Global Keys](#16-global-keys)
17. [Debugging Flow](#17-debugging-flow)

## 1. Launch

```bash
k9s
```

To target a specific context or namespace at startup:

```bash
k9s --context minikube
k9s --namespace todo-app
k9s --context my-eks-cluster --namespace production
```

The active context and namespace are always shown in the **top-right header bar**.

## 2. Navigation Model

k9s works like Vim — type a command prefixed with `:` to jump to any resource view, then use keys to act on rows.

```
:pods          → list all pods
  Enter        → drill into pod (see containers)
  l            → stream logs
  s            → shell into container
  d            → describe (full kubectl describe output)
  y            → view raw YAML
  Ctrl+d       → delete
  Esc          → go back
```

`/` filters any list by string. `?` shows all available keys for the current view.

## 3. Pods

```
:pods
```

Press `0` to show pods across **all namespaces** at once. A `NAMESPACE` column appears.

```
:pods              # current namespace
:pods → 0          # all namespaces
/todo-api          # filter to todo-api pods
```

Column meanings:

| Column        | What it means                                                 |
| ------------- | ------------------------------------------------------------- |
| `READY`       | `1/1` = container running and passing readiness probe         |
| `STATUS`      | `Running` / `Pending` / `CrashLoopBackOff` / `OOMKilled`      |
| `RESTARTS`    | Times the container has restarted — climbing number = problem |
| `CPU` / `MEM` | Live resource usage (requires metrics-server)                 |
| `AGE`         | How long the pod has been running                             |

## 4. Deployments

```
:deploy
```

Shows all Deployments with `READY`, `UP-TO-DATE`, and `AVAILABLE` columns.

For your cluster:

| Deployment      | Namespace    | Expected READY                     |
| --------------- | ------------ | ---------------------------------- |
| `todo-api`      | `todo-app`   | `1/1` (dev) · `2/2–4/4` (prod HPA) |
| `argocd-server` | `argocd`     | `1/1`                              |
| `grafana`       | `monitoring` | `1/1`                              |
| `prometheus`    | `monitoring` | `1/1`                              |
| `traefik`       | `traefik`    | `1/1`                              |

Press `d` on any deployment to see its full spec, labels, strategy, and events.

## 5. StatefulSets

```
:sts
```

Your `todo-db` PostgreSQL database runs as a StatefulSet (not a Deployment) so it gets a stable network identity and a persistent volume. Check:

```
:sts → todo-db → d     # describe — confirm PVC is Bound
:pvc                   # list PersistentVolumeClaims — STATUS must be Bound
```

If the PVC is `Pending`, the DB pod cannot start.

## 6. Scale and Restart

### Scale a deployment

Navigate to `:deploy`, highlight the deployment, press `s`:

A prompt appears — enter the desired replica count and confirm.

Equivalent kubectl:

```bash
kubectl scale deployment/todo-api --replicas=0 -n todo-app   # scale to zero (stops all pods)
kubectl scale deployment/todo-api --replicas=1 -n todo-app   # bring back up
```

### Scale to zero (force stop without deleting)

Scaling to `0` is the clean way to stop a workload without deleting the Deployment. The config, secrets, and PVCs remain intact. Scale back to `1` to restart.

Useful when:

- You need to apply a secret change before the next start
- You want to free resources temporarily on a local cluster

```bash
# In k9s terminal (Ctrl+` to open built-in terminal)
kubectl scale deployment/todo-api --replicas=0 -n todo-app
kubectl scale deployment/grafana --replicas=0 -n monitoring
```

### Restart a deployment (rolling restart)

Navigate to `:deploy`, highlight the deployment, press `Ctrl+r` — or from the k9s terminal:

```bash
kubectl rollout restart deployment/todo-api -n todo-app
```

This triggers a rolling restart: new pods come up first, old pods terminate after. Zero downtime.

### Delete a pod (force restart via ReplicaSet)

Navigate to `:pods`, highlight the pod, press `Ctrl+d` → confirm.

The owning ReplicaSet immediately creates a replacement. This is the fastest way to restart a single pod without touching the Deployment.

### Delete a Deployment (full removal)

Navigate to `:deploy`, highlight, press `Ctrl+d` → confirm.

This removes the Deployment and all its pods. The namespace, ConfigMap, and Secrets remain. Re-apply with:

```bash
kustomize build k8s/overlays/dev/ | kubectl apply -f -
```

## 7. Rollout Status

This is the most important view when you push a new image version — on minikube, EKS, or any cluster.

### Watch a rollout in progress

```
:deploy → todo-api → d
```

Scroll to the `Events` section at the bottom of the describe output. You will see:

```
Scaled up replica set todo-api-<new-hash> to 1
Scaled down replica set todo-api-<old-hash> to 0
```

Or from the k9s terminal:

```bash
kubectl rollout status deployment/todo-api -n todo-app
# Waiting for deployment "todo-api" rollout to finish: 1 old replicas are pending termination...
# deployment "todo-api" successfully rolled out
```

### Check rollout history (version tracking)

```bash
kubectl rollout history deployment/todo-api -n todo-app
# REVISION  CHANGE-CAUSE
# 1         <none>
# 2         <none>
```

See what changed in a specific revision:

```bash
kubectl rollout history deployment/todo-api -n todo-app --revision=2
```

### Watch pods cycle during rollout

```
:pods → /todo-api
```

During a rolling update you will briefly see **two pods** — old (`Terminating`) and new (`ContainerCreating` → `Running`). Watch the RESTARTS column on the new pod — if it climbs, the new version has a startup crash.

### Roll back to the previous version

```bash
kubectl rollout undo deployment/todo-api -n todo-app
```

Roll back to a specific revision:

```bash
kubectl rollout undo deployment/todo-api -n todo-app --to-revision=1
```

### On EKS with ArgoCD (GitOps rollout flow)

When you commit and push to the `dev` branch:

1. ArgoCD detects the diff (polls every 3 minutes by default, or via webhook instantly)
2. ArgoCD triggers a sync — applies the updated manifest to the cluster
3. Kubernetes starts a rolling update on the Deployment

Watch this in k9s:

```
:application → todo-app-dev → d    # sync status: Synced / OutOfSync / Progressing
:deploy → todo-api               # READY column: 0/1 → 1/1
:pods → /todo-api                # watch old pod Terminate, new pod go Running
```

The `STATUS` field in `:application` goes:

```
OutOfSync → Progressing → Synced (Healthy)
```

If it stops at `Degraded`, the new pod is crashing — go to `:pods` → `l` to read the logs.

## 8. Logs

Navigate to `:pods`, highlight a pod, press `l`.

| Key             | Action                                   |
| --------------- | ---------------------------------------- |
| `f`             | Toggle fullscreen                        |
| `w`             | Toggle line wrap                         |
| `/`             | Filter log lines by string               |
| `0`             | Show logs from all containers in the pod |
| `Ctrl+s`        | Save logs to a file                      |
| `g` / `Shift+g` | Jump to top / bottom                     |
| `Esc`           | Go back                                  |

Useful filters for your stack:

```
/ERROR          # show only error lines
/trace_id       # show only lines carrying OTel trace IDs
/migration      # check Alembic migration output at startup
```

## 9. Shell Into a Pod

Navigate to `:pods`, highlight a pod, press `s`. A shell opens inside the container.

Common checks inside `todo-api`:

```bash
# Test database connectivity
nc -zv todo-db 5432
# todo-db (5432): Connection succeeded

# Confirm env vars are populated from the secret
env | grep DATABASE_URL
env | grep SECRET_KEY

# Test the health endpoint from inside the pod
curl -s http://localhost:8000/health
```

Common checks inside `todo-db`:

```bash
# Connect to the database
psql -U $POSTGRES_USER -d $POSTGRES_DB

# List tables (confirm migrations applied)
\dt

# Quit
\q
```

Press `Ctrl+d` to exit the shell.

## 10. Ingress

```
:ing
```

Shows all Ingress and IngressRoute resources. For your cluster, filter to each namespace:

| Namespace    | Host                   | Backend                   |
| ------------ | ---------------------- | ------------------------- |
| `todo-app`   | `todo.localhost`       | `todo-api:8000`           |
| `argocd`     | `argocd.localhost`     | `argocd-server:80`        |
| `monitoring` | `grafana.localhost`    | `grafana:3000`            |
| `monitoring` | `prometheus.localhost` | `prometheus:9090`         |
| `traefik`    | `traefik.localhost`    | Traefik dashboard `:9000` |

Press `d` on an Ingress to see the full routing rules and any Traefik middleware annotations.

To verify routing is actually working, check the Traefik Service has an external IP:

```
:svc → traefik namespace → traefik
```

`EXTERNAL-IP` must be `127.0.0.1` (not `<pending>`). If it is pending, `minikube tunnel` is not running. On EKS, this will be an AWS load balancer hostname.

## 11. Port Forwarding

Navigate to any **Service** or **Pod**, press `Shift+f`.

A dialog appears asking for the local port. Enter it and confirm. The port-forward stays active until you press `Shift+f` again or close k9s.

Active port-forwards are listed in the k9s header bar.

Recommended forwards for this project:

| Service             | Namespace    | Local port |
| ------------------- | ------------ | ---------- |
| `todo-api`          | `todo-app`   | `8000`     |
| `argocd-server`     | `argocd`     | `8080`     |
| `grafana`           | `monitoring` | `3000`     |
| `prometheus-server` | `monitoring` | `9090`     |
| `traefik`           | `traefik`    | `9000`     |

> Port forwarding bypasses Traefik entirely — useful when `minikube tunnel` is not running or you are on EKS and only want direct access to a single service.

## 12. Events

```
:events
```

Events are the first place to look when something is wrong. Press `Ctrl+s` to sort by most recent.

Useful filters:

```
/Warning        # show only Warning events (ignore Normal)
/todo-app       # show only events from todo-app namespace
/todo-api       # show only events related to todo-api
/Failed         # show FailedScheduling, FailedMount, etc.
/OOM            # show OOMKilled events
```

Press `d` on an event row for the full detail message.

## 13. ConfigMaps and Secrets

### ConfigMaps

```
:cm → todo-app namespace → todo-api-config
```

Shows all key-value pairs from the ConfigMap as a table. This is what gets injected into `todo-api` via `envFrom.configMapRef`.

### Secrets

```
:secret → todo-app namespace → todo-api-secret
```

Values are masked by default. Press `x` to decode and reveal a value. These are the SOPS-decrypted secrets that were applied during `make k8s-deploy`.

## 14. Namespace Switching

| Action                         | How                                  |
| ------------------------------ | ------------------------------------ |
| Switch namespace               | `:ns` → arrow to namespace → `Enter` |
| All namespaces in current view | Press `0`                            |
| Cycle recent namespaces        | Press `n`                            |
| Filter within a view           | `/todo-app` to filter rows           |
| Target namespace at launch     | `k9s --namespace todo-app`           |

The active namespace is shown in the **top-right header** next to the context name.

## 15. All Resource Commands

| Command        | Resource                         |
| -------------- | -------------------------------- |
| `:pods`        | Pods                             |
| `:deploy`      | Deployments                      |
| `:sts`         | StatefulSets                     |
| `:rs`          | ReplicaSets                      |
| `:svc`         | Services                         |
| `:ing`         | Ingresses                        |
| `:ep`          | Endpoints                        |
| `:cm`          | ConfigMaps                       |
| `:secret`      | Secrets                          |
| `:pvc`         | PersistentVolumeClaims           |
| `:pv`          | PersistentVolumes                |
| `:hpa`         | HorizontalPodAutoscalers         |
| `:ns`          | Namespaces                       |
| `:nodes`       | Nodes                            |
| `:events`      | Events                           |
| `:crd`         | Custom Resource Definitions      |
| `:application` | ArgoCD Application CRDs          |
| `:sa`          | ServiceAccounts                  |
| `:rb`          | RoleBindings                     |
| `:contexts`    | Switch kubeconfig context        |
| `Ctrl+a`       | Full list of every resource type |

## 16. Global Keys

| Key       | Action                                          |
| --------- | ----------------------------------------------- |
| `0`       | All namespaces in current view                  |
| `/`       | Fuzzy filter the current list                   |
| `?`       | Show available keys for this view               |
| `Esc`     | Go back one level                               |
| `Ctrl+r`  | Force refresh current view                      |
| `Ctrl+\`` | Open built-in terminal (kubectl pre-configured) |
| `q`       | Quit                                            |

### Keys on any resource row

| Key       | Action                              |
| --------- | ----------------------------------- |
| `d`       | Describe                            |
| `y`       | View YAML                           |
| `e`       | Edit YAML live                      |
| `s`       | Shell (pods only)                   |
| `l`       | Logs (pods only)                    |
| `Shift+f` | Port forward                        |
| `Ctrl+d`  | Delete                              |
| `Ctrl+k`  | Force delete (no graceful shutdown) |

## 17. Debugging Flow

A repeatable sequence covering the most common failure scenarios:

```
:events → /Warning → Ctrl+s        # 1. Find what broke (sort by latest)

:pods → 0 → /todo-api              # 2. Check pod STATUS and RESTARTS
  → d                              # 3. Describe → probe failures, image errors, OOM
  → l                              # 4. Stream logs → read the actual exception
  → s                              # 5. Shell in → nc -zv todo-db 5432

:pvc → todo-app                    # 6. Confirm DB volume is Bound
:application → todo-app-dev → d    # 7. ArgoCD sync status → Synced / Degraded
:deploy → todo-api → d             # 8. Check rollout events during a new deploy
```
