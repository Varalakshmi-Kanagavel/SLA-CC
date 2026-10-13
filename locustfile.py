"""SLA-Adaptive Kubernetes Autoscaling for Cloud Applications.

Locust traffic for the CloudScale Lab FastAPI workload. Set the target with
Locust's --host option; no application host is embedded in this file.
"""

import os

from locust import HttpUser, between, task


def _wait_bounds() -> tuple[float, float]:
    """Read a safe, configurable think-time range from the environment."""
    try:
        minimum = float(os.getenv("LOCUST_MIN_WAIT_SECONDS", "1.0"))
        maximum = float(os.getenv("LOCUST_MAX_WAIT_SECONDS", "2.0"))
    except ValueError as exc:
        raise ValueError(
            "LOCUST_MIN_WAIT_SECONDS and LOCUST_MAX_WAIT_SECONDS must be numbers"
        ) from exc

    if minimum < 0 or maximum < minimum:
        raise ValueError(
            "Wait times must satisfy 0 <= LOCUST_MIN_WAIT_SECONDS "
            "<= LOCUST_MAX_WAIT_SECONDS"
        )
    return minimum, maximum


MIN_WAIT_SECONDS, MAX_WAIT_SECONDS = _wait_bounds()


class CloudScaleUser(HttpUser):
    """A light client that mostly exercises the CPU/latency workload endpoint."""

    # Set LOCUST_MIN_WAIT_SECONDS and LOCUST_MAX_WAIT_SECONDS before launching
    # Locust to tune the pause between requests. Defaults are 1–2 seconds.
    wait_time = between(MIN_WAIT_SECONDS, MAX_WAIT_SECONDS)

    @task(5)
    def run_workload(self) -> None:
        """Call the workload using the app's safe built-in default parameters."""
        self._get_and_record("/workload")

    @task(1)
    def check_health(self) -> None:
        """Occasionally check that the application remains healthy."""
        self._get_and_record("/health")

    def _get_and_record(self, endpoint: str) -> None:
        # Name each request explicitly so the Locust table reports failures
        # separately for GET /workload and GET /health.
        with self.client.get(endpoint, name=f"GET {endpoint}", catch_response=True) as response:
            if not 200 <= response.status_code < 300:
                response.failure(f"HTTP {response.status_code}")
            else:
                response.success()
