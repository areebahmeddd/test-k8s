# Monitoring

The monitoring stack covers all three pillars of observability: metrics, logs, and traces. Each pillar has a dedicated storage backend. Grafana is the single interface that queries all three.

## Stack Overview

| Service      | Image                       | Role                                    | Port |
| ------------ | --------------------------- | --------------------------------------- | ---- |
| Prometheus   | `prom/prometheus:v3.10.0`   | Metrics collection and alerting         | 9090 |
| Alertmanager | `prom/alertmanager:v0.31.0` | Alert routing and notification delivery | 9093 |
| Grafana      | `grafana/grafana:12.4.0`    | Unified dashboard UI                    | 3000 |
| Loki         | `grafana/loki:3.5.0`        | Log storage and querying                | 3100 |
| Alloy        | `grafana/alloy:v1.14.0`     | Log collection and trace ingestion      | 4317 |
| Tempo        | `grafana/tempo:2.8.0`       | Trace storage and querying              | 3200 |

## Signal Flow

```
                      ┌──────────────────────────────────┐
                      │           GRAFANA :3000          │
                      │  (unified UI for all 3 pillars)  │
                      └────────┬──────────┬──────────┬───┘
                               │          │          │
                        metrics│          │ logs     │ traces
                               │          │          │
                      ┌────────▼──┐  ┌────▼────┐  ┌─▼──────┐
                      │PROMETHEUS │  │  LOKI   │  │ TEMPO  │
                      │  :9090    │  │  :3100  │  │ :3200  │
                      └────┬──────┘  └────▲────┘  └────▲───┘
                           │              │             │
                      fires│          push│         push│
                      alert│          logs│       traces│
                      ┌─────▼──────┐  ┌───┴─────────────┴──┐
                      │ALERTMANAGER│  │        ALLOY       │
                      │  :9093     │  │logs  :—  otlp :4317│
                      └────────────┘  └────────────────────┘
                                                  │receives traces
                                             ┌────▼────┐
                                             │   API   │
                                             │  :8000  │
                                             └─────────┘
```

Alloy collects logs from all Kubernetes pods via the Kubernetes API (`loki.source.kubernetes`) and receives traces from the API over gRPC OTLP (port 4317). It requires no node filesystem access and runs as a single Deployment.

## Configuration Files

All configuration lives under `k8s/base/monitoring/`.

```
k8s/base/monitoring/
  alloy/
    configmap.yaml       # River (Alloy) pipeline config
    deployment.yaml
    service.yaml
    ingress.yaml
    clusterrole.yaml
    clusterrolebinding.yaml
    serviceaccount.yaml
  grafana/
    configmap-datasources.yaml
    configmap-provisioning.yaml
    dashboards/
      api-metrics.json
    deployment.yaml
    service.yaml
    ingress.yaml
  loki/
    configmap.yaml
    deployment.yaml
    service.yaml
  prometheus/
    configmap.yaml       # prometheus.yml + alert-rules.yml
    deployment.yaml
    service.yaml
    ingress.yaml
  alertmanager/
    deployment.yaml
    service.yaml
  tempo/
    configmap.yaml
    deployment.yaml
    service.yaml
```

## Prometheus

**Config:** `monitoring/prometheus/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093

rule_files:
  - /etc/prometheus/alert-rules.yml

scrape_configs:
  - job_name: todo-api
    static_configs:
      - targets:
          - api:8000
    metrics_path: /metrics
```

Prometheus pulls metrics from `http://api:8000/metrics` every 15 seconds. The API exposes this endpoint via the OpenTelemetry Prometheus exporter. The `alertmanager` target is where Prometheus forwards firing alerts.

**Alert rules:** `monitoring/prometheus/alert-rules.yml`

Three rules are defined:

| Rule             | Expression                              | Fires after | Severity |
| ---------------- | --------------------------------------- | ----------- | -------- |
| `APIDown`        | `up{job="todo-api"} == 0`               | 1 minute    | critical |
| `HighErrorRate`  | 5xx rate > 5% of all requests over 5m   | 2 minutes   | critical |
| `SlowP99Latency` | p99 latency > 1s on any handler over 5m | 3 minutes   | warning  |

