# Kubernetes Best Practices

## Resource Requests and Limits (Required on Every Container)

```yaml
resources:
  requests:
    cpu: "100m"
    memory: "128Mi"
  limits:
    cpu: "500m"
    memory: "512Mi"
```

- Never omit both — pods are evicted first under node pressure
- Memory limit close to request (loose limits waste node capacity)
- CPU limits cause throttling even with spare node capacity — be generous or omit if latency matters

## Health Probes (Required)

```yaml
livenessProbe:
  httpGet: { path: /health, port: 8000 }
  initialDelaySeconds: 15
  periodSeconds: 20
  failureThreshold: 3

readinessProbe:
  httpGet: { path: /health, port: 8000 }
  initialDelaySeconds: 5
  periodSeconds: 10
  failureThreshold: 3
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

Add `emptyDir` volume if the app needs a writable path:

```yaml
volumes:
  - name: tmp
    emptyDir: {}
volumeMounts:
  - name: tmp
    mountPath: /tmp
```

## Required Labels

```yaml
labels:
  app.kubernetes.io/name: todo-api
  app.kubernetes.io/instance: todo-api-dev
  app.kubernetes.io/version: "1.2.3"
  app.kubernetes.io/component: api
  app.kubernetes.io/part-of: todo-app
  app.kubernetes.io/managed-by: kustomize
```

## Kustomize Conventions

- Base: `k8s/base/` — no env-specific values
- Overlays: `k8s/overlays/dev/` and `k8s/overlays/prod/`
- Image tag overrides: `images:` transformer in overlay `kustomization.yaml`
- Secrets: never commit to Git — use external-secrets or reference ignored `.env` files

## Field Ordering

```
apiVersion → kind → metadata (name → namespace → labels → annotations) → spec
```
