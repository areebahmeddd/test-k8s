package kubernetes.practices.labels

import future.keywords.contains
import future.keywords.if

# =============================================================================
# Required Labels Validation
# Enforces standard app.kubernetes.io/* labels on all workload resources.
# Reference: https://kubernetes.io/docs/concepts/overview/working-with-objects/common-labels
# =============================================================================

workloads := {"Deployment", "StatefulSet", "DaemonSet"}

required_labels := [
    "app.kubernetes.io/name",
    "app.kubernetes.io/part-of",
    "app.kubernetes.io/managed-by",
]

deny contains msg if {
    workloads[input.kind]
    missing := missing_labels
    count(missing) > 0
    msg := sprintf("%s '%s' is missing required labels: %v", [input.kind, input.metadata.name, missing])
}

missing_labels contains label if {
    required_labels[_] = label
    not input.metadata.labels[label]
}
