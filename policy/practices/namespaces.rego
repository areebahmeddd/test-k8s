# Namespaced resources must name their namespace explicitly. Without one, a resource lands in
# whatever namespace the deploy happens to target (usually "default"), where it silently does nothing.
package kubernetes.practices.namespaces

cluster_scoped := {
    "ClusterRole",
    "ClusterRoleBinding",
    "CustomResourceDefinition",
    "IngressClass",
    "Namespace",
}

deny contains msg if {
    not cluster_scoped[input.kind]
    not input.metadata.namespace
    msg := sprintf("%s '%s' must set metadata.namespace", [input.kind, input.metadata.name])
}
