"""Small Prometheus HTTP API client; live metric failures remain unavailable."""
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


class PrometheusUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class PrometheusSample:
    value: float
    observed_at: datetime


class PrometheusClient:
    def __init__(self, base_url: str, query: str, timeout_seconds: float = 3.0,
                 max_age_seconds: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.query = query
        self.timeout_seconds = timeout_seconds
        self.max_age_seconds = max_age_seconds

    @classmethod
    def from_env(cls) -> "PrometheusClient":
        return cls(
            os.getenv("PROMETHEUS_URL", "http://prometheus-server.monitoring.svc.cluster.local"),
            os.getenv("PROMETHEUS_P95_QUERY", "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[1m])) by (le)) * 1000"),
            float(os.getenv("PROMETHEUS_TIMEOUT_SECONDS", "3")),
            float(os.getenv("MAX_METRIC_AGE_SECONDS", "30")),
        )

    def query_p95(self, now: datetime | None = None) -> PrometheusSample:
        url = f"{self.base_url}/api/v1/query?{urlencode({'query': self.query})}"
        try:
            with urlopen(url, timeout=self.timeout_seconds) as response:
                if response.status != 200:
                    raise PrometheusUnavailable(f"Prometheus HTTP status {response.status}")
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise PrometheusUnavailable(f"Prometheus query failed: {exc}") from exc
        if not isinstance(payload, dict) or payload.get("status") != "success":
            raise PrometheusUnavailable("Prometheus returned an unsuccessful or malformed response")
        data = payload.get("data")
        results = data.get("result") if isinstance(data, dict) else None
        if not isinstance(results, list) or len(results) != 1:
            raise PrometheusUnavailable("Prometheus query must return exactly one P95 series")
        sample = results[0].get("value") if isinstance(results[0], dict) else None
        if not isinstance(sample, list) or len(sample) != 2:
            raise PrometheusUnavailable("Prometheus returned a malformed sample")
        try:
            timestamp = datetime.fromtimestamp(float(sample[0]), tz=timezone.utc)
            value = float(sample[1])
        except (TypeError, ValueError, OverflowError, OSError) as exc:
            raise PrometheusUnavailable("Prometheus sample was not numeric") from exc
        current = now or datetime.now(timezone.utc)
        age = (current - timestamp).total_seconds()
        if not math.isfinite(value) or value < 0 or age < -5 or age > self.max_age_seconds:
            raise PrometheusUnavailable("Prometheus sample was invalid or stale")
        return PrometheusSample(value, timestamp)
