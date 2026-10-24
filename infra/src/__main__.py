import pulumi
import pulumi_kubernetes as k8s
from argocd import deploy_argocd
from cluster_secrets import deploy_secrets

overlay = pulumi.Config().get("overlay") or "dev"

# Uses the current kubeconfig context, like kubectl.
provider = k8s.Provider("k8s")

# Secrets first, so ArgoCD's first sync finds them in place.
secrets = deploy_secrets(provider)
deploy_argocd(provider, overlay, depends_on=secrets)

pulumi.export("overlay", overlay)
