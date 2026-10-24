# Workloads carry the recommended app.kubernetes.io labels:
# https://kubernetes.io/docs/concepts/overview/working-with-objects/common-labels/
package kubernetes.practices.labels

import data.lib.workloads

required_labels := {
    "app.kubernetes.io/name",
    "app.kubernetes.io/part-of",
    "app.kubernetes.io/managed-by",
}

deny contains msg if {
    workloads.is_workload
    missing := {label | some label in required_labels; not input.metadata.labels[label]}
    count(missing) > 0
    msg := sprintf("%s '%s' is missing required labels: %v", [input.kind, input.metadata.name, missing])
}
