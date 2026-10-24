package policies_test

import data.kubernetes.practices.health
import data.kubernetes.practices.images
import data.kubernetes.practices.labels
import data.kubernetes.practices.namespaces
import data.kubernetes.resources.limits
import data.kubernetes.security.network

resources := {
    "requests": {"cpu": "100m", "memory": "128Mi"},
    "limits": {"cpu": "500m", "memory": "256Mi"},
}

probe := {"httpGet": {"path": "/health", "port": 8000}}

compliant := {
    "kind": "Deployment",
    "metadata": {"name": "api", "namespace": "app", "labels": {
        "app.kubernetes.io/name": "api",
        "app.kubernetes.io/part-of": "todo-k8s",
        "app.kubernetes.io/managed-by": "kustomize",
    }},
    "spec": {"template": {"spec": {
        "initContainers": [{"name": "migrate", "image": "api:1.0.0", "resources": resources}],
        "containers": [{
            "name": "api",
            "image": "api:1.0.0",
            "resources": resources,
            "readinessProbe": probe,
            "livenessProbe": probe,
        }],
    }}},
}

# Also covers init containers, which need resources and tags but no probes.
test_compliant_deployment_passes if {
    count(health.deny) == 0 with input as compliant
    count(images.deny) == 0 with input as compliant
    count(labels.deny) == 0 with input as compliant
    count(limits.deny) == 0 with input as compliant
    count(namespaces.deny) == 0 with input as compliant
}

test_missing_probes_denied if {
    bad := json.patch(compliant, [
        {"op": "remove", "path": "/spec/template/spec/containers/0/readinessProbe"},
        {"op": "remove", "path": "/spec/template/spec/containers/0/livenessProbe"},
    ])
    count(health.deny) == 2 with input as bad
}

test_latest_and_untagged_images_denied if {
    latest := json.patch(compliant, [{"op": "replace", "path": "/spec/template/spec/containers/0/image", "value": "api:latest"}])
    untagged := json.patch(compliant, [{"op": "replace", "path": "/spec/template/spec/initContainers/0/image", "value": "api"}])
    count(images.deny) == 1 with input as latest
    count(images.deny) == 1 with input as untagged
}

test_missing_labels_denied if {
    bad := json.patch(compliant, [{"op": "replace", "path": "/metadata/labels", "value": {}}])
    count(labels.deny) == 1 with input as bad
}

test_missing_init_container_limits_denied if {
    bad := json.patch(compliant, [{"op": "remove", "path": "/spec/template/spec/initContainers/0/resources/limits"}])
    count(limits.deny) == 2 with input as bad
}

test_missing_namespace_denied if {
    hpa := {"kind": "HorizontalPodAutoscaler", "metadata": {"name": "api"}, "spec": {}}
    count(namespaces.deny) == 1 with input as hpa
}

test_cluster_scoped_resources_need_no_namespace if {
    count(namespaces.deny) == 0 with input as {"kind": "ClusterRole", "metadata": {"name": "reader"}}
}

test_non_workloads_ignored if {
    service := {"kind": "Service", "metadata": {"name": "api"}, "spec": {}}
    count(health.deny) == 0 with input as service
    count(labels.deny) == 0 with input as service
}

test_allow_all_network_policy_rules_denied if {
    policy := {
        "kind": "NetworkPolicy",
        "metadata": {"name": "open"},
        "spec": {"ingress": [{}], "egress": [{}]},
    }
    count(network.deny) == 2 with input as policy
}

test_scoped_network_policy_rules_pass if {
    policy := {
        "kind": "NetworkPolicy",
        "metadata": {"name": "scoped"},
        "spec": {"ingress": [{"ports": [{"port": 8000}]}]},
    }
    count(network.deny) == 0 with input as policy
}
