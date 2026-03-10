---
name: Kubernetes Best Practices
description: "Use when writing or reviewing Kubernetes YAML manifests, Kustomize overlays, or Helm templates. Covers resource limits, health probes, security contexts, labels, PodDisruptionBudgets, and production readiness. Triggers on: k8s manifest, deployment yaml, kubernetes config, kustomize overlay, resource limits, health probe, security context."
applyTo: "k8s/**"
---

# Kubernetes Best Practices

## Resource Requests and Limits (Required on Every Container)

```yaml
resources:
  requests: # Scheduler guarantee — what K8s reserves on the node
    cpu: "100m"
    memory: "128Mi"
  limits: # Hard cap — OOMKill if memory exceeded; throttle if CPU exceeded
    cpu: "500m"
    memory: "512Mi"
```

Rules:

- Never set limits without requests
- Never omit both — pods are evicted first under node pressure
- Set memory limit close to request (loose limits waste node capacity)
- CPU limits cause throttling even when node has spare — be generous or omit CPU limit if latency matters

## Health Probes (Required)

```yaml
livenessProbe: # Restart container if this fails (deadlock detection)
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 15
  periodSeconds: 20
  failureThreshold: 3

readinessProbe: # Remove pod from Service endpoints until ready
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
  failureThreshold: 3

startupProbe: # For slow-starting pods — disables liveness until started
  httpGet:
    path: /health
    port: 8000
  failureThreshold: 30
  periodSeconds: 10
```

## Security Context (Required)

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  seccompProfile:
    type: RuntimeDefault
  capabilities:
    drop: ["ALL"]
```

If the app needs a writable directory, add a `tmpfs` volume:

```yaml
volumes:
  - name: tmp
    emptyDir: {}
volumeMounts:
  - name: tmp
    mountPath: /tmp
```

## Required Labels on All Resources

```yaml
labels:
  app.kubernetes.io/name: todo-api
  app.kubernetes.io/instance: todo-api-dev
  app.kubernetes.io/component: api # api | db | worker | cache
  app.kubernetes.io/version: "1.2.3" # image tag
  app.kubernetes.io/managed-by: kustomize
```

## Kustomize Conventions (this project)

- Base manifests: `k8s/base/` — no env-specific values
- Env patches: `k8s/overlays/dev/` and `k8s/overlays/prod/`
- Image tag overrides: use `images:` transformer in overlay `kustomization.yaml`
- Secrets: never commit to Git — reference `.env` files listed in `.gitignore`, or use external-secrets operator
- `namePrefix` / `nameSuffix` to namespace resource names between envs

## Production Checklist

- [ ] Resource `requests` AND `limits` set on every container
- [ ] `livenessProbe` and `readinessProbe` set
- [ ] `runAsNonRoot: true` set
- [ ] `allowPrivilegeEscalation: false` set
- [ ] `readOnlyRootFilesystem: true` set (with tmpfs if needed)
- [ ] `capabilities.drop: ["ALL"]` set
- [ ] No secrets in ConfigMaps or inline `env.value` fields
- [ ] `PodDisruptionBudget` defined for critical services (minimum 1 available)
- [ ] `topologySpreadConstraints` set for deployments with >1 replica (HA across zones)
- [ ] `terminationGracePeriodSeconds` set to allow graceful shutdown
