import pulumi
import pulumi_kubernetes as k8s

from cnpg import deploy_cnpg
from argocd import deploy_argocd
from secrets import deploy_secrets

# kubeconfig context is read from the environment (same as kubectl).
provider = k8s.Provider("k8s")

# CNPG and ArgoCD deploy in parallel; both are independent of each other.
# Secrets depend on argocd_group so application namespaces exist before secrets are applied.
cnpg_release = deploy_cnpg(provider)
argocd_group = deploy_argocd(provider)
secrets = deploy_secrets(provider, argocd_group=argocd_group)

cfg = pulumi.Config()
pulumi.export("overlay", cfg.get("overlay", "dev"))
pulumi.export("cnpg_release_name", cnpg_release.name)
