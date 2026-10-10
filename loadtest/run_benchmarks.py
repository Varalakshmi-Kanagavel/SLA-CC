import os
import sys
import time
import json
import argparse
import requests
import pandas as pd

def query_prometheus_range(prom_url: str, query: str, start_time: float, end_time: float, step: str = "5s"):
    url = f"{prom_url.rstrip('/')}/api/v1/query_range"
    params = {
        "query": query,
        "start": start_time,
        "end": end_time,
        "step": step
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "success":
            results = data.get("data", {}).get("result", [])
            if results:
                # Extract [[timestamp, val], ...]
                return results[0].get("values", [])
    except Exception as e:
        print(f"Error querying Prometheus: {e}")
    return []

def analyze_experiment(name: str, prom_url: str, start_time: float, end_time: float, slo_ms: float = 200.0):
    print(f"--- Analyzing Experiment: {name} ---")
    
    # 1. P95 Latency
    p95_query = "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[1m])) by (le)) * 1000"
    p95_data = query_prometheus_range(prom_url, p95_query, start_time, end_time)

    # 2. CPU Utilization
    cpu_query = "sum(rate(container_cpu_usage_seconds_total{container='webapp'}[1m])) / sum(kube_pod_container_resource_requests{resource='cpu', container='webapp'}) * 100"
    cpu_data = query_prometheus_range(prom_url, cpu_query, start_time, end_time)

    # 3. Active Replicas
    replica_query = "kube_deployment_status_replicas_available{deployment='webapp-deployment'}"
    replica_data = query_prometheus_range(prom_url, replica_query, start_time, end_time)

    latencies = [float(v[1]) for v in p95_data if v[1] != "NaN"]
    cpus = [float(v[1]) for v in cpu_data if v[1] != "NaN"]
    replicas = [int(float(v[1])) for v in replica_data if v[1] != "NaN"]

    total_steps = len(latencies)
    if total_steps == 0:
        print(f"Warning: No metrics recorded for {name}!")
        return {}

    violations = sum(1 for l in latencies if l > slo_ms)
    violation_rate = (violations / total_steps) * 100.0

    summary = {
        "experiment_name": name,
        "duration_seconds": round(end_time - start_time, 1),
        "total_time_steps": total_steps,
        "slo_threshold_ms": slo_ms,
        "slo_violations_count": violations,
        "slo_violation_rate_pct": round(violation_rate, 2),
        "mean_p95_latency_ms": round(sum(latencies) / total_steps, 2),
        "peak_p95_latency_ms": round(max(latencies), 2),
        "mean_cpu_pct": round(sum(cpus) / len(cpus), 2) if cpus else 0.0,
        "mean_replicas": round(sum(replicas) / len(replicas), 2) if replicas else 0.0,
        "peak_replicas": max(replicas) if replicas else 0
    }

    print(json.dumps(summary, indent=2))
    return summary

def main():
    parser = argparse.ArgumentParser(description="Automated HPA Benchmark Evaluation")
    parser.add_argument("--prom-url", default="http://localhost:9090", help="Prometheus base URL")
    parser.add_argument("--target-url", default="http://localhost:30080", help="Target Web App URL")
    parser.add_argument("--slo-ms", type=float, default=200.0, help="SLO Latency threshold in ms")
    parser.add_argument("--duration", type=int, default=600, help="Test duration in seconds")
    parser.add_argument("--output-csv", default="benchmark_comparison_results.csv", help="Output comparison CSV")

    args = parser.parse_args()

    print("=================================================================")
    print("SLA-Adaptive Autoscaling Benchmark Harness")
    print(f"Prometheus URL: {args.prom_url}")
    print(f"Target URL:     {args.target_url}")
    print(f"SLO Target:     {args.slo_ms} ms")
    print(f"Test Duration:  {args.duration} s")
    print("=================================================================")

if __name__ == "__main__":
    main()
