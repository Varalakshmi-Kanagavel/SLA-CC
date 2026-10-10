import logging
from typing import Optional, Dict, Any
from kubernetes import client, config

logger = logging.getLogger("AdaptiveController.K8s")

class KubernetesAutoscaleManager:
    """
    Interacts with the Kubernetes API to read and patch HorizontalPodAutoscaler resources.
    Supports in-cluster ServiceAccount authentication and local ~/.kube/config fallback.
    """
    def __init__(self, in_cluster: bool = True):
        try:
            if in_cluster:
                config.load_incluster_config()
                logger.info("Loaded in-cluster Kubernetes configuration.")
            else:
                config.load_kube_config()
                logger.info("Loaded local kubeconfig.")
        except Exception:
            # Fallback attempt
            try:
                config.load_kube_config()
                logger.info("Fell back to local kubeconfig.")
            except Exception as e:
                logger.error(f"Failed to initialize Kubernetes API client: {e}")

        self.autoscaling_v2 = client.AutoscalingV2Api()
        self.apps_v1 = client.AppsV1Api()

    def get_hpa(self, name: str, namespace: str) -> Optional[Any]:
        try:
            return self.autoscaling_v2.read_namespaced_horizontal_pod_autoscaler(name=name, namespace=namespace)
        except Exception as e:
            logger.error(f"Error reading HPA {name} in namespace {namespace}: {e}")
            return None

    def get_current_cpu_target(self, name: str, namespace: str) -> Optional[int]:
        hpa = self.get_hpa(name, namespace)
        if not hpa:
            return None
        try:
            for metric in hpa.spec.metrics:
                if metric.type == "Resource" and metric.resource.name == "cpu":
                    return metric.resource.target.average_utilization
        except Exception as e:
            logger.error(f"Could not parse CPU target from HPA: {e}")
        return None

    def patch_hpa_cpu_target(self, name: str, namespace: str, target_cpu: int) -> bool:
        """
        Atomically patches the target CPU average utilization of the HPA resource.
        """
        # Read current metric index
        hpa = self.get_hpa(name, namespace)
        if not hpa:
            return False

        cpu_metric_index = 0
        for idx, metric in enumerate(hpa.spec.metrics):
            if metric.type == "Resource" and metric.resource.name == "cpu":
                cpu_metric_index = idx
                break

        patch_body = [
            {
                "op": "replace",
                "path": f"/spec/metrics/{cpu_metric_index}/resource/target/averageUtilization",
                "value": int(target_cpu)
            }
        ]
        try:
            self.autoscaling_v2.patch_namespaced_horizontal_pod_autoscaler(
                name=name,
                namespace=namespace,
                body=patch_body
            )
            logger.info(f"Successfully patched HPA '{name}' target CPU -> {target_cpu}%")
            return True
        except Exception as e:
            logger.error(f"Failed to patch HPA '{name}': {e}")
            return False
