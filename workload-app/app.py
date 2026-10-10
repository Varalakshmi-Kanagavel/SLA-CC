import os
import time
import math
import hashlib
from fastapi import FastAPI, Response, Request
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI(title="SLA-CC Benchmark Microservice", version="1.0.0")

# Prometheus Metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP Requests",
    ["method", "endpoint", "status"]
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP Request Latency in Seconds",
    ["method", "endpoint"],
    buckets=(0.025, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.75, 1.0, 2.0, 5.0)
)

IN_FLIGHT_REQUESTS = Gauge(
    "http_in_flight_requests",
    "Current in-flight requests"
)

@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    IN_FLIGHT_REQUESTS.inc()
    start_time = time.time()
    endpoint = request.url.path
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        duration = time.time() - start_time
        IN_FLIGHT_REQUESTS.dec()
        REQUEST_COUNT.labels(method=request.method, endpoint=endpoint, status=str(status_code)).inc()
        REQUEST_DURATION.labels(method=request.method, endpoint=endpoint).observe(duration)

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": time.time()}

@app.get("/workload")
def compute_workload(iterations: int = 15000, sleep_ms: float = 10.0):
    """
    Simulates a microservice workload with both CPU computation and I/O delay.
    - iterations: number of SHA-256 hashing loops to consume CPU.
    - sleep_ms: millisecond pause to emulate downstream database/cache I/O latency.
    """
    # 1. Simulate I/O latency
    if sleep_ms > 0:
        time.sleep(sleep_ms / 1000.0)

    # 2. Simulate CPU burn
    data = b"benchmark-workload-string"
    for _ in range(iterations):
        data = hashlib.sha256(data).digest()

    return {
        "status": "completed",
        "iterations": iterations,
        "sleep_ms": sleep_ms,
        "result_hash": data.hex()[:16]
    }

@app.get("/metrics")
def metrics():
    """Prometheus scrape endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