`up` is a synthetic metric Prometheus sets to `1` on a successful scrape and `0` on failure.

`HighErrorRate` uses `http_request_duration_seconds_count` labelled by `status`.

`SlowP99Latency` uses `histogram_quantile(0.99, ...)` over `http_request_duration_seconds_bucket` grouped by handler.

The `for` durations prevent single-blip noise from triggering notifications.

## Alertmanager

**Config:** `monitoring/alertmanager/alertmanager.yml`

```yaml
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
      - api_url: $SLACK_WEBHOOK_URL
        channel: "#alerts"
        send_resolved: true
```

Alertmanager receives alerts from Prometheus and routes them to Slack.

`group_wait: 30s` — waits 30 seconds before sending the first notification, allowing related alerts to arrive and be bundled into one message.

`group_interval: 5m` — sends an update every 5 minutes while the group is still firing.

`repeat_interval: 1h` — re-sends an unresolved alert every hour.

`send_resolved: true` — sends a recovery notification when the condition clears.

The message colour is templated: red for critical, yellow for warning, green for resolved.

### Webhook URL

The Slack webhook URL is sensitive and must never be committed to the repository. It is passed via the environment variable `SLACK_WEBHOOK_URL`.

In Docker: set it in a `.env` file at the project root.

In Kubernetes: store it in a Secret and inject it as an environment variable into the Alertmanager pod. See the Kubernetes setup section for details.

## Loki

**Config:** `monitoring/loki/loki-config.yml`

```yaml
auth_enabled: false

server:
  http_listen_port: 3100
  log_level: warn

common:
  instance_addr: 127.0.0.1
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory

query_range:
  results_cache:
    cache:
      embedded_cache:
        enabled: true
        max_size_mb: 100

schema_config:
  configs:
    - from: 2020-10-24
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h
```

`auth_enabled: false` runs Loki in single-tenant mode — no `X-Scope-OrgID` header required.

`log_level: warn` suppresses the verbose info logs Loki emits on every query.

`store: tsdb` with `schema: v13` is the current recommended schema. Earlier schemas used BoltDB which is deprecated. The TSDB index and log chunks are stored on the local filesystem, mounted to the `loki_data` volume.

`embedded_cache` keeps up to 100MB of recent query results in memory to speed up repeated queries in Grafana.

`replication_factor: 1` and `store: inmemory` are correct for a single-instance deployment. No external Consul or etcd is needed.

## Alloy

**Config:** `k8s/base/monitoring/alloy/configmap.yaml` (key: `config.alloy`)

Alloy uses the River configuration language. The pipeline has two independent signal paths:

### Logs pipeline

```alloy
discovery.kubernetes "pod" {
  role = "pod"
}

discovery.relabel "pod_logs" {
  targets = discovery.kubernetes.pod.targets

  rule { source_labels = ["__meta_kubernetes_namespace"]            target_label = "namespace" }
  rule { source_labels = ["__meta_kubernetes_pod_name"]             target_label = "pod" }
  rule { source_labels = ["__meta_kubernetes_pod_container_name"]   target_label = "container" }
  rule { source_labels = ["__meta_kubernetes_pod_label_app_kubernetes_io_name"] target_label = "app" }
  rule {
    source_labels = ["__meta_kubernetes_namespace", "__meta_kubernetes_pod_container_name"]
    target_label  = "job"
    separator     = "/"
  }
}

loki.source.kubernetes "pod_logs" {
  targets    = discovery.relabel.pod_logs.output
  forward_to = [loki.write.loki.receiver]
}

loki.write "loki" {
  endpoint { url = "http://loki:3100/loki/api/v1/push" }
}
```

`loki.source.kubernetes` tails pod logs via the Kubernetes API — no DaemonSet, no `hostPath` mounts, and no privileged container required. A single Alloy Deployment serves the whole cluster.

The `discovery.relabel` rules map Kubernetes pod metadata to Loki stream labels. In Grafana, logs can be queried with selectors like `{namespace="todo-app"}` or `{app="todo-api"}`.

