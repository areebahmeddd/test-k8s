package kubernetes.practices.images

import data.lib.workloads

deny contains msg if {
    some container in workloads.all_containers
    endswith(container.image, ":latest")
    msg := sprintf("%s '%s' container '%s' uses ':latest'; pin an explicit version tag", [input.kind, input.metadata.name, container.name])
}

deny contains msg if {
    some container in workloads.all_containers
    not contains(container.image, ":")
    msg := sprintf("%s '%s' container '%s' has no image tag; pin an explicit version tag", [input.kind, input.metadata.name, container.name])
}
