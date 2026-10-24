# Kubernetes

## Prerequisites

You need `kubectl`, `kustomize`, `minikube` (Docker driver), `helm`, `sops` and `age`. Depending on how you
deploy, you may also want `tilt`, `argocd`, `k9s`, `pulumi`, `kubeconform` and `conftest`. SOPS reads the age
private key from `./age.key`, which is git-ignored. The Makefile uses bash, so on Windows run `make` from Git
Bash.

```bash
make cluster-up     # minikube with Calico, 4 CPUs and 8 GiB of memory
```

Calico is required because minikube's default network plugin does not enforce NetworkPolicies. The policies
assume minikube's defaults: service CIDR `10.96.0.0/12` and node IP `192.168.49.2`.

## Namespaces

| Namespace     | Workloads                                                                 |
| ------------- | ------------------------------------------------------------------------- |
| `traefik`     | Traefik ingress controller (a `LoadBalancer` Service, port 80 to 8000)    |
| `todo-app`    | `todo-api` Deployment, `todo-db` CNPG Cluster, `todo-db-pooler` PgBouncer |
| `monitoring`  | Prometheus, Alertmanager, Grafana, Loki, Tempo and Alloy                  |
| `cnpg-system` | CloudNativePG operator                                                    |
| `argocd`      | ArgoCD (GitOps deployments only)                                          |

The Kustomize layout and the differences between the overlays are described in
[k8s/README.md](../k8s/README.md).

## Deploying

There are four ways to deploy. Use one of them per cluster.

### 1. Tilt, for local development

```bash
tilt up            # or `tilt ci` to deploy once and exit when everything is healthy
```

Tilt installs the CNPG operator if it is missing (`make cnpg-operator`), applies the SOPS secrets
(`make k8s-secrets`), builds the API image inside minikube and deploys `k8s/overlays/dev`. It rebuilds and
redeploys whenever the code changes, and never pushes images anywhere. It also port-forwards the API (`8000`),
Grafana (`3000`), Prometheus (`9090`), Alloy (`12345`) and the Traefik dashboard (`9000`).

### 2. Plain kubectl, to deploy an overlay once

The same steps Tilt runs, done by hand. This also works for the prod overlay (enable metrics-server for its
HPA with `minikube addons enable metrics-server`):

```bash
make cnpg-operator                              # install the CNPG operator (Helm)
make k8s-secrets OVERLAY=dev                    # decrypt and apply the secrets
make image                                      # build the API image inside minikube
kubectl apply --server-side -k k8s/overlays/dev
```

Remove it with `kubectl delete -k k8s/overlays/dev`.

### 3. ArgoCD, for GitOps

ArgoCD deploys what is in Git and pulls the API image from Docker Hub, so publish the image for the version in
the manifests first, then bootstrap:

```bash
make image-push                 # builds and pushes areebahmeddd/todo-api:<version>
make k8s-deploy                 # OVERLAY=dev by default, or OVERLAY=prod
```

`make k8s-deploy` applies `k8s/argocd/<overlay>` (ArgoCD itself, its ingress and NetworkPolicies, and two
Applications), then the SOPS secrets. From then on ArgoCD syncs from GitHub:

- `cloudnativepg` installs the CNPG Helm chart into `cnpg-system`.
- `todo-app` deploys `k8s/overlays/<overlay>` from the branch with the same name, with automated sync, pruning
  and self-healing. It keeps retrying until the CNPG CRDs from the first Application are registered.

