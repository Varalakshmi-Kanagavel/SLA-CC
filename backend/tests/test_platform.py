from fastapi.testclient import TestClient
from app.main import app
from app.autoscaler.adaptive_controller import AdaptiveConfig, AdaptiveController
from app.autoscaler.conventional_hpa import desired_replicas
from app.schemas import ExperimentRequest
from app.simulation import execute

client = TestClient(app)

def test_adaptive_threshold_bounds_and_response():
    ctl = AdaptiveController(AdaptiveConfig())
    original = ctl.threshold
    assert ctl.update(400) < original
    assert ctl.update(30) <= 85
    for _ in range(100): ctl.update(10000)
    assert ctl.threshold == 40

def test_adaptive_healthy_recovery_and_determinism():
    a, b = AdaptiveController(AdaptiveConfig()), AdaptiveController(AdaptiveConfig())
    assert a.update(100) == b.update(100) == 71
    assert a.update(100) == b.update(100)

def test_conventional_scaling_and_bounds():
    assert desired_replicas(2, 90, 70, 1, 10) == 3
    assert desired_replicas(4, 20, 70, 1, 10) == 2
    assert desired_replicas(1, 5, 70, 2, 10) == 2
    assert desired_replicas(10, 100, 70, 1, 10) == 10

def test_experiment_same_workload_and_summary():
    result = execute(ExperimentRequest(duration=30, workload="spike"))
    left, right = result["runs"].values()
    assert len(left["metrics"]) == len(right["metrics"]) == 30
    assert [p["users"] for p in left["metrics"]] == [p["users"] for p in right["metrics"]]
    assert "p95_latency" in left["summary"]
    assert any(p["threshold"] != 70 for p in right["metrics"])

def test_api_health_create_fetch_and_exports():
    assert client.get("/api/health").json()["mode"] == "simulation"
    created = client.post("/api/experiments/compare", json={"duration":20}).json()
    assert created["id"] and len(created["runs"]) == 2
    assert client.get(f"/api/experiments/{created['id']}").status_code == 200
    assert "text/csv" in client.get(f"/api/experiments/{created['id']}/export/csv").headers["content-type"]
    assert client.get(f"/api/experiments/{created['id']}/export/json").status_code == 200
