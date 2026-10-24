package lib.workloads

kinds := {"Deployment", "StatefulSet", "DaemonSet"}

is_workload if kinds[input.kind]

# Long-running containers: probes apply to these.
containers contains c if {
    is_workload
    some c in input.spec.template.spec.containers
}

# Every container that runs, including init containers: images and resources apply to these.
all_containers contains c if some c in containers

all_containers contains c if {
    is_workload
    some c in input.spec.template.spec.initContainers
}
