from collections.abc import Sequence
from pathlib import Path

import pulumi
import pulumi_kubernetes as k8s
from pulumi_kubernetes.kustomize.v2 import Directory

# k8s/argocd/ stays the single source of truth for the ArgoCD bootstrap.
_ARGOCD_DIR = Path(__file__).resolve().parents[2] / "k8s" / "argocd"


def deploy_argocd(
    provider: k8s.Provider, overlay: str, depends_on: Sequence[pulumi.Resource]
) -> Directory:
    """Apply k8s/argocd/<overlay>: ArgoCD itself plus the CNPG and todo-app Applications.

    Readiness is not awaited: ArgoCD reconciles its own resources, and its Ingress only
    gets a load-balancer address once Traefik (deployed by ArgoCD) is running.
    """
    return Directory(
        "argocd",
        directory=str(_ARGOCD_DIR / overlay),
        skip_await=True,
        opts=pulumi.ResourceOptions(provider=provider, depends_on=list(depends_on)),
    )
