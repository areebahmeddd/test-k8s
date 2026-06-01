import subprocess
from pathlib import Path

import pulumi
import pulumi_kubernetes as k8s
from pulumi_kubernetes.yaml.v2 import ConfigGroup

# Absolute path to k8s/argocd/, computed from this file's location.
_ARGOCD_DIR: Path = Path(__file__).resolve().parent.parent.parent / "k8s" / "argocd"


def _render_kustomization(kustomize_dir: Path) -> str:
    result = subprocess.run(
        ["kustomize", "build", str(kustomize_dir)],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return result.stdout


def deploy_argocd(provider: k8s.Provider) -> ConfigGroup:
    """Render k8s/argocd/ with Kustomize and apply all resources.

    k8s/argocd/ is the single source of truth and is not duplicated here.
    Resources include: argocd namespace, ArgoCD v3.3.8 install, server.insecure
    patch, sops-age Secret, repo-server SOPS volume, Ingress, NetworkPolicy,
    and todo-app-dev/prod Application CRDs.
    """
    rendered_yaml = _render_kustomization(_ARGOCD_DIR)
    return ConfigGroup(
        "argocd",
        yaml=rendered_yaml,
        opts=pulumi.ResourceOptions(provider=provider),
    )
