from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
import json
import pytest

from app.autoscaler.runtime_controller import (
    AdaptiveRuntimeController, LatencyObservation, RuntimeConfig,
)
from app.autoscaler.kubernetes_hpa import HpaConfigurationError, KubernetesHpaAdapter
from app.autoscaler.leader_lock import KubernetesLeaseLock
from app.metrics.prometheus_client import PrometheusClient, PrometheusUnavailable


def observation(value, at=None, error=None):
    return LatencyObservation(value, at or datetime.now(timezone.utc), error)


@pytest.mark.parametrize("latency,expected,reason", [
    (300, 62.5, "critical_latency"),
    (240, 65, "warning_latency"),
    (160, 70, "within_slo_hold"),
    (159.99, 71, "healthy_headroom"),
])
def test_runtime_controller_latency_bands(latency, expected, reason):
    controller = AdaptiveRuntimeController(RuntimeConfig())
    decision = controller.observe(observation(latency))
    assert decision.new_target == expected
    assert decision.reason == reason


def test_runtime_controller_bounds_fractional_target_and_cooldown():
    now = datetime.now(timezone.utc)
    config = RuntimeConfig(initial_target=41, min_target=40, cooldown_seconds=60)
    ctl = AdaptiveRuntimeController(config)
    first = ctl.observe(observation(400, now), now)
    assert first.new_target == 40
    assert first.hpa_average_utilization == 40
    assert first.changed
    assert ctl.observe(observation(400, now + timedelta(seconds=10)), now + timedelta(seconds=10)).reason == "cooldown"
    later = ctl.observe(observation(150, now + timedelta(seconds=61)), now + timedelta(seconds=61))
    assert later.new_target == 41
    fractional = AdaptiveRuntimeController(RuntimeConfig(initial_target=70.5, increase=0.5))
    result = fractional.observe(observation(100))
    assert result.new_target == 71
    assert result.hpa_average_utilization == 71


def test_controller_retries_after_rejected_hpa_change_and_rejects_bad_config():
    now = datetime.now(timezone.utc)
    ctl = AdaptiveRuntimeController(RuntimeConfig())
    proposed = ctl.observe(observation(350, now), now)
    ctl.rollback(proposed)
    retry = ctl.observe(observation(350, now + timedelta(seconds=10)), now + timedelta(seconds=10))
    assert retry.reason == "critical_latency"
    assert retry.new_target == 62.5
    with pytest.raises(ValueError, match="finite"):
        RuntimeConfig(slo_ms=float("nan"))


@pytest.mark.parametrize("obs,reason", [
    (LatencyObservation(None, None), "metrics_missing"),
    (LatencyObservation(float("nan"), datetime.now(timezone.utc)), "metrics_invalid"),
    (LatencyObservation(float("inf"), datetime.now(timezone.utc)), "metrics_invalid"),
    (LatencyObservation(-1, datetime.now(timezone.utc)), "metrics_invalid"),
    (LatencyObservation(100, datetime.now(timezone.utc) - timedelta(minutes=2)), "metrics_stale"),
    (LatencyObservation(None, None, "request timed out"), "metrics_error"),
])
def test_invalid_or_unavailable_metrics_never_lower_threshold(obs, reason):
    ctl = AdaptiveRuntimeController(RuntimeConfig())
    decision = ctl.observe(obs)
    assert decision.reason == reason
    assert decision.new_target == 70


def test_controller_is_deterministic():
    a, b = AdaptiveRuntimeController(RuntimeConfig()), AdaptiveRuntimeController(RuntimeConfig())
    now = datetime.now(timezone.utc)
    for value in (250, 350, 180, 100):
        sample = observation(value, now)
        assert a.observe(sample, now) == b.observe(sample, now)


def prometheus_response(payload, status=200):
    response = Mock()
    response.status = status
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    response.read.return_value = json.dumps(payload).encode()
    return response


def test_prometheus_validates_and_parses_fresh_numeric_p95():
    now = datetime.now(timezone.utc)
    body = {"status": "success", "data": {"result": [{"value": [str(now.timestamp()), "245.5"]}]}}
    with patch("app.metrics.prometheus_client.urlopen", return_value=prometheus_response(body)) as request:
        sample = PrometheusClient("http://prometheus", "up", max_age_seconds=30).query_p95(now)
    assert sample.value == 245.5
    assert request.call_args.kwargs["timeout"] == 3.0


@pytest.mark.parametrize("body", [
    {"status": "error"},
    {"status": "success", "data": {"result": []}},
    {"status": "success", "data": {"result": [{"value": ["x", "5"]}]}},
    {"status": "success", "data": {"result": [{"value": ["1", "NaN"]}]}},
])
def test_prometheus_rejects_failed_empty_malformed_and_nonfinite_responses(body):
    with patch("app.metrics.prometheus_client.urlopen", return_value=prometheus_response(body)):
        with pytest.raises(PrometheusUnavailable):
            PrometheusClient("http://prometheus", "up").query_p95()


