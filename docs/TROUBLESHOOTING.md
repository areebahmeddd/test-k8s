# Troubleshooting

Start broad, then narrow down:

```bash
kubectl get pods -A | grep -v Running
kubectl get events -A --sort-by=.lastTimestamp | tail -20
kubectl describe pod -n <namespace> <pod>
```

## Cluster

**minikube does not start.** Check that Docker is running with `docker info`, then recreate the cluster with
`minikube delete && make cluster-up`. If Docker has less than about 10 GiB of memory, lower `--memory` in the
`cluster-up` target.

**Pods are stuck in `Pending` or get `OOMKilled`.** `kubectl describe node minikube` shows how much of the node
is already requested. Scale a monitoring component down for a while
(`kubectl scale -n monitoring deploy/loki --replicas=0`) or give minikube more memory.

**`ErrImagePull` for `areebahmeddd/todo-api`.** The image is neither in the registry nor in minikube. Run
`make image` (or let Tilt build it), then `kubectl rollout restart -n todo-app deploy/todo-api`. For the GitOps
path, publish it with `make image-push`.

## Secrets

**`make check-sops` fails.** Either `age.key` is missing, or it is not the key the files were encrypted for.
Compare the public key in `.sops.yaml` with the output of `age-keygen -y age.key`.

**A pod shows `CreateContainerConfigError`.** A Secret it references is missing. Run `make k8s-secrets`, then
check with `kubectl get secrets -n todo-app` and `kubectl get secrets -n monitoring`.

## Deployment

**`kustomize build` fails.** Run `make validate-k8s` to see which kustomization breaks. The usual causes are a
missing file in `resources:` or a patch whose `target` no longer matches anything.

**`make validate-policies` fails.** The message names the resource and the rule it breaks: a missing limit,
probe or label, or an unpinned image tag. The policies and their tests are in `policy/`.

**An ArgoCD Application is `OutOfSync` or `Degraded`.**

```bash
kubectl get applications -n argocd
kubectl describe application -n argocd todo-app             # sync errors and conditions
kubectl logs -n argocd deploy/argocd-repo-server --tail=50  # Git and Kustomize errors
```

ArgoCD deploys what is pushed to the `dev` or `prod` branch, not your working tree. While the `cloudnativepg`
Application is still installing the CNPG CRDs, `todo-app` keeps retrying.

## Routing

**`curl http://todo.localhost` fails.** `kubectl get svc -n traefik traefik` must show an `EXTERNAL-IP`. If it
shows `<pending>`, `minikube tunnel` is not running. To test Traefik without the tunnel:

```bash
kubectl port-forward -n traefik svc/traefik 8080:80
curl -H "Host: todo.localhost" http://localhost:8080/health
```

A Traefik `404 page not found` means no Ingress matches that host; list them with `kubectl get ingress -A`.

**A UI behind Traefik returns `504`.** A NetworkPolicy is blocking the route. Policies match the pod's port,
not the Service's, so check Traefik's egress rule and the target's ingress rule for the pod port.

## Application

**`todo-api` is stuck in `Init:0/1`.** The `migrate` init container is waiting for the database:

```bash
kubectl logs -n todo-app deploy/todo-api -c migrate
kubectl get clusters.postgresql.cnpg.io,pods -n todo-app
```

The CNPG cluster has to be healthy and `todo-db-pooler` ready. The first start can take a few minutes while
images are pulled.

**`todo-api` is in `CrashLoopBackOff`.** Read the crash with
`kubectl logs -n todo-app deploy/todo-api --previous`. A `SECRET_KEY` validation error means
`todo-api-secret` does not contain that key.

**Database connection errors.** The API reaches PostgreSQL only through `todo-db-pooler:5432`, using the
`todo-db-secret` credentials. Check the pooler with `kubectl logs -n todo-app deploy/todo-db-pooler` and the
`allow-pgbouncer` and `allow-postgres` NetworkPolicies.

**The schema looks out of date.** `kubectl exec -n todo-app deploy/todo-api -- alembic current` shows the
applied revision, and `alembic history` lists all of them.

## Observability

**No metrics.** In Prometheus, open _Status_ and then _Targets_: every `todo-api` pod should be `UP`. A failing
target usually means the `allow-prometheus` egress rule or the `allow-todo-api` ingress rule is missing.

**No traces.** Check that the API has `OTEL_EXPORTER_OTLP_ENDPOINT` set, then read
`kubectl logs -n monitoring deploy/alloy` and `kubectl logs -n monitoring deploy/tempo`. New traces can take a
few seconds to appear.

**No logs.** Alloy needs egress to the Kubernetes API and its ClusterRole on `pods` and `pods/log`. Its UI on
port 12345 shows the health of every pipeline component.

**The HPA shows `<unknown>` (prod).** Enable metrics-server with `minikube addons enable metrics-server`.
