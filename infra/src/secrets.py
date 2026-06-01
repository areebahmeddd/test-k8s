from textwrap import dedent

import pulumi
import pulumi_kubernetes as k8s
from pulumi_kubernetes.yaml.v2 import ConfigGroup

# Labels applied to every resource created here.
_LABELS: dict[str, str] = {
    "app.kubernetes.io/part-of": "todo-k8s",
    "app.kubernetes.io/managed-by": "pulumi",
}


def deploy_secrets(
    provider: k8s.Provider,
    argocd_group: ConfigGroup,
) -> list[k8s.core.v1.Secret]:
    """Create application namespaces and K8s Secrets from Pulumi config.

    Namespaces are pre-created so secrets land before ArgoCD's first sync.
    Both Pulumi and ArgoCD use server-side apply with separate field managers,
    so dual ownership is safe and idempotent.
    """
    cfg = pulumi.Config()

    # Namespaces are created after ArgoCD is deployed to prevent a race where
    # ArgoCD and Pulumi both attempt to create the same namespace simultaneously.
    ns_opts = pulumi.ResourceOptions(provider=provider, depends_on=[argocd_group])

    todo_app_ns = k8s.core.v1.Namespace(
        "todo-app-ns",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name="todo-app",
            labels={
                **_LABELS,
                "kubernetes.io/metadata.name": "todo-app",
            },
        ),
        opts=ns_opts,
    )

    monitoring_ns = k8s.core.v1.Namespace(
        "monitoring-ns",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name="monitoring",
            labels={
                **_LABELS,
                "kubernetes.io/metadata.name": "monitoring",
            },
        ),
        opts=ns_opts,
    )

    todo_app_opts = pulumi.ResourceOptions(
        provider=provider,
        depends_on=[todo_app_ns],
    )
    monitoring_opts = pulumi.ResourceOptions(
        provider=provider,
        depends_on=[monitoring_ns],
    )

    todo_api_secret = k8s.core.v1.Secret(
        "todo-api-secret",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name="todo-api-secret",
            namespace="todo-app",
            labels={
                **_LABELS,
                "app.kubernetes.io/name": "todo-api",
                "app.kubernetes.io/instance": "todo-api",
                "app.kubernetes.io/component": "api",
            },
        ),
        type="Opaque",
        string_data={
            "DATABASE_URL": cfg.require_secret("api_database_url"),
            "SECRET_KEY": cfg.require_secret("api_secret_key"),
        },
        opts=todo_app_opts,
    )

    todo_db_secret = k8s.core.v1.Secret(
        "todo-db-secret",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name="todo-db-secret",
            namespace="todo-app",
            labels={
                **_LABELS,
                "app.kubernetes.io/name": "todo-db",
                "app.kubernetes.io/instance": "todo-db",
                "app.kubernetes.io/component": "database",
            },
        ),
        type="Opaque",
        string_data={
            "username": cfg.require_secret("db_username"),
            "password": cfg.require_secret("db_password"),
        },
        opts=todo_app_opts,
    )

    grafana_secret = k8s.core.v1.Secret(
        "grafana-secret",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name="grafana-secret",
            namespace="monitoring",
            labels={
                **_LABELS,
                "app.kubernetes.io/name": "grafana",
                "app.kubernetes.io/instance": "grafana",
                "app.kubernetes.io/component": "dashboard",
            },
        ),
        type="Opaque",
        string_data={
            "ADMIN_USER": cfg.require_secret("grafana_admin_user"),
            "ADMIN_PASSWORD": cfg.require_secret("grafana_admin_password"),
        },
        opts=monitoring_opts,
    )

    alertmanager_secret = k8s.core.v1.Secret(
        "alertmanager-secret",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name="alertmanager-secret",
            namespace="monitoring",
            labels={
                **_LABELS,
                "app.kubernetes.io/name": "alertmanager",
                "app.kubernetes.io/instance": "alertmanager",
                "app.kubernetes.io/component": "alerting",
            },
        ),
        type="Opaque",
        string_data={
            "alertmanager.yml": cfg.require_secret("slack_webhook_url").apply(
                _render_alertmanager_config
            ),
        },
        opts=monitoring_opts,
    )

    return [todo_api_secret, todo_db_secret, grafana_secret, alertmanager_secret]


def _render_alertmanager_config(slack_webhook_url: str) -> str:
    """Render alertmanager.yml with the given Slack webhook URL.

    The webhook URL is injected via str.replace so Go template syntax ({{ }})
    in the config body is preserved without f-string escaping.
    """
    # Mirrors monitoring/alertmanager/alertmanager.yml; keep in sync.
    template = dedent("""\
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
    """)
    return template.replace("__WEBHOOK_URL__", slack_webhook_url)
