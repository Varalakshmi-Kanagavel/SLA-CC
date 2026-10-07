class PrometheusMetricsProvider:
    """Reserved integration boundary; Prometheus is not required for demo mode."""
    def __init__(self, base_url: str):
        self.base_url = base_url

    def get_mode(self) -> str:
        return "prometheus"
