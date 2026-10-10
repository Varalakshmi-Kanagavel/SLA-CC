import logging
import requests
from typing import Optional

logger = logging.getLogger("AdaptiveController.Prometheus")

class PrometheusMetricsClient:
    """
    Connects to live Prometheus HTTP API to query real-time P95 latency and resource utilization.
    """
    def __init__(self, base_url: str = "http://prometheus-server.monitoring.svc.cluster.local"):
        self.base_url = base_url.rstrip("/")

    def _query_instant(self, query: str) -> Optional[float]:
        url = f"{self.base_url}/api/v1/query"
        try:
            resp = requests.get(url, params={"query": query}, timeout=4.0)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "success":
                results = data.get("data", {}).get("result", [])
                if results and len(results) > 0:
                    # Result format: [timestamp, "value_string"]
                    return float(results[0]["value"][1])
            return None
        except Exception as e:
            logger.warning(f"Failed to query Prometheus: {e} | Query: {query}")
            return None

    def get_p95_latency_ms(self, endpoint: str = "/workload", window: str = "1m") -> Optional[float]:
        """Calculates P95 response duration in milliseconds from histogram buckets."""
        query = (
            f"histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{{endpoint='{endpoint}'}}[{window}])) by (le)) * 1000"
        )
        val = self._query_instant(query)
        return round(val, 2) if val is not None else None

    def get_cpu_utilization(self, container_name: str = "webapp", window: str = "1m") -> Optional[float]:
        """Calculates current container CPU utilization percentage relative to its request."""
        query = (
            f"sum(rate(container_cpu_usage_seconds_total{{container='{container_name}'}}[{window}])) / "
            f"sum(kube_pod_container_resource_requests{{resource='cpu', container='{container_name}'}}) * 100"
        )
        val = self._query_instant(query)
        return round(val, 2) if val is not None else None

    def get_request_rate(self, endpoint: str = "/workload", window: str = "1m") -> Optional[float]:
        """Calculates requests per second (RPS)."""
        query = f"sum(rate(http_requests_total{{endpoint='{endpoint}'}}[{window}]))"
        val = self._query_instant(query)
        return round(val, 2) if val is not None else None

    def get_active_replicas(self, deployment: str = "webapp-deployment") -> Optional[int]:
        """Queries ready pod count from kube-state-metrics."""
        query = f"kube_deployment_status_replicas_available{{deployment='{deployment}'}}"
        val = self._query_instant(query)
        return int(val) if val is not None else None
