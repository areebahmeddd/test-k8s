version_settings(constraint = ">=0.36.0")

# Local clusters only; avoids targeting prod.
allow_k8s_contexts(["kind-todo-k8s", "minikube"])

# Image
# Syncs app/ into the running container on change.
# uvicorn catches SIGHUP on PID 1 and reloads without a pod restart.
docker_build(
    ref = "areebahmeddd/todo-api",
    context = ".",
    dockerfile = "Dockerfile",
    live_update = [
        sync("./app", "/app/app"),
        run("kill -HUP 1 || true", trigger = ["./app"]),
    ],
)

# Manifests
# Secrets are excluded from the Kustomize build (commented out in the overlay)
# and are applied separately by the sops-secrets local_resource below.
k8s_yaml(kustomize("k8s/overlays/dev"))

# Bootstrap (run once at startup, in dependency order)

# Guard: fail fast with a clear message if the CNPG operator is not installed.
# The dev overlay contains Cluster and Pooler CRs that need these CRDs to exist.
local_resource(
    name = "cnpg-check",
    cmd = "kubectl get crd clusters.postgresql.cnpg.io",
    labels = ["infra"],
)

# Decrypts SOPS secrets in memory and applies them; plaintext never touches disk.
# Pods referencing these secrets stay Pending until this completes.
local_resource(
    name = "sops-secrets",
    cmd = (
        "sops -d k8s/overlays/dev/secrets/todo-api-secret.yaml | kubectl apply -f - && " +
        "sops -d k8s/overlays/dev/secrets/todo-db-secret.yaml | kubectl apply -f - && " +
        "sops -d k8s/overlays/dev/secrets/grafana-secret.yaml | kubectl apply -f - && " +
        "sops -d k8s/overlays/dev/secrets/alertmanager-secret.yaml | kubectl apply -f -"
    ),
    resource_deps = ["cnpg-check"],
    labels = ["infra"],
)

# Waits for the CNPG postgres pod and PgBouncer pooler to be Ready.
# todo-db-secret must exist before the Cluster can bootstrap.
local_resource(
    name = "db-ready",
    cmd = (
        "kubectl wait pod -n todo-app -l cnpg.io/cluster=todo-db " +
        "--for=condition=Ready --timeout=300s && " +
        "kubectl rollout status deployment/todo-db-pooler -n todo-app --timeout=120s"
    ),
    resource_deps = ["sops-secrets"],
    labels = ["infra"],
)

# Postgres
# CNPG Cluster and Pooler are custom resources; Tilt can't auto-detect their
# workload type. Group them explicitly so they wait for CNPG CRDs to exist.
k8s_resource(
    new_name = "postgres",
    objects = [
        "todo-db:Cluster:todo-app",
        "todo-db-pooler:Pooler:todo-app",
    ],
    resource_deps = ["cnpg-check"],
    labels = ["infra"],
)

# Networking
# Traefik dashboard on port 9000; port 80 (web entrypoint) is handled by
# minikube tunnel assigning 127.0.0.1 to the LoadBalancer service.
k8s_resource(
    workload = "traefik",
    port_forwards = ["9000:9000"],
    links = [link("http://localhost:9000/dashboard/", "Traefik Dashboard")],
    labels = ["infra"],
)

# Application
# Port-forwarded directly to the pod, bypassing Traefik.
# Stays reachable even if the ingress layer is misconfigured.
k8s_resource(
    workload = "todo-api",
    port_forwards = ["8000:8000"],
    links = [
        link("http://localhost:8000/health", "Health"),
        link("http://localhost:8000/docs",   "Swagger UI"),
        link("http://localhost:8000/redoc",  "ReDoc"),
    ],
    resource_deps = ["db-ready"],
    labels = ["app"],
)

# Monitoring
k8s_resource(
    workload = "grafana",
    port_forwards = ["3000:3000"],
    links = [link("http://localhost:3000", "Grafana")],
    resource_deps = ["sops-secrets"],
    labels = ["monitoring"],
)

k8s_resource(
    workload = "prometheus",
    port_forwards = ["9090:9090"],
    links = [link("http://localhost:9090", "Prometheus")],
    labels = ["monitoring"],
)

k8s_resource(
    workload = "loki",
    labels = ["monitoring"],
)

k8s_resource(
    workload = "tempo",
    labels = ["monitoring"],
)

# Alloy HTTP metrics UI (port 12345); also receives OTLP traces on 4317 but
# that port is internal-only (used by todo-api → alloy → tempo pipeline).
k8s_resource(
    workload = "alloy",
    port_forwards = ["12345:12345"],
    links = [link("http://localhost:12345", "Alloy")],
    labels = ["monitoring"],
)

k8s_resource(
    workload = "alertmanager",
    labels = ["monitoring"],
)

# Dev Tasks
local_resource(
    name = "lint",
    cmd = "uv run ruff check app/ --fix && uv run ruff format app/",
    auto_init = False,
    trigger_mode = TRIGGER_MODE_MANUAL,
    labels = ["dev"],
)

local_resource(
    name = "test",
    cmd = "uv run pytest -v --cov=app --cov-report=term-missing",
    auto_init = False,
    trigger_mode = TRIGGER_MODE_MANUAL,
    labels = ["dev"],
)

local_resource(
    name = "migrate",
    cmd = "uv run alembic upgrade head",
    auto_init = False,
    trigger_mode = TRIGGER_MODE_MANUAL,
    labels = ["dev"],
)
