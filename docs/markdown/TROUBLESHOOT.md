# Troubleshooting

## Table of Contents

**Infrastructure**

1. [Minikube Won't Start](#1-minikube-wont-start)
2. [Images Missing Inside Minikube](#2-images-missing-inside-minikube)
3. [Cluster Resource Pressure](#3-cluster-resource-pressure)

**Pre-deploy Checks**

4. [Secrets Not Decrypting (SOPS / age)](#4-secrets-not-decrypting-sops--age)
5. [Kustomize Build Fails](#5-kustomize-build-fails)
6. [Policy Validation Failures](#6-policy-validation-failures)

**Deploy & Routing**

7. [ArgoCD Application Stuck in OutOfSync or Progressing](#7-argocd-application-stuck-in-outofsync-or-progressing)
8. [Traefik Not Routing (curl connection refused)](#8-traefik-not-routing-curl-connection-refused)

**App Runtime**

9. [todo-api Pod in CrashLoopBackOff or Pending](#9-todo-api-pod-in-crashloopbackoff-or-pending)
10. [Database Connection Refused](#10-database-connection-refused)
11. [Alembic Migration Fails Inside the Pod](#11-alembic-migration-fails-inside-the-pod)

**Observability & Scaling**

12. [Metrics / Traces / Logs Not Appearing in Grafana](#12-metrics--traces--logs-not-appearing-in-grafana)
13. [HPA Not Scaling (prod overlay)](#13-hpa-not-scaling-prod-overlay)

## 1. Minikube Won't Start

**Symptoms:**

```bash
$ make minikube-create
# Exiting due to PROVIDER_DOCKER_NOT_RUNNING: ...
# or: Failed to start minikube: exit status 1
```

**Debug:**

```bash
# Confirm Docker is running
docker info

# Check existing minikube state
minikube status

# Inspect startup logs
minikube logs --file=minikube-debug.log
cat minikube-debug.log | tail -50
```

**Fix:**

```bash
# Clean broken state and retry
minikube delete
minikube start --cpus=4 --memory=8192

# If Docker Desktop on Windows: ensure WSL2 backend is enabled and Docker Desktop is running
# If resource error: lower memory to 6144 or cpus to 2
minikube start --cpus=2 --memory=6144
```

## 2. Images Missing Inside Minikube

**Symptoms:**

```bash
$ kubectl get pods -n todo-app
# todo-api-xxx   0/1   ErrImagePull   or   ImagePullBackOff
```

**Debug:**

```bash
# Confirm what minikube has cached
minikube image ls | grep todo-api

# Check the exact pull error
kubectl describe pod -n todo-app -l app.kubernetes.io/name=todo-api | grep -A10 Events
```

**Fix:**

```bash
# Rebuild and reload — images on the host are NOT visible inside minikube by default
make k8s-build
make minikube-load

# Confirm the image is now present
minikube image ls | grep todo-api
# areebahmeddd/todo-api:1.0.0

# Force a rollout to pick up the freshly loaded image
kubectl rollout restart deployment/todo-api -n todo-app
```

## 3. Cluster Resource Pressure

**Symptoms:**

```bash
$ kubectl get pods -n todo-app
# todo-api-xxx   0/1   Pending
# or: OOMKilled
```

**Check node and namespace resource consumption:**

```bash
# Node-level CPU and memory usage
kubectl top nodes

# Pod-level usage across all namespaces
kubectl top pods -A

# Allocated vs available capacity on the node
kubectl describe nodes | grep -A10 "Allocated resources"

# Check for any resource pressure conditions (MemoryPressure, DiskPressure, PIDPressure)
kubectl get nodes -o wide
kubectl describe nodes | grep -A5 Conditions

# Check recent OOMKilled events cluster-wide
kubectl get events -A --field-selector reason=OOMKilling --sort-by='.lastTimestamp'

# Minikube dashboard (opens in browser — requires minikube tunnel running)
minikube dashboard
```

**Fix:**

```bash
# Not enough node resources — restart minikube with higher limits
minikube delete
minikube start --cpus=4 --memory=8192

# A single pod is using too much — check its actual vs requested usage
kubectl top pod <pod-name> -n <namespace>
# Then tighten or raise limits in the relevant manifest

# Monitoring namespace consuming too much on a small local cluster
# Scale down non-essential components temporarily
kubectl scale deployment grafana --replicas=0 -n monitoring
kubectl scale deployment tempo --replicas=0 -n monitoring
```

## 4. Secrets Not Decrypting (SOPS / age)

**Symptoms:**

```bash
$ make k8s-deploy
# ERROR: age.key not found at /path/to/age.key
# or: ERROR: age.key cannot decrypt secrets in k8s/overlays/dev/secrets/
```

Or the pod starts but immediately crashes:

```bash
$ kubectl get pods -n todo-app
# todo-api-xxx   0/1   CrashLoopBackOff
$ kubectl logs -n todo-app -l app.kubernetes.io/name=todo-api
# pydantic_settings.exceptions.SettingsError: DATABASE_URL not set
```

**Debug:**

```bash
# Check that your key file exists
ls -la age.key

# Test decryption manually against one secret
sops -d k8s/overlays/dev/secrets/todo-api-secret.yaml

# Check what public key was used to encrypt the file
grep 'age1' k8s/overlays/dev/secrets/todo-api-secret.yaml

# Compare with the public key derived from your age.key
age-keygen -y age.key
# Output should match the recipient listed in the encrypted file

# Confirm the sops-age secret is present in the cluster (for ArgoCD-driven decryption)
kubectl get secret sops-age -n argocd
kubectl get secret sops-age -n argocd -o jsonpath='{.data.key\.txt}' | base64 -d | head -3
```

**Fix:**

```bash
# Case 1: age.key is missing — get the team key or generate a fresh one
age-keygen -o age.key
# Then re-encrypt all secrets with the new key:
make sops-encrypt

# Case 2: Wrong key (MAC mismatch / decryption failed)
# Replace age.key with the correct team key, then verify:
sops -d k8s/overlays/dev/secrets/todo-api-secret.yaml

# Case 3: sops-age cluster secret is stale
kubectl delete secret sops-age -n argocd
kubectl create secret generic sops-age \
  --from-file=key.txt=age.key \
  --namespace=argocd
kubectl rollout restart deployment/argocd-repo-server -n argocd

# Case 4: Secrets committed unencrypted — encrypt before re-deploying
make validate-sops    # will flag which files are plaintext
make sops-encrypt
```

## 5. Kustomize Build Fails

**Symptoms:**

```bash
$ make validate-k8s
# Error: accumulating resources: ...
# or: json: cannot unmarshal ...
```

**Debug:**

```bash
# Build each overlay individually to isolate which one fails
kustomize build k8s/overlays/dev
kustomize build k8s/overlays/prod

# Build the ArgoCD kustomization (pulls the upstream install manifest)
kustomize build k8s/argocd/

# Validate the rendered YAML against Kubernetes schemas
kustomize build k8s/overlays/dev | kubeconform -strict -ignore-missing-schemas -summary -skip Secret -
```

**Fix:**

```bash
# Invalid YAML indentation — run a YAML linter
kustomize build k8s/overlays/dev | python -c "import sys,yaml; list(yaml.safe_load_all(sys.stdin))"

# Broken reference (resource file missing) — check resources: list in the failing kustomization.yaml
cat k8s/overlays/dev/kustomization.yaml
ls k8s/overlays/dev/

# Patch target mismatch — verify kind/name in the patch block matches the actual resource
kustomize build k8s/overlays/prod 2>&1 | grep "no resource"
```

## 6. Policy Validation Failures

**Symptoms:**

```bash
$ make validate-policies
# FAIL - k8s/overlays/dev
# app/todo-api-deployment.yaml: container 'todo-api' has no readinessProbe
# or: image 'todo-api:latest' uses the :latest tag
```

**Debug:**

```bash
# Run each validation step individually to isolate the failing check
make validate-k8s        # kustomize build dry-run
make validate-sops       # all secrets must carry sops: and ENC[ markers
make validate-schema     # kubeconform schema check
make validate-policies   # OPA/conftest — resource limits, labels, probes, image tags

# Run conftest directly with verbose output
kustomize build k8s/overlays/dev | conftest test --no-color --all-namespaces -p policy/ -

# Show which policy rule is failing
conftest test --no-color --all-namespaces --report -p policy/ - < <(kustomize build k8s/overlays/dev)
```

**Common violations and fixes:**

| Failure                              | Location                                | Fix                                             |
| ------------------------------------ | --------------------------------------- | ----------------------------------------------- |
| Missing resource limits              | `k8s/base/app/todo-api-deployment.yaml` | Add `resources.limits.cpu/memory`               |
| Missing `app.kubernetes.io/*` labels | Any workload manifest                   | Add all four required labels                    |
| Image uses `:latest` tag             | Deployment or StatefulSet               | Pin to a specific version tag                   |
| Missing readiness/liveness probe     | Deployment                              | Add `readinessProbe` and `livenessProbe` blocks |
| Secret not SOPS-encrypted            | `k8s/overlays/*/secrets/`               | Run `make sops-encrypt`                         |

```bash
# After fixing, re-run the full suite
make validate
```

## 7. ArgoCD Application Stuck in OutOfSync or Progressing

**Symptoms:**

```bash
$ kubectl get applications -n argocd
# todo-app-dev   OutOfSync   Progressing
# or: todo-app-dev   Synced   Degraded
```

**Debug:**

```bash
# Get the full sync error message
kubectl describe application todo-app-dev -n argocd | grep -A30 "Status:"

# Check repo-server logs — covers git clone, kustomize build, and SOPS errors
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-repo-server --tail=80

# Check application controller logs — covers resource apply errors
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller --tail=80

# List recent events scoped to this application
kubectl get events -n argocd --field-selector involvedObject.name=todo-app-dev --sort-by='.lastTimestamp'

# Verify the target branch exists and the path is correct
# (targetRevision: dev, path: k8s/overlays/dev in the Application manifest)
kubectl get application todo-app-dev -n argocd -o jsonpath='{.spec.source}'
```

**Common causes and fixes:**

```bash
# 1. Git branch doesn't exist or was renamed
#    Edit k8s/argocd/applications/todo-app-dev.yaml → targetRevision
#    Then re-apply:
kubectl apply -k k8s/argocd/ --server-side

# 2. Kustomize build error — test locally before pushing
kustomize build k8s/overlays/dev

# 3. SOPS decryption fails in repo-server (wrong or missing sops-age secret)
#    → See section 4 above, then restart repo-server:
kubectl rollout restart deployment/argocd-repo-server -n argocd

# 4. Force a manual sync if automated sync is stuck
kubectl patch application todo-app-dev -n argocd \
  --type merge -p '{"operation":{"sync":{"revision":"dev"}}}'
```

## 8. Traefik Not Routing (curl connection refused)

**Symptoms:**

```bash
$ curl http://todo.localhost
# curl: (7) Failed to connect to todo.localhost port 80
# or: 404 page not found
```

**Debug:**

```bash
# 1. Check Traefik pod is running
kubectl get pods -n traefik

# 2. Check the LoadBalancer external IP — must be 127.0.0.1, not <pending>
kubectl get svc -n traefik
# If <pending>: minikube tunnel is not running → see fix below

# 3. Check that the Ingress resource exists and has the right host
kubectl get ingress -n todo-app
kubectl describe ingress todo-api -n todo-app

# 4. Check Traefik logs for routing errors
kubectl logs -n traefik -l app.kubernetes.io/name=traefik --tail=50

# 5. Verify hosts file entry
# Windows: type C:\Windows\System32\drivers\etc\hosts | findstr localhost
# Linux/macOS: grep localhost /etc/hosts
```

**Fix:**

```bash
# Minikube tunnel must be running in an elevated window (gives LoadBalancer its external IP)
# Windows PowerShell (Admin):
Start-Process powershell -ArgumentList "-NoExit", "-Command", "minikube tunnel" -Verb RunAs

# Linux / macOS:
sudo minikube tunnel

# Confirm external IP is now assigned
kubectl get svc -n traefik
# NAME      TYPE           EXTERNAL-IP   PORT(S)
# traefik   LoadBalancer   127.0.0.1     80:...

# If hosts file entry is missing, add:
# 127.0.0.1  todo.localhost argocd.localhost grafana.localhost prometheus.localhost traefik.localhost

# Test routing directly through Traefik (bypasses DNS)
kubectl port-forward -n traefik svc/traefik 8080:80
curl -H "Host: todo.localhost" http://localhost:8080/health
```

## 9. todo-api Pod in CrashLoopBackOff or Pending

**Symptoms:**

```bash
$ kubectl get pods -n todo-app
# todo-api-xxx   0/1   CrashLoopBackOff
# or: todo-api-xxx   0/1   Pending
```

**Debug:**

```bash
# Read the crash reason
kubectl logs -n todo-app -l app.kubernetes.io/name=todo-api --previous

# Read pod events (Pending → often a scheduling or resource issue)
kubectl describe pod -n todo-app -l app.kubernetes.io/name=todo-api | grep -A20 Events

# Confirm all required secrets and configmaps are present
kubectl get secret todo-api-secret -n todo-app
kubectl get configmap todo-api-config -n todo-app

# Dump the env the pod would receive (without starting it)
kubectl get secret todo-api-secret -n todo-app -o jsonpath='{.data}' | \
  python -c "import sys,json,base64; [print(k,'=',base64.b64decode(v).decode()) for k,v in json.load(sys.stdin).items()]"
```

**Fix:**

```bash
# Missing secret → apply it
sops -d k8s/overlays/dev/secrets/todo-api-secret.yaml | kubectl apply -f -

# Image not loaded → reload
make minikube-load
kubectl rollout restart deployment/todo-api -n todo-app

# Startup config error (wrong DATABASE_URL, SECRET_KEY, etc.)
# Edit the plaintext secret, re-encrypt, re-apply:
sops k8s/overlays/dev/secrets/todo-api-secret.yaml  # opens in $EDITOR
sops -d k8s/overlays/dev/secrets/todo-api-secret.yaml | kubectl apply -f -

# Pending due to resource pressure — check node capacity
kubectl describe nodes | grep -A5 "Allocated resources"
# Lower the resource requests in k8s/base/app/todo-api-deployment.yaml if needed
```

## 10. Database Connection Refused

**Symptoms:**

```bash
$ kubectl logs -n todo-app -l app.kubernetes.io/name=todo-api
# sqlalchemy.exc.OperationalError: (asyncpg.exceptions.ConnectionRefusedError) ...
# or: could not connect to server: Connection refused
```

**Debug:**

```bash
# Check the PostgreSQL pod state
kubectl get pods -n todo-app -l app.kubernetes.io/name=todo-db

# Read Postgres logs
kubectl logs -n todo-app -l app.kubernetes.io/name=todo-db --tail=30

# Check ClusterIP service exists
kubectl get svc -n todo-app

# Verify the DATABASE_URL in the todo-api-secret points to the right host/db
kubectl get secret todo-api-secret -n todo-app -o jsonpath='{.data.DATABASE_URL}' | base64 -d
# Expected: postgresql+asyncpg://todo_admin:<pass>@todo-db:5432/todos

# Run pg_isready from inside the todo-api pod
kubectl exec -n todo-app deployment/todo-api -- \
  pg_isready -h todo-db -U todo_admin -d todos
```

**Fix:**

```bash
# Postgres not ready yet — wait for StatefulSet to reach 1/1
kubectl rollout status statefulset/todo-db -n todo-app

# Secret missing or wrong credentials
sops -d k8s/overlays/dev/secrets/todo-db-secret.yaml | kubectl apply -f -
kubectl rollout restart statefulset/todo-db -n todo-app

# Wrong hostname in DATABASE_URL — must be `todo-db` (ClusterIP service name), not localhost
# Fix: edit and re-encrypt the todo-api-secret, then reapply and restart
sops k8s/overlays/dev/secrets/todo-api-secret.yaml
sops -d k8s/overlays/dev/secrets/todo-api-secret.yaml | kubectl apply -f -
kubectl rollout restart deployment/todo-api -n todo-app
```

## 11. Alembic Migration Fails Inside the Pod

**Symptoms:**

```bash
$ kubectl exec -n todo-app deploy/todo-api -- uv run alembic upgrade head
# sqlalchemy.exc.OperationalError: ...
# or: ERROR [alembic.util.exc] Can't locate revision ...
```

**Debug:**

```bash
# Confirm the pod is running and healthy before running migrations
kubectl get pods -n todo-app -l app.kubernetes.io/name=todo-api

# Check current migration state
kubectl exec -n todo-app deploy/todo-api -- uv run alembic current

# List available revisions
kubectl exec -n todo-app deploy/todo-api -- uv run alembic history --verbose

# Check the DATABASE_URL the app sees at runtime
kubectl exec -n todo-app deploy/todo-api -- env | grep DATABASE_URL
```

**Fix:**

```bash
# Database is unreachable — resolve section 10 first, then retry

# Revision mismatch (e.g., after a bad downgrade)
kubectl exec -n todo-app deploy/todo-api -- uv run alembic downgrade base
kubectl exec -n todo-app deploy/todo-api -- uv run alembic upgrade head

# Corrupt alembic_version table — nuclear option (dev only, destroys all data)
kubectl exec -n todo-app deploy/todo-api -- \
  uv run alembic stamp head --purge
kubectl exec -n todo-app deploy/todo-api -- uv run alembic upgrade head
```

## 12. Metrics / Traces / Logs Not Appearing in Grafana

**Symptoms:**

- Grafana dashboard shows "No data"
- Prometheus targets page shows the `todo-api` job as DOWN
- Loki returns zero results for `{service="todo-api"}`
- Tempo shows no traces

**Debug:**

```bash
# --- Metrics ---
# Check Prometheus scrape targets (port-forward first if not using minikube tunnel)
kubectl port-forward -n monitoring svc/prometheus 9090:9090 &
# Then open: http://localhost:9090/targets
# Look for todo-api job → should show "UP"

# Check OTel Collector is running (API pushes traces through it)
kubectl get pods -n monitoring -l app.kubernetes.io/name=otel-collector
kubectl logs -n monitoring -l app.kubernetes.io/name=otel-collector --tail=30

# --- Traces ---
# Check the OTEL endpoint the api is configured to send to
kubectl get configmap todo-api-config -n todo-app -o jsonpath='{.data.OTEL_EXPORTER_OTLP_ENDPOINT}'
# Expected: otel-collector.monitoring.svc.cluster.local:4317

# Check Tempo is receiving spans
kubectl logs -n monitoring -l app.kubernetes.io/name=tempo --tail=30

# --- Logs ---
# Check Promtail DaemonSet is running on the node
kubectl get pods -n monitoring -l app.kubernetes.io/name=promtail

# Check Promtail can reach Loki
kubectl logs -n monitoring -l app.kubernetes.io/name=promtail --tail=30 | grep -i "error\|level=error"

# Verify Loki is healthy
kubectl logs -n monitoring -l app.kubernetes.io/name=loki --tail=20
```

**Fix:**

```bash
# Prometheus cannot reach todo-api (scrape DOWN)
# → Confirm svc/todo-api exists in todo-app namespace and port 8000 is correct
kubectl get svc -n todo-app
kubectl port-forward -n todo-app svc/todo-api 8000:8000
curl http://localhost:8000/metrics   # should return Prometheus exposition format

# OTel Collector crashing — check for config errors
kubectl describe deployment otel-collector -n monitoring | grep -A10 Events
kubectl rollout restart deployment/otel-collector -n monitoring

# Grafana datasources not pointing to the right service
kubectl get configmap -n monitoring | grep datasource
kubectl get configmap grafana-datasources -n monitoring -o yaml
# Verify: prometheus URL = http://prometheus:9090
#         loki URL       = http://loki:3100
#         tempo URL      = http://tempo:3200

# Restart the full monitoring stack if all else fails
kubectl rollout restart deployment -n monitoring
```

## 13. HPA Not Scaling (prod overlay)

**Symptoms:**

```bash
$ kubectl get hpa -n todo-app
# todo-api   Deployment/todo-api   <unknown>/70%   2   4   2   5m
# TARGETS shows <unknown>
```

**Debug:**

```bash
# <unknown> means metrics-server is not running or not reachable
kubectl get deployment metrics-server -n kube-system
kubectl logs -n kube-system -l k8s-app=metrics-server --tail=20

# Check HPA events for descriptive error
kubectl describe hpa todo-api -n todo-app | grep -A10 Events

# Verify current pod resource usage
kubectl top pods -n todo-app
```

**Fix:**

```bash
# Enable metrics-server addon in minikube (not enabled by default)
minikube addons enable metrics-server

# Wait for it to start
kubectl rollout status deployment/metrics-server -n kube-system

# Confirm kubectl top now returns data
kubectl top pods -n todo-app

# HPA should update within ~30 seconds
kubectl get hpa -n todo-app -w
```