Changes reach the cluster only after they are pushed to that branch. To get ArgoCD's initial admin password:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d
```

### 4. Pulumi, for GitOps with secrets from Pulumi config

This works like the ArgoCD path, but the Kubernetes Secrets come from encrypted Pulumi config instead of the
SOPS files. See [infra/README.md](../infra/README.md).

## Accessing services

Ingress hosts are `*.localhost` in dev, which browsers and curl resolve to 127.0.0.1, and `*.1mindlabs.org` in
prod. To give Traefik's `LoadBalancer` an address on 127.0.0.1, keep a tunnel running (it needs admin rights):

```bash
minikube tunnel
```

| Service    | Dev URL                               | Login                                  |
| ---------- | ------------------------------------- | -------------------------------------- |
| API and UI | <http://todo.localhost>               | Register in the UI                     |
| Grafana    | <http://grafana.localhost>            | Credentials from `grafana-secret`      |
| Prometheus | <http://prometheus.localhost>         | None                                   |
| Alloy      | <http://alloy.localhost>              | None                                   |
| Traefik    | <http://traefik.localhost/dashboard/> | None                                   |
| ArgoCD     | <http://argocd.localhost>             | `admin` and the initial password above |

Without a tunnel, run `kubectl port-forward -n traefik svc/traefik 8080:80` and send a `Host` header, or use
Tilt's port-forwards.

## Secrets

Secrets are encrypted with SOPS and age (the public key is in `.sops.yaml`) and stored in
`k8s/overlays/<env>/secrets/`. They are never part of a Kustomize build; `make k8s-secrets` decrypts and
applies them.

| Secret                | Namespace    | Keys                           | Used by                                                                            |
| --------------------- | ------------ | ------------------------------ | ---------------------------------------------------------------------------------- |
| `todo-api-secret`     | `todo-app`   | `SECRET_KEY`                   | The API, to sign JWTs                                                              |
| `todo-db-secret`      | `todo-app`   | `username`, `password`         | CNPG, to create the database owner; the API, to build its PgBouncer `DATABASE_URL` |
| `grafana-secret`      | `monitoring` | `ADMIN_USER`, `ADMIN_PASSWORD` | Grafana                                                                            |
| `alertmanager-secret` | `monitoring` | `alertmanager.yml`             | Alertmanager, whose Slack receiver includes the webhook URL                        |

```bash
sops k8s/overlays/dev/secrets/grafana-secret.yaml     # edit; the file is re-encrypted on save
make sops-encrypt                                     # encrypt any new plaintext secret files
```

## Database

CloudNativePG runs PostgreSQL 18 as `todo-db`, with one instance in dev and three in prod. The API connects only
through a PgBouncer `Pooler` in session mode, which asyncpg's prepared statements require.

```bash
kubectl get clusters.postgresql.cnpg.io -n todo-app
kubectl logs -n todo-app deploy/todo-api -c migrate      # Alembic output from the init container
```

## Networking

Every namespace has a `default-deny-all` policy, and each workload gets its own allow policy
(`network-policy.yaml` in each base component and in `k8s/argocd/base/`).

| From                                             | To                                                  | Ports                         |
| ------------------------------------------------ | --------------------------------------------------- | ----------------------------- |
| Outside the cluster, through the load balancer   | Traefik                                             | 8000, 9000                    |
| Traefik                                          | todo-api, Grafana, Prometheus, Alloy, argocd-server | 8000, 3000, 9090, 12345, 8080 |
| todo-api                                         | PgBouncer, and Alloy for traces                     | 5432, 4317                    |
| PgBouncer                                        | PostgreSQL                                          | 5432                          |
| PostgreSQL                                       | PostgreSQL replicas                                 | 5432                          |
| CNPG operator                                    | PostgreSQL                                          | 5432, 8000                    |
| Prometheus                                       | todo-api pods, Alertmanager                         | 8000, 9093                    |
| Alloy                                            | Loki, Tempo                                         | 3100, 4318                    |
| Grafana                                          | Prometheus, Loki, Tempo, Alertmanager               | 9090, 3100, 3200, 9093        |
| Alertmanager                                     | Internet (Slack)                                    | 443                           |
| ArgoCD server and repo server                    | Internet (Git and Helm repositories)                | 443                           |
| Traefik, Alloy, Prometheus, CNPG pods and ArgoCD | Kubernetes API                                      | 443, 8443                     |
| Every pod                                        | CoreDNS                                             | 53 (UDP and TCP)              |

The API server is not a pod that a selector can match, so Kubernetes API egress uses `ipBlock` rules for both
the service CIDR (before DNAT) and the node IP (after DNAT). Internet egress excludes the private RFC 1918
ranges. Policy ports are always the pod's port, not the Service's: the `argocd-server` Service listens on 80,
but the policies allow 8080.

To confirm a denied path, try reaching the API from Grafana, which has no route to it:

```bash
kubectl exec -n monitoring deploy/grafana -- wget -qO- -T 3 http://todo-api.todo-app.svc:8000/health
```

## Autoscaling in prod

`k8s/overlays/prod/hpa-todo-api.yaml` scales `todo-api` between 2 and 4 replicas at 70% CPU. The prod overlay
removes `spec.replicas` from the Deployment so that only the HPA sets the replica count. The HPA needs
metrics-server (`minikube addons enable metrics-server`).

## Validation

```bash
make validate   # runs the four checks below, as CI does
```

| Check               | What it does                                                                                               |
| ------------------- | ---------------------------------------------------------------------------------------------------------- |
| `validate-k8s`      | Builds both overlays and both ArgoCD bootstraps                                                            |
| `validate-schema`   | Validates the overlays with kubeconform in strict mode, against Kubernetes and CRD schemas (CNPG included) |
| `validate-sops`     | Fails if any committed secret is not encrypted                                                             |
| `validate-policies` | Runs the policy unit tests (`conftest verify`), then the policies themselves against both overlays         |

The policies in `policy/` require resource requests and limits (init containers included), readiness and
liveness probes, the standard `app.kubernetes.io` labels and pinned image tags, and they reject NetworkPolicy
rules that allow all traffic.

## Resources

Requests and limits are set in `k8s/base/` and apply to both overlays. With one replica of everything, as in
dev, the stack requests 800m CPU and 2432Mi of memory (limits: 3000m and 4992Mi), plus ArgoCD and the CNPG
operator with their upstream defaults. `make cluster-up` gives minikube 4 CPUs and 8 GiB.

| Component    | CPU request / limit | Memory request / limit |
| ------------ | ------------------- | ---------------------- |
| todo-api     | 100m / 500m         | 256Mi / 512Mi          |
| todo-db      | 250m / 500m         | 512Mi / 1Gi            |
| pgbouncer    | 50m / 200m          | 64Mi / 256Mi           |
| traefik      | 100m / 500m         | 128Mi / 256Mi          |
| prometheus   | 100m / 500m         | 512Mi / 1Gi            |
| grafana      | 50m / 200m          | 256Mi / 512Mi          |
| loki         | 50m / 200m          | 256Mi / 512Mi          |
| tempo        | 50m / 200m          | 256Mi / 512Mi          |
| alloy        | 25m / 100m          | 128Mi / 256Mi          |
| alertmanager | 25m / 100m          | 64Mi / 128Mi           |

## Lab shortcuts

Everything uses plain HTTP, the Prometheus, Alloy and Traefik dashboards have no authentication, and the
monitoring stack stores data in `emptyDir` volumes. Before real use:

- Add TLS with cert-manager and an authentication middleware on the internal ingresses.
- Configure PostgreSQL backups (the CloudNativePG Barman Cloud plugin with object storage).
- Set the Kubernetes API addresses in the NetworkPolicies to the target cluster's service CIDR and API
  endpoint; the current values are minikube's.
- Use persistent storage for Prometheus, Loki and Tempo.

Traefik can read Secrets in every namespace. That is required: its Ingress provider always watches Secrets
for TLS certificates.

## Tearing down

```bash
make k8s-delete      # GitOps: delete the Applications (and what they deployed), then ArgoCD
tilt down            # Tilt
make cluster-down    # delete the whole minikube cluster
```

`make k8s-delete` leaves the CNPG CRDs and the empty `cnpg-system` namespace in place: the chart marks its CRDs
to be kept so databases are never deleted by accident, and ArgoCD does not delete namespaces it created.
`make cluster-down` removes everything.
