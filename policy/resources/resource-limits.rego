package kubernetes.resources.limits

import future.keywords.contains
import future.keywords.if

# =============================================================================
# Resource Requests and Limits Validation
# Ensures all containers in workload resources declare CPU and memory
# requests + limits so the scheduler can bin-pack pods correctly and
# prevent runaway containers from starving neighbours.
# =============================================================================

workloads := {"Deployment", "StatefulSet", "DaemonSet"}

deny contains msg if {
    workloads[input.kind]
    container := input.spec.template.spec.containers[_]
    not container.resources.requests.cpu
    msg := sprintf("%s '%s' container '%s' is missing CPU request", [input.kind, input.metadata.name, container.name])
}

deny contains msg if {
    workloads[input.kind]
    container := input.spec.template.spec.containers[_]
    not container.resources.requests.memory
    msg := sprintf("%s '%s' container '%s' is missing memory request", [input.kind, input.metadata.name, container.name])
}

deny contains msg if {
    workloads[input.kind]
    container := input.spec.template.spec.containers[_]
    not container.resources.limits.cpu
    msg := sprintf("%s '%s' container '%s' is missing CPU limit", [input.kind, input.metadata.name, container.name])
}

deny contains msg if {
    workloads[input.kind]
    container := input.spec.template.spec.containers[_]
    not container.resources.limits.memory
    msg := sprintf("%s '%s' container '%s' is missing memory limit", [input.kind, input.metadata.name, container.name])
}
