import os
import sys
import time
import signal
import logging
from .adaptive_controller import AdaptiveController, AdaptiveConfig
from .prometheus_client import PrometheusMetricsClient
from .k8s_manager import KubernetesAutoscaleManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("AdaptiveController")

class ControllerService:
    def __init__(self):
        self.running = True
        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)

        # Configuration from environment
        self.namespace = os.getenv("NAMESPACE", "sla-autoscaling")
        self.hpa_name = os.getenv("HPA_NAME", "webapp-hpa")
        self.deployment_name = os.getenv("DEPLOYMENT_NAME", "webapp-deployment")
        self.prometheus_url = os.getenv("PROMETHEUS_URL", "http://prometheus-server.monitoring.svc.cluster.local")
        self.poll_interval = float(os.getenv("POLL_INTERVAL_SECONDS", "10"))
        self.dry_run = os.getenv("DRY_RUN", "false").lower() in ("true", "1", "yes")

        config = AdaptiveConfig(
            slo_ms=float(os.getenv("SLO_MS", "200")),
            initial_threshold=float(os.getenv("INITIAL_THRESHOLD", "70")),
            min_threshold=float(os.getenv("MIN_THRESHOLD", "40")),
            max_threshold=float(os.getenv("MAX_THRESHOLD", "85")),
            decrease_step=float(os.getenv("DECREASE_STEP", "5")),
            increase_step=float(os.getenv("INCREASE_STEP", "1")),
            warning_multiplier=float(os.getenv("WARNING_MULTIPLIER", "1.2")),
            critical_multiplier=float(os.getenv("CRITICAL_MULTIPLIER", "1.5")),
            cooldown_seconds=float(os.getenv("COOLDOWN_SECONDS", "30"))
        )

        self.controller = AdaptiveController(config)
        self.prom_client = PrometheusMetricsClient(self.prometheus_url)
        self.k8s_mgr = KubernetesAutoscaleManager(in_cluster=os.getenv("IN_CLUSTER", "true").lower() == "true")

        logger.info("==================================================")
        logger.info("SLA-Adaptive Autoscaling Controller Initialized")
        logger.info(f"Target Namespace:    {self.namespace}")
        logger.info(f"Target HPA:          {self.hpa_name}")
        logger.info(f"SLO Target (P95):    {config.slo_ms} ms")
        logger.info(f"Threshold Bounds:    [{config.min_threshold}%, {config.max_threshold}%]")
        logger.info(f"Prometheus URL:      {self.prometheus_url}")
        logger.info(f"Dry Run Mode:        {self.dry_run}")
        logger.info("==================================================")

    def _handle_exit(self, signum, frame):
        logger.info("Received termination signal. Exiting gracefully...")
        self.running = False

    def run(self):
        while self.running:
            try:
                # 1. Fetch live metrics from Prometheus
                p95_latency = self.prom_client.get_p95_latency_ms()
                cpu_util = self.prom_client.get_cpu_utilization()
                rps = self.prom_client.get_request_rate()
                replicas = self.prom_client.get_active_replicas(self.deployment_name)

                if p95_latency is None:
                    logger.warning("P95 latency metric currently unavailable from Prometheus (insufficient traffic). Holding threshold.")
                    time.sleep(self.poll_interval)
                    continue

                # 2. Evaluate adaptive control algorithm
                new_threshold, reason = self.controller.update(p95_latency)

                logger.info(
                    f"[Telemetry] P95: {p95_latency:.1f}ms | CPU: {cpu_util or 0:.1f}% | "
                    f"RPS: {rps or 0:.1f} | Replicas: {replicas or 'N/A'} | "
                    f"Current Target: {new_threshold}% | Decision: {reason}"
                )

                # 3. Patch HPA if changed and not in dry-run
                if not self.dry_run:
                    current_hpa_target = self.k8s_mgr.get_current_cpu_target(self.hpa_name, self.namespace)
                    if current_hpa_target is not None and current_hpa_target != int(new_threshold):
                        self.k8s_mgr.patch_hpa_cpu_target(self.hpa_name, self.namespace, int(new_threshold))

            except Exception as e:
                logger.error(f"Error in control loop iteration: {e}", exc_info=True)

            time.sleep(self.poll_interval)

if __name__ == "__main__":
    app = ControllerService()
    app.run()
