"""Process entry point for the opt-in Kubernetes adaptive controller Deployment."""
import logging
import os
import time

from .kubernetes_hpa import KubernetesHpaAdapter
from .leader_lock import KubernetesLeaseLock
from .runtime_controller import AdaptiveRuntimeController, LatencyObservation, RuntimeConfig
from ..metrics.prometheus_client import PrometheusClient, PrometheusUnavailable


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper(),
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    log = logging.getLogger("cloudscale.controller")
    interval = max(1.0, float(os.getenv("CONTROL_INTERVAL_SECONDS", os.getenv("POLL_INTERVAL_SECONDS", "10"))))
    config = RuntimeConfig.from_env()
    metrics = PrometheusClient.from_env()
    hpa = KubernetesHpaAdapter.from_env()
    lease = KubernetesLeaseLock.from_env()
    controller = AdaptiveRuntimeController(config)
    try:
        current_hpa_target = hpa.read_cpu_target()
        controller.target = float(current_hpa_target)
        log.info("initialized controller target from HPA target=%s", current_hpa_target)
    except Exception as exc:
        log.error("cannot read the initial HPA target; first control actions will fail safely: %s", exc)
    log.info("controller starting mode=live namespace=%s hpa=%s interval=%ss dry_run=%s",
             hpa.namespace, hpa.hpa_name, interval, hpa.dry_run)
    while True:
        try:
            if not lease.acquire_or_renew():
                log.warning("controller lease is held by another pod; skipping this control cycle")
                time.sleep(interval)
                continue
        except Exception as exc:
            log.error("cannot establish single-writer lease; skipping control cycle: %s", exc)
            time.sleep(interval)
            continue
        try:
            sample = metrics.query_p95()
            observation = LatencyObservation(sample.value, sample.observed_at)
        except PrometheusUnavailable as exc:
            observation = LatencyObservation(None, None, str(exc))
            log.error("mode=unavailable component=prometheus error=%s", exc)
        decision = controller.observe(observation)
        if decision.changed and observation.error is None:
            try:
                result = hpa.update_cpu_target(decision.new_target)
                if not result["confirmed"]:
                    log.error("HPA adapter returned without API confirmation: %s", result)
                    controller.rollback(decision)
                else:
                    log.info("HPA target decision=%s old=%s requested=%s rounded=%s dry_run=%s",
                             decision.reason, decision.old_target, decision.new_target,
                             decision.hpa_average_utilization, result["dry_run"])
            except Exception as exc:
                log.exception("mode=live component=kubernetes_hpa update_failed error=%s", exc)
                controller.rollback(decision)
        time.sleep(interval)


if __name__ == "__main__":
    main()
