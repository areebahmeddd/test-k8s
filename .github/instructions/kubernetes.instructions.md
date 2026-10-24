---
name: Kubernetes
description: Conventions for Kustomize manifests, overlays and the ArgoCD bootstrap.
applyTo: "k8s/**"
---

# Kubernetes

- `k8s/base/<component>/` is shared by every environment. Hosts, replica counts and sizing are patched in
  `k8s/overlays/dev` and `k8s/overlays/prod`. The ArgoCD bootstrap in `k8s/argocd/` follows the same pattern.
- Every container, init containers included, sets CPU and memory requests and limits, a pinned image tag,
  `allowPrivilegeEscalation: false`, `capabilities.drop: [ALL]` and, where possible,
  `readOnlyRootFilesystem: true`. Long-running containers also get readiness and liveness probes. Pods run as
  non-root with `seccompProfile: RuntimeDefault`.
- Label everything with `app.kubernetes.io/name`, `instance`, `component`, `part-of` and `managed-by`;
  `app.kubernetes.io/version` matches the image tag.
- Each namespace denies all traffic by default. A new traffic path needs an egress rule on the client and an
  ingress rule on the server, in each namespace's `network-policy.yaml`. Rules use the pod's port, not the
  Service's. Kubernetes API egress allows both the service CIDR and the minikube node IP.
- Secrets never go into ConfigMaps or plain manifests. Add them SOPS-encrypted under `overlays/<env>/secrets/`.
- Order fields as `apiVersion`, `kind`, `metadata`, `spec`. Inside a container: `name`, `image`,
  `imagePullPolicy`, `command`/`args`, `ports`, `env`/`envFrom`, `volumeMounts`, probes, `resources`,
  `securityContext`.
- Check every change with `make validate`: Kustomize builds, kubeconform with CRD schemas, the SOPS check, and
  the OPA policies with their unit tests.