def test_prometheus_rejects_stale_sample_and_network_error():
    stale = {"status": "success", "data": {"result": [{"value": ["1", "5"]}]}}
    with patch("app.metrics.prometheus_client.urlopen", return_value=prometheus_response(stale)):
        with pytest.raises(PrometheusUnavailable, match="stale"):
            PrometheusClient("http://prometheus", "up").query_p95()
    with patch("app.metrics.prometheus_client.urlopen", side_effect=TimeoutError("late")):
        with pytest.raises(PrometheusUnavailable, match="query failed"):
            PrometheusClient("http://prometheus", "up").query_p95()


def make_hpa():
    return {"metadata": {"resourceVersion": "17"}, "spec": {"metrics": [
        {"type": "Pods", "pods": {"metric": {"name": "requests_per_second"}, "target": {"averageValue": "20"}}},
        {"type": "Resource", "resource": {"name": "cpu", "target": {"type": "Utilization", "averageUtilization": 70}}},
        {"type": "Resource", "resource": {"name": "memory", "target": {"type": "Utilization", "averageUtilization": 80}}},
    ], "behavior": {"scaleDown": {"stabilizationWindowSeconds": 300}}}}


def test_kubernetes_adapter_selects_cpu_metric_and_only_patches_that_field():
    api = Mock()
    api.read_namespaced_horizontal_pod_autoscaler.return_value = make_hpa()
    api.patch_namespaced_horizontal_pod_autoscaler.return_value = {"metadata": {"resourceVersion": "18"}}
    result = KubernetesHpaAdapter(api, "research", "webapp-hpa", dry_run=True).update_cpu_target(65.5)
    operations = api.patch_namespaced_horizontal_pod_autoscaler.call_args.args[2]
    assert result["confirmed"] and result["dry_run"] and result["new_target"] == 66
    assert operations[-1] == {"op": "replace", "path": "/spec/metrics/1/resource/target/averageUtilization", "value": 66}
    assert operations[0]["path"] == "/metadata/resourceVersion"
    assert api.patch_namespaced_horizontal_pod_autoscaler.call_args.kwargs["dry_run"] == "All"
    api.read_namespaced_horizontal_pod_autoscaler.return_value = make_hpa()
    assert KubernetesHpaAdapter(api, "research", "webapp-hpa").read_cpu_target() == 70


def test_kubernetes_adapter_missing_cpu_and_api_errors_are_not_hidden():
    api = Mock()
    api.read_namespaced_horizontal_pod_autoscaler.return_value = {"metadata": {}, "spec": {"metrics": [{"type": "Pods"}]}}
    with pytest.raises(HpaConfigurationError):
        KubernetesHpaAdapter(api, "research", "webapp-hpa").update_cpu_target(65)
    api.read_namespaced_horizontal_pod_autoscaler.side_effect = RuntimeError("forbidden")
    with pytest.raises(RuntimeError, match="forbidden"):
        KubernetesHpaAdapter(api, "research", "webapp-hpa").update_cpu_target(65)


def test_lease_lock_serializes_controllers_and_recovers_expired_lease():
    now = datetime.now(timezone.utc)
    busy_api = Mock()
    busy_api.read_namespaced_lease.return_value = {"spec": {
        "holderIdentity": "controller-a", "renewTime": now - timedelta(seconds=3),
        "leaseDurationSeconds": 30,
    }}
    assert not KubernetesLeaseLock(busy_api, "research", "lock", "controller-b").acquire_or_renew(now)
    busy_api.replace_namespaced_lease.assert_not_called()

    expired_api = Mock()
    expired_api.read_namespaced_lease.return_value = {"metadata": {"resourceVersion": "8"}, "spec": {
        "holderIdentity": "controller-a", "renewTime": now - timedelta(seconds=45),
        "leaseDurationSeconds": 30, "acquireTime": now - timedelta(minutes=4),
    }}
    assert KubernetesLeaseLock(expired_api, "research", "lock", "controller-b").acquire_or_renew(now)
    body = expired_api.replace_namespaced_lease.call_args.args[2]
    assert body.spec.holder_identity == "controller-b"
    assert body.metadata.resource_version == "8"


def test_lease_lock_creates_only_when_missing_and_surfaces_other_errors():
    missing_api = Mock()
    missing_api.read_namespaced_lease.side_effect = type("NotFound", (Exception,), {"status": 404})()
    assert KubernetesLeaseLock(missing_api, "research", "lock", "controller-a").acquire_or_renew()
    missing_api.create_namespaced_lease.assert_called_once()
    forbidden_api = Mock()
    forbidden_api.read_namespaced_lease.side_effect = type("Forbidden", (Exception,), {"status": 403})()
    with pytest.raises(Exception):
        KubernetesLeaseLock(forbidden_api, "research", "lock", "controller-a").acquire_or_renew()
