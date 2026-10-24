# Observability

The stack runs in the `monitoring` namespace. Each component's manifests live in
`k8s/base/monitoring/<component>/`.

| Component    | Image                       | Role                                                | Ports            |
| ------------ | --------------------------- | --------------------------------------------------- | ---------------- |
| Alloy        | `grafana/alloy:v1.21.2`     | Collects pod logs for Loki and traces for Tempo     | 12345 (UI), 4317 |
| Loki         | `grafana/loki:3.7.9`        | Stores logs                                         | 3100             |
| Tempo        | `grafana/tempo:3.1.1`       | Stores traces (single-binary mode)                  | 3200, 4318       |
| Prometheus   | `prom/prometheus:v3.15.1`   | Scrapes API metrics and evaluates alert rules       | 9090             |
| Alertmanager | `prom/alertmanager:v0.34.1` | Sends alerts to Slack                               | 9093             |
| Grafana      | `grafana/grafana:13.2.4`    | Dashboards and exploration across all three signals | 3000             |

## Signal flow

```text
Metrics  todo-api pods  --/metrics, scraped per pod-->  Prometheus  --alerts-->  Alertmanager  -->  Slack
Traces   todo-api pods  --OTLP/gRPC :4317-->  Alloy  --OTLP/HTTP :4318-->  Tempo
Logs     every pod's stdout  --read through the Kubernetes API-->  Alloy  --push-->  Loki

Grafana queries Prometheus, Loki, Tempo and Alertmanager.
```

## Metrics

The API exposes `/metrics` through `prometheus-fastapi-instrumentator`; requests to `/health` and `/metrics`
themselves are not counted. Prometheus finds every `todo-api` pod through Kubernetes service discovery (a
read-only ClusterRole on pods), so each replica is scraped on its own and keeps a `pod` label.

| Metric                          | Labels                                                         |
| ------------------------------- | -------------------------------------------------------------- |
| `http_requests_total`           | `handler`, `method`, `status` (grouped as `2xx`, `4xx`, `5xx`) |
| `http_request_duration_seconds` | `handler`, `method` (histogram, buckets from 50 ms to 10 s)    |

### Alert rules

Defined in `prometheus/configmap.yaml`:

| Alert            | Fires when                                           | For | Severity |
| ---------------- | ---------------------------------------------------- | --- | -------- |
| `APIDown`        | A `todo-api` pod cannot be scraped                   | 1m  | critical |
| `HighErrorRate`  | More than 5% of requests return 5xx over 5 minutes   | 2m  | critical |
| `SlowP99Latency` | A handler's 99th percentile latency exceeds 1 second | 3m  | warning  |

Alertmanager groups alerts by `alertname` and `severity`, posts them to Slack and announces when they resolve.
Its configuration is stored in `alertmanager-secret` because it contains the webhook URL.

## Logs

Alloy reads container logs with `loki.source.kubernetes`, which streams them through the Kubernetes API. No
DaemonSet, host path mounts or privileges are needed. Each stream is labeled with `namespace`, `pod`,
`container`, `app` and `job` (`<namespace>/<container>`):

```logql
{app="todo-api"} | json | levelname="WARNING"
```

The API logs in JSON. When tracing is on, each line also carries `trace_id`, `span_id`, `trace_sampled` and
`service_name`.

## Traces

The `todo-api-config` ConfigMap sets `OTEL_EXPORTER_OTLP_ENDPOINT` to Alloy, which turns tracing on. The API
then records a span for every request (FastAPI) and every query (SQLAlchemy) and exports them over OTLP/gRPC.
Alloy batches the spans and forwards them over OTLP/HTTP to Tempo, which stores them on local disk.

In Grafana, the Tempo datasource links each span to its log lines (matched by trace id) and to the related
Prometheus metrics.

## Grafana

Everything is provisioned from ConfigMaps at startup, so nothing needs to be set up by hand:

- **Datasources** (`configmap-datasources.yaml`): Prometheus (the default), Loki, Tempo and Alertmanager, all
  read-only.
- **Dashboards** (`configmap-provisioning.yaml`, with the JSON files from `dashboards/` added by the Kustomize
  `configMapGenerator`): the _Todo API_ dashboard in the _Todo App_ folder shows pods up, request rate, 5xx
  ratio, p95 and p99 latency, and traffic by handler and status.

Usage reporting, update checks and plugin preinstalls are turned off, so Grafana needs no internet access.

## Retention

All stores use `emptyDir` volumes, so a pod restart loses its data. That is acceptable for a lab. For anything
long-lived, use PersistentVolumeClaims, plus object storage for Loki and Tempo.
