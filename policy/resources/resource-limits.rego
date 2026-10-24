# Every container, including init containers, declares CPU and memory requests and limits
# so the scheduler can place pods and one container cannot starve its neighbors.
package kubernetes.resources.limits

import data.lib.workloads

fields := ["requests.cpu", "requests.memory", "limits.cpu", "limits.memory"]

deny contains msg if {
    some container in workloads.all_containers
    some field in fields
    [kind, resource] := split(field, ".")
    not container.resources[kind][resource]
    msg := sprintf("%s '%s' container '%s' is missing resources.%s", [input.kind, input.metadata.name, container.name, field])
}
