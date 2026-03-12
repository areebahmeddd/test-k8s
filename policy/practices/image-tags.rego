package kubernetes.practices.images

import future.keywords.contains
import future.keywords.if

# =============================================================================
# Image Tag Validation
# Denies ':latest' on all images with no exceptions. All container images
# must be pinned to an explicit version tag for reproducibility and security.
# Applies to Deployments, StatefulSets, and DaemonSets.
# =============================================================================

workloads := {"Deployment", "StatefulSet", "DaemonSet"}

deny contains msg if {
    workloads[input.kind]
    container := input.spec.template.spec.containers[_]
    endswith(container.image, ":latest")
    msg := sprintf("%s '%s' container '%s' uses ':latest' — pin to an explicit version tag", [input.kind, input.metadata.name, container.name])
}

deny contains msg if {
    workloads[input.kind]
    container := input.spec.template.spec.containers[_]
    not contains(container.image, ":")
    msg := sprintf("%s '%s' container '%s' has no image tag — explicit tags are required", [input.kind, input.metadata.name, container.name])
}
