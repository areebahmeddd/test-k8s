from textwrap import dedent

import pulumi
import pulumi_kubernetes as k8s

_LABELS = {
    "app.kubernetes.io/part-of": "todo-k8s",
    "app.kubernetes.io/managed-by": "pulumi",
}

# Same routing and message format as the SOPS-encrypted alertmanager-secret.yaml.
_ALERTMANAGER_CONFIG = dedent("""\
    global:
      resolve_timeout: 5m

    route:
      receiver: slack
      group_by: [alertname, severity]
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 1h

    receivers:
      - name: slack
        slack_configs:
          - api_url: __WEBHOOK_URL__
            channel: "#alerts"
            send_resolved: true
            color: '{{ if eq .Status "firing" }}{{ if eq (index .Alerts 0).Labels.severity "critical" }}danger{{ else }}warning{{ end }}{{ else }}good{{ end }}'
            title: '[{{ .Status | toUpper }}] {{ .GroupLabels.alertname }}'
            text: |
              {{ range .Alerts }}
              *Summary:* {{ .Annotations.summary }}
              *Description:* {{ .Annotations.description }}
              *Severity:* {{ .Labels.severity }}
              {{ end }}
""")  # noqa: E501


def _secret(
    name: str,
    namespace: k8s.core.v1.Namespace,
    component: str,
    data: dict[str, pulumi.Input[str]],
    provider: k8s.Provider,
) -> k8s.core.v1.Secret:
    """Create an Opaque Secret with the project's standard labels in the given namespace."""
    return k8s.core.v1.Secret(
        name,
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name=name,
            namespace=namespace.metadata.name,
            labels={**_LABELS, "app.kubernetes.io/component": component},
        ),
        type="Opaque",
        string_data=data,
        opts=pulumi.ResourceOptions(provider=provider),
    )


def deploy_secrets(provider: k8s.Provider) -> list[k8s.core.v1.Secret]:
    """Create the app namespaces and the Secrets the overlays expect, from Pulumi config.

    They are created before ArgoCD, so its first sync finds the Secrets in place instead of
    racing Pulumi to create the namespaces.
    """
    cfg = pulumi.Config()
    todo_app, monitoring = (
        k8s.core.v1.Namespace(
            f"{name}-ns",
            metadata=k8s.meta.v1.ObjectMetaArgs(name=name, labels=_LABELS),
            opts=pulumi.ResourceOptions(provider=provider),
        )
        for name in ("todo-app", "monitoring")
    )

    return [
        _secret(
            "todo-api-secret",
            todo_app,
            "api",
            {"SECRET_KEY": cfg.require_secret("api_secret_key")},
            provider,
        ),
        _secret(
            "todo-db-secret",
            todo_app,
            "database",
            {
                "username": cfg.require_secret("db_username"),
                "password": cfg.require_secret("db_password"),
            },
            provider,
        ),
        _secret(
            "grafana-secret",
            monitoring,
            "dashboard",
            {
                "ADMIN_USER": cfg.require_secret("grafana_admin_user"),
                "ADMIN_PASSWORD": cfg.require_secret("grafana_admin_password"),
            },
            provider,
        ),
        _secret(
            "alertmanager-secret",
            monitoring,
            "alerting",
            {
                "alertmanager.yml": cfg.require_secret("slack_webhook_url").apply(
                    lambda url: _ALERTMANAGER_CONFIG.replace("__WEBHOOK_URL__", url)
                )
            },
            provider,
        ),
    ]
