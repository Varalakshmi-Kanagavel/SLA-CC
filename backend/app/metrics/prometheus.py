import requests
from typing import Optional, Dict, Any

class PrometheusMetricsProvider:
    """
    Integration provider for Prometheus HTTP API.
    Can operate in stub mode or connect to a live Prometheus endpoint.
    """
    def __init__(self, base_url: str = "http://localhost:9090"):
        self.base_url = base_url.rstrip("/")

    def get_mode(self) -> str:
        return "prometheus"

    def query_instant(self, query: str) -> Optional[float]:
        url = f"{self.base_url}/api/v1/query"
        try:
            resp = requests.get(url, params={"query": query}, timeout=3.0)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("data", {}).get("result", [])
                if results:
                    return float(results[0]["value"][1])
        except Exception:
            pass
        return None

    def query_p95_latency(self, endpoint: str = "/workload") -> Optional[float]:
        query = f"histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{{endpoint='{endpoint}'}}[1m])) by (le)) * 1000"
        return self.query_instant(query)

    def query_cpu_usage(self, container_name: str = "webapp") -> Optional[float]:
        query = f"sum(rate(container_cpu_usage_seconds_total{{container='{container_name}'}}[1m])) / sum(kube_pod_container_resource_requests{{resource='cpu', container='{container_name}'}}) * 100"
        return self.query_instant(query)
