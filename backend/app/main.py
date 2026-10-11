import csv
import io
import json
import os
import sqlite3
import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from .schemas import BatchRequest, ExperimentRequest
from .simulation import execute

app = FastAPI(title="CloudScale Lab API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
DB_PATH = Path(os.getenv("CLOUDSCALE_DB", Path(__file__).resolve().parents[1] / "cloudscale.db"))

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as db:
        db.execute("CREATE TABLE IF NOT EXISTS experiments (id TEXT PRIMARY KEY, name TEXT NOT NULL, result TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
init_db()

@app.get("/api/health")
def health():
    return {"status": "ok", "mode": "simulation", "service": "CloudScale Lab"}

@app.get("/api/config")
def config():
    return {"mode": "simulation", "kubernetes_configured": False, "prometheus_configured": False}

@app.post("/api/experiments")
def create_experiment(request: ExperimentRequest):
    try:
        result = execute(request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    experiment_id = str(uuid.uuid4())
    result["id"] = experiment_id
    with sqlite3.connect(DB_PATH) as db:
        db.execute("INSERT INTO experiments (id, name, result) VALUES (?, ?, ?)", (experiment_id, request.name, json.dumps(result)))
    return result

@app.post("/api/experiments/compare")
def compare(request: ExperimentRequest):
    request.algorithm = "both"
    return create_experiment(request)


@app.post("/api/experiments/batch")
def create_batch(request: BatchRequest):
    results = []
    for scenario in request.scenarios:
        scenario.algorithm = "both"
        results.append(create_experiment(scenario))
    batch_id = str(uuid.uuid4())
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            "INSERT INTO experiments (id, name, result) VALUES (?, ?, ?)",
            (batch_id, request.name, json.dumps({"batch": True, "batch_id": batch_id, "results": results})),
        )
    return {"batch_id": batch_id, "results": results}

@app.get("/api/experiments")
def list_experiments():
    with sqlite3.connect(DB_PATH) as db:
        return [{"id": row[0], "name": row[1], "created_at": row[2]} for row in db.execute("SELECT id,name,created_at FROM experiments ORDER BY created_at DESC")]

def get_result(experiment_id: str):
    with sqlite3.connect(DB_PATH) as db:
        row = db.execute("SELECT result FROM experiments WHERE id=?", (experiment_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return json.loads(row[0])

@app.get("/api/experiments/{experiment_id}")
def get_experiment(experiment_id: str):
    return get_result(experiment_id)


@app.delete("/api/experiments/{experiment_id}")
def delete_experiment(experiment_id: str):
    with sqlite3.connect(DB_PATH) as db:
        db.execute("DELETE FROM experiments WHERE id=?", (experiment_id,))
    return {"deleted": experiment_id}

@app.get("/api/experiments/{experiment_id}/export/json")
def export_json(experiment_id: str):
    return get_result(experiment_id)

@app.get("/api/experiments/{experiment_id}/export/csv")
def export_csv(experiment_id: str):
    result = get_result(experiment_id)
    output = io.StringIO()
    fields = ["timestamp", "t", "users", "cpu", "memory", "request_rate", "response_time", "replicas", "threshold", "slo_violation", "algorithm"]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for run in result["runs"].values():
        writer.writerows(run["metrics"])
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={experiment_id}.csv"})
