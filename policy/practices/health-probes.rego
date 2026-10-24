# Long-running containers need readiness and liveness probes so traffic is only routed
# to ready pods and hung containers are restarted.
package kubernetes.practices.health

import data.lib.workloads

deny contains msg if {
    some container in workloads.containers
    not container.readinessProbe
    msg := sprintf("%s '%s' container '%s' must have a readinessProbe", [input.kind, input.metadata.name, container.name])
}

deny contains msg if {
    some container in workloads.containers
    not container.livenessProbe
    msg := sprintf("%s '%s' container '%s' must have a livenessProbe", [input.kind, input.metadata.name, container.name])
}
