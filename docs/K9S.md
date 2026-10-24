# k9s cheat sheet

```bash
k9s --context minikube --namespace todo-app
```

Type `:` followed by a resource name to switch views, `/` to filter the rows, `?` to list every key available
in the current view, and `Esc` to go back. The header shows the active context and namespace; choosing `0` in
the namespace bar shows all namespaces.

## Views for this project

| Command                        | Shows                                                                        |
| ------------------------------ | ---------------------------------------------------------------------------- |
| `:pods`                        | Pods; filter with `/todo-api`, `/todo-db` and so on                          |
| `:deploy`                      | Deployments: `todo-api`, `todo-db-pooler`, the monitoring stack, Traefik     |
| `:clusters.postgresql.cnpg.io` | CNPG database clusters (`todo-db`)                                           |
| `:poolers.postgresql.cnpg.io`  | PgBouncer poolers                                                            |
| `:applications`                | ArgoCD Applications with their sync and health status                        |
| `:ingress`                     | Ingress hosts (`*.localhost` in dev)                                         |
| `:netpol`                      | NetworkPolicies                                                              |
| `:hpa`                         | The HorizontalPodAutoscaler (prod)                                           |
| `:events`                      | Recent events, the first place to look when something is stuck               |
| `:cm` and `:secrets`           | ConfigMaps and Secrets (`x` decodes a Secret, so avoid it on shared screens) |

## Keys on a selected row

| Key       | Action                                                                         |
| --------- | ------------------------------------------------------------------------------ |
| `Enter`   | Drill down, from a deployment to its pods and from a pod to its containers     |
| `d`       | Describe                                                                       |
| `y`       | Show the YAML                                                                  |
| `l`       | Logs (`0` for all containers, `w` to wrap, `/` to filter, `f` for full screen) |
| `p`       | Logs of the previous container, after a crash                                  |
| `s`       | Shell into a pod's container, or scale a deployment                            |
| `Shift+f` | Port-forward                                                                   |
| `r`       | Restart a deployment's rollout                                                 |
| `e`       | Edit                                                                           |
| `Ctrl+d`  | Delete                                                                         |

## Common tasks

**Watch a rollout.** Open `:deploy`, select `todo-api` and press `Enter`. Old pods terminate as the new ones
become `Running`. A pod stuck at `Init:0/1` is waiting in the `migrate` init container; press `l` and pick
`migrate` to see why.

**Follow a GitOps sync.** Open `:applications` and select `todo-app`. The status moves from `OutOfSync` to
`Progressing` to `Synced` and `Healthy`. `Degraded` means a new pod is failing, so check its logs.

**Read structured logs.** Open `:pods`, select a `todo-api` pod and press `l`. Filter with `/trace_id` to see
requests with tracing context, or with `/WARNING`.

**Query the database.** Open `:pods`, select `todo-db-1` and press `s`, then run:

```bash
psql -d todos -c '\dt'
```

**Port-forward a UI.** Open `:svc`, select `grafana`, press `Shift+f` and enter `3000`.

## Debugging order

1. `:events` for scheduling, image pull and probe failures.
2. `:pods`, then `d`, for container states, restart reasons and missing Secrets.
3. `l` and `p` for the current and previous logs.
4. `:netpol` when a connection times out. Check both the egress side and the ingress side.
