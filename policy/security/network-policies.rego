# An empty ingress or egress rule ({}) matches all traffic and silently defeats the
# namespace's default-deny policy.
package kubernetes.security.network

deny contains msg if {
    input.kind == "NetworkPolicy"
    some rule in input.spec.ingress
    rule == {}
    msg := sprintf("NetworkPolicy '%s' allows all ingress traffic; specify explicit rules", [input.metadata.name])
}

deny contains msg if {
    input.kind == "NetworkPolicy"
    some rule in input.spec.egress
    rule == {}
    msg := sprintf("NetworkPolicy '%s' allows all egress traffic; specify explicit rules", [input.metadata.name])
}
