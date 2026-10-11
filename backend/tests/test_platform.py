from fastapi.testclient import TestClient
from app.main import app
from app.autoscaler.adaptive_controller import AdaptiveConfig, AdaptiveController
from app.autoscaler.conventional_hpa import desired_replicas
from app.schemas import ExperimentRequest, BatchRequest
from app.simulation import execute, workload_users

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
    assert all(p["timestamp"] for p in left["metrics"])
    assert [p["timestamp"] for p in left["metrics"]] == [p["timestamp"] for p in right["metrics"]]
    assert all(key in left["summary"] for key in ("p50_latency", "p95_latency", "p99_latency"))
    assert any(p["threshold"] != 70 for p in right["metrics"])

def test_api_health_create_fetch_and_exports():
    assert client.get("/api/health").json()["mode"] == "simulation"
    created = client.post("/api/experiments/compare", json={"duration":20}).json()
    assert created["id"] and len(created["runs"]) == 2
    assert client.get(f"/api/experiments/{created['id']}").status_code == 200
    csv_response = client.get(f"/api/experiments/{created['id']}/export/csv")
    assert "text/csv" in csv_response.headers["content-type"]
    assert "timestamp,t,users" in csv_response.text
    assert client.get(f"/api/experiments/{created['id']}/export/json").status_code == 200

# ── New tests ──────────────────────────────────────────────────────────────

def test_batch_creates_multiple_experiments():
    payload = {
        "name": "Test sweep",
        "scenarios": [
            {"duration": 20, "workload": "spike", "slo_ms": 200},
            {"duration": 20, "workload": "ramp", "slo_ms": 300},
            {"duration": 20, "workload": "constant", "slo_ms": 150},
        ]
    }
    resp = client.post("/api/experiments/batch", json=payload).json()
    assert "batch_id" in resp
    assert len(resp["results"]) == 3
    for r in resp["results"]:
        assert "runs" in r
        assert len(r["runs"]) == 2  # both algorithms

def test_minecraft_workload_shape():
    duration = 100
    initial, peak = 10, 80
    users = [workload_users("minecraft", t, duration, initial, peak) for t in range(duration)]
    # First point near initial, midpoint at peak, last point near initial
    assert users[0] == initial
    assert users[duration // 2] == peak
    assert users[-1] <= initial + 5  # within tolerance at cooldown end

def test_delete_experiment():
    created = client.post("/api/experiments/compare", json={"duration": 20}).json()
    exp_id = created["id"]
    assert client.get(f"/api/experiments/{exp_id}").status_code == 200
    resp = client.delete(f"/api/experiments/{exp_id}").json()
    assert resp["deleted"] == exp_id
    assert client.get(f"/api/experiments/{exp_id}").status_code == 404

def test_minecraft_in_execute():
    result = execute(ExperimentRequest(duration=30, workload="minecraft", slo_ms=250))
    for run in result["runs"].values():
        assert len(run["metrics"]) == 30
        # Game replicas must always be 1
        assert all(p.get("game_replicas") == 1 for p in run["metrics"])
        assert "avg_latency" in run["summary"]
