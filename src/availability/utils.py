import logging
from datetime import datetime, timedelta, timezone

from .models import Service
from fromedwin.prometheus import query, query_range

logger = logging.getLogger(__name__)

PROBE_LAST_METRICS = (
    "probe_http_status_code",
    "probe_http_ssl",
    "probe_http_redirects",
    "probe_http_version",
    "probe_tls_version_info",
    "probe_ssl_earliest_cert_expiry",
)


def _service_title(service_id: str) -> str | None:
    try:
        return Service.objects.get(pk=service_id).title
    except Service.DoesNotExist:
        return None


def _ensure_service(services: dict, service_id: str) -> dict:
    if service_id not in services:
        title = _service_title(service_id)
        services[service_id] = {"title": title} if title else {}
    return services[service_id]


def _load_last_probe_fields(label: str, label_value: str) -> dict:
    """Fetch latest probe_* samples for a project or user label."""
    metric_re = "|".join(PROBE_LAST_METRICS)
    promql = f'{{__name__=~"{metric_re}",{label}="{label_value}"}}'
    services: dict = {}

    for series in query(promql):
        metric = series.get("metric", {})
        service_id = metric.get("service")
        field = metric.get("__name__")
        if not service_id or not field:
            continue
        try:
            value = float(series["value"][1])
        except (KeyError, IndexError, TypeError, ValueError):
            continue
        entry = _ensure_service(services, service_id)
        entry[field] = value

    return services


def get_project_stats(project_id, duration=60 * 60):
    """Fetch project probe metrics from Prometheus and bundle them for the UI."""
    services = _load_last_probe_fields("project", str(project_id))

    time_range_stop = datetime.now(timezone.utc) - timedelta(seconds=60)
    time_range_start = time_range_stop - timedelta(seconds=duration)

    for series in query_range(
        f'probe_duration_seconds{{project="{project_id}"}}',
        start=time_range_start,
        end=time_range_stop,
        step="60s",
    ):
        service_id = series.get("metric", {}).get("service")
        if not service_id:
            continue
        entry = _ensure_service(services, service_id)
        points = entry.setdefault("duration_seconds", [])
        for ts, raw in series.get("values", []):
            try:
                value = float(raw) if raw is not None else 0.0
            except (TypeError, ValueError):
                value = 0.0
            timestamp = datetime.fromtimestamp(ts, tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S"
            )
            existing = next((i for i, p in enumerate(points) if p[0] == timestamp), -1)
            if existing == -1:
                points.append([timestamp, value])
            elif points[existing][1] in (None, 0):
                points[existing][1] = value

    return {"services": services}


def get_user_stats(user_id):
    """Fetch latest probe metrics for all services owned by a user."""
    return {"services": _load_last_probe_fields("user", str(user_id))}


def is_project_monitored(project_id):
    """Return True if Prometheus has recent probe_duration_seconds for the project."""
    results = query(f'probe_duration_seconds{{project="{project_id}"}}')
    for series in results:
        try:
            if float(series["value"][1]) > 0:
                return True
        except (KeyError, IndexError, TypeError, ValueError):
            continue
    return False
