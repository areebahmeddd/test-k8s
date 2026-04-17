import pulumi
import pulumi_kubernetes as k8s
from pulumi_kubernetes.helm.v3 import Release, ReleaseArgs, RepositoryOptsArgs

_CNPG_CHART_VERSION = "0.27.1"
_CNPG_REPO = "https://cloudnative-pg.github.io/charts"


def deploy_cnpg(provider: k8s.Provider) -> Release:
    """Install the cloudnative-pg Helm chart into cnpg-system.

    Using a direct Helm Release rather than an ArgoCD Application guarantees
    CNPG CRDs are registered synchronously before ArgoCD syncs the cluster
    overlay, which contains Cluster and Pooler CRs.
    """
    return Release(
        "cloudnative-pg",
        ReleaseArgs(
            chart="cloudnative-pg",
            name="cloudnative-pg",
            namespace="cnpg-system",
            create_namespace=True,
            repository_opts=RepositoryOptsArgs(repo=_CNPG_REPO),
            version=_CNPG_CHART_VERSION,
            values={
                # TODO: increase to 2 on multi-node clusters.
                "replicaCount": 1,
            },
            # atomic purges the release on failure so the cluster is not left
            # in a partial state.
            atomic=True,
            timeout=120,
        ),
        opts=pulumi.ResourceOptions(provider=provider),
    )

