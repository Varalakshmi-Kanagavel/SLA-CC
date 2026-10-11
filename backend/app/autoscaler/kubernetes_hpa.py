"""Narrow Kubernetes HPA adapter using the official Python client API shape."""
import logging

logger = logging.getLogger(__name__)


class HpaConfigurationError(RuntimeError):
    pass


def _get(value, key, default=None):
    return value.get(key, default) if isinstance(value, dict) else getattr(value, key, default)


class KubernetesHpaAdapter:
    def __init__(self, api, namespace: str, hpa_name: str, dry_run: bool = True):
        self.api = api
        self.namespace = namespace
        self.hpa_name = hpa_name
        self.dry_run = dry_run

    @classmethod
    def from_env(cls):
        import os
        from kubernetes import client, config
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
        return cls(
            client.AutoscalingV2Api(),
            os.getenv("KUBERNETES_NAMESPACE", os.getenv("NAMESPACE", "sla-autoscaling")),
            os.getenv("HPA_NAME", "webapp-hpa"),
            os.getenv("KUBERNETES_DRY_RUN", os.getenv("DRY_RUN", "true")).lower() == "true",
        )

    def update_cpu_target(self, target: float) -> dict:
        if not 1 <= target <= 100:
            raise ValueError("HPA CPU target must be between 1 and 100")
        old_hpa = self.api.read_namespaced_horizontal_pod_autoscaler(self.hpa_name, self.namespace)
        metrics = _get(_get(old_hpa, "spec", {}), "metrics", []) or []
        cpu_index = next((i for i, metric in enumerate(metrics)
                          if _get(metric, "type") == "Resource"
                          and _get(_get(metric, "resource", {}), "name") == "cpu"), None)
        if cpu_index is None:
            raise HpaConfigurationError(f"HPA {self.hpa_name} has no CPU resource metric")
        resource = _get(metrics[cpu_index], "resource", {})
        current = _get(_get(resource, "target", {}), "average_utilization")
        if current is None:
            current = _get(_get(resource, "target", {}), "averageUtilization")
        new_value = int(round(target))
        if current == new_value:
            return {"namespace": self.namespace, "hpa": self.hpa_name,
                    "old_target": current, "new_target": current, "changed": False,
                    "dry_run": self.dry_run, "confirmed": True}

        resource_version = _get(_get(old_hpa, "metadata", {}), "resource_version")
        if resource_version is None:
            resource_version = _get(_get(old_hpa, "metadata", {}), "resourceVersion")
        path = f"/spec/metrics/{cpu_index}/resource/target/averageUtilization"
        operations = []
        if resource_version:
            operations.append({"op": "test", "path": "/metadata/resourceVersion", "value": resource_version})
        operations.append({"op": "replace" if current is not None else "add", "path": path, "value": new_value})
        try:
            updated = self.api.patch_namespaced_horizontal_pod_autoscaler(
                self.hpa_name, self.namespace, operations,
                dry_run="All" if self.dry_run else None,
                _content_type="application/json-patch+json",
            )
        except Exception:
            logger.exception("HPA update failed namespace=%s hpa=%s old=%s requested=%s",
                             self.namespace, self.hpa_name, current, new_value)
            raise
        logger.info("HPA update confirmed namespace=%s hpa=%s old=%s new=%s dry_run=%s",
                    self.namespace, self.hpa_name, current, new_value, self.dry_run)
        return {"namespace": self.namespace, "hpa": self.hpa_name,
                "old_target": current, "new_target": new_value,
                "changed": True, "dry_run": self.dry_run, "confirmed": updated is not None}

    def read_cpu_target(self) -> int:
        hpa = self.api.read_namespaced_horizontal_pod_autoscaler(self.hpa_name, self.namespace)
        metrics = _get(_get(hpa, "spec", {}), "metrics", []) or []
        for metric in metrics:
            if _get(metric, "type") != "Resource":
                continue
            resource = _get(metric, "resource", {})
            if _get(resource, "name") != "cpu":
                continue
            target = _get(resource, "target", {})
            value = _get(target, "average_utilization", _get(target, "averageUtilization"))
            if isinstance(value, int) and 1 <= value <= 100:
                return value
            raise HpaConfigurationError("HPA CPU metric has no valid averageUtilization target")
        raise HpaConfigurationError(f"HPA {self.hpa_name} has no CPU resource metric")
