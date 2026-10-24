version_settings(constraint=">=0.37.0")
allow_k8s_contexts("minikube")

# Build straight into minikube's image store and never push, so local builds
# cannot end up in the public registry.
custom_build(
    "areebahmeddd/todo-api",
    command="minikube image build -t $EXPECTED_REF -f Dockerfile .",
    command_bat="minikube image build -t %EXPECTED_REF% -f Dockerfile .",
    deps=["app", "alembic", "alembic.ini", "pyproject.toml", "uv.lock", "Dockerfile"],
    skips_local_docker=True,
    disable_push=True,
)

k8s_yaml(kustomize("k8s/overlays/dev"))

# Bootstrap

# Installs the CNPG operator unless it is already present, for example from ArgoCD.
local_resource("cnpg-operator", cmd="make cnpg-operator", labels=["infra"])

local_resource(
    "secrets",
    cmd="make k8s-secrets OVERLAY=dev",
    labels=["infra"],
)

k8s_resource(
    new_name="postgres",
    objects=["todo-db:Cluster:todo-app", "todo-db-pooler:Pooler:todo-app"],
    resource_deps=["cnpg-operator", "secrets"],
    labels=["infra"],
)

k8s_resource(
    "traefik",
    port_forwards=["9000:9000"],
    links=[link("http://localhost:9000/dashboard/", "Traefik dashboard")],
    labels=["infra"],
)

# Application

k8s_resource(
    "todo-api",
    port_forwards=["8000:8000"],
    links=[
        link("http://localhost:8000/", "UI"),
        link("http://localhost:8000/docs", "Swagger UI"),
    ],
    resource_deps=["postgres"],
    labels=["app"],
)

# Monitoring

k8s_resource("grafana", port_forwards=["3000:3000"], resource_deps=["secrets"], labels=["monitoring"])
k8s_resource("prometheus", port_forwards=["9090:9090"], labels=["monitoring"])
k8s_resource("alertmanager", resource_deps=["secrets"], labels=["monitoring"])
k8s_resource("alloy", port_forwards=["12345:12345"], labels=["monitoring"])
k8s_resource("loki", labels=["monitoring"])
k8s_resource("tempo", labels=["monitoring"])

# Manual tasks

for name, cmd in [("lint", "make lint"), ("test", "make test")]:
    local_resource(name, cmd=cmd, auto_init=False, trigger_mode=TRIGGER_MODE_MANUAL, labels=["dev"])