### Traces pipeline

```alloy
otelcol.receiver.otlp "default" {
  grpc { endpoint = "0.0.0.0:4317" }
  output { traces = [otelcol.processor.batch.default.input] }
}

otelcol.processor.batch "default" {
  output { traces = [otelcol.exporter.otlphttp.tempo.input] }
}

otelcol.exporter.otlphttp "tempo" {
  client { endpoint = "http://tempo:4318" }
}
```

Alloy receives traces from the API over gRPC OTLP (port 4317), batches them, and forwards to Tempo over HTTP OTLP (port 4318). The `batch` processor reduces the number of HTTP calls to Tempo by grouping spans before export.

The API is configured with `OTEL_EXPORTER_OTLP_ENDPOINT=alloy.monitoring.svc.cluster.local:4317`.

## Tempo

**Config:** `monitoring/tempo/tempo-config.yml`

```yaml
server:
  http_listen_port: 3200
  log_level: warn

distributor:
  receivers:
    otlp:
      protocols:
        http:
          endpoint: 0.0.0.0:4318

ingester:
  max_block_duration: 5m

storage:
  trace:
    backend: local
    local:
      path: /var/tempo/traces
    wal:
      path: /var/tempo/wal
```

Tempo runs in single-binary mode (`all` target), which starts all components — distributor, ingester, querier, compactor — in a single process. This is the correct mode for a single-node deployment.

`distributor.receivers.otlp.http.endpoint: 0.0.0.0:4318` — listens on all network interfaces so the OTel Collector can reach it across the Docker bridge network. The default (`localhost:4318`) would reject cross-container connections.

`max_block_duration: 5m` overrides the 30-minute default. Spans flow: OTel Collector → Tempo distributor → WAL on disk → in-memory ingester → flushed to parquet blocks every 5 minutes. Grafana can query both in-memory and flushed blocks.

The WAL at `/var/tempo/wal` ensures spans are not lost if Tempo restarts mid-block.

`backend: local` stores trace blocks on the local filesystem, mounted to the `tempo_data` volume.

## Grafana

**Datasources:** `monitoring/grafana/provisioning/datasources/datasources.yml`

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    uid: prometheus
    url: http://prometheus:9090
    isDefault: true
    editable: false

  - name: Loki
    type: loki
    uid: loki
    url: http://loki:3100
    editable: false

  - name: Tempo
    type: tempo
    uid: tempo
    url: http://tempo:3200
    editable: false
    jsonData:
      tracesToLogs:
        datasourceUid: loki
        filterByTraceID: true
```

All three data sources are provisioned automatically at startup. No manual Grafana configuration is needed.

`editable: false` prevents saving changes through the UI — the config files remain the single source of truth.

`tracesToLogs` enables cross-pillar correlation: in the Tempo trace view, a button appears that jumps to Loki filtered by the current trace ID. This works because the API's OTel SDK injects the trace ID into log lines.

`isDefault: true` on Prometheus means new Grafana panels default to it.

**Dashboards:** `monitoring/grafana/provisioning/dashboards/dashboards.yml`

```yaml
apiVersion: 1

providers:
  - name: todo-dashboards
    orgId: 1
    folder: Todo App
    type: file
    disableDeletion: true
    updateIntervalSeconds: 10
    options:
      path: /var/lib/grafana/dashboards
```

Every `.json` file under `monitoring/grafana/dashboards/` is imported automatically. Currently one dashboard is included: `api-metrics.json`, which displays HTTP request rates, error rates, and latency percentiles for the API.

Grafana stores its own data (users, preferences, saved state) in the `grafana_data` volume.

## Access

| Interface    | URL                     | Notes                                |
| ------------ | ----------------------- | ------------------------------------ |
| Grafana      | `http://localhost:3000` | Default credentials: admin / admin   |
| Prometheus   | `http://localhost:9090` | Query interface and alert state      |
| Alertmanager | `http://localhost:9093` | Active alerts and silence management |
| Loki         | `http://localhost:3100` | No browser UI — query via Grafana    |
| Tempo        | `http://localhost:3200` | No browser UI — query via Grafana    |
