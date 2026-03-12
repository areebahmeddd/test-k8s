package kubernetes.security.network

import future.keywords.contains
import future.keywords.if

# =============================================================================
# Network Policy Validation
# Enforces that NetworkPolicy rules are never empty (which would allow all
# traffic). Deployment-level network isolation is managed separately.
# =============================================================================

deny contains msg if {
    input.kind == "NetworkPolicy"
    input.spec.ingress[_] == {}
    msg := sprintf("NetworkPolicy '%s' allows all ingress traffic — specify explicit rules", [input.metadata.name])
}

deny contains msg if {
    input.kind == "NetworkPolicy"
    input.spec.egress[_] == {}
    msg := sprintf("NetworkPolicy '%s' allows all egress traffic — specify explicit rules", [input.metadata.name])
}
