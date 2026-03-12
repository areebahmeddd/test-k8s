package kubernetes.practices.health

import future.keywords.contains
import future.keywords.if

# =============================================================================
# Health Probe Validation
# Ensures Deployments, StatefulSets, and DaemonSets have readiness and
# liveness probes so the scheduler can route traffic and restart unhealthy pods.
# =============================================================================

workloads := {"Deployment", "StatefulSet", "DaemonSet"}

deny contains msg if {
    workloads[input.kind]
    container := input.spec.template.spec.containers[_]
    not container.readinessProbe
    msg := sprintf("%s '%s' container '%s' must have a readinessProbe", [input.kind, input.metadata.name, container.name])
}

deny contains msg if {
    workloads[input.kind]
    container := input.spec.template.spec.containers[_]
    not container.livenessProbe
    msg := sprintf("%s '%s' container '%s' must have a livenessProbe", [input.kind, input.metadata.name, container.name])
}
