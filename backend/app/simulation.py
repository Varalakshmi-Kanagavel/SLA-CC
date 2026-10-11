import math
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from .autoscaler.adaptive_controller import AdaptiveConfig, AdaptiveController
from .autoscaler.conventional_hpa import desired_replicas
from .schemas import ExperimentRequest


def workload_users(pattern: str, t: int, duration: int, initial: int, peak: int) -> int:
    phase = t / max(1, duration - 1)
    if pattern == "constant":
        return initial
    if pattern == "ramp":
        return round(initial + (peak - initial) * phase)
    if pattern == "sawtooth":
        return round(initial + (peak - initial) * (phase * 3 % 1))
    if pattern == "custom":
        return round(initial + (peak - initial) * min(1, phase * 1.5)) if phase < .67 else round(peak - (peak - initial) * ((phase - .67) / .33))
    if pattern == "spike":
        return peak if .35 <= phase <= .62 else initial
    if pattern == "minecraft":
        # Evening burst: players join steadily (0-40%), plateau (40-70%), log off (70-100%)
        if phase < 0.4:
            return round(initial + (peak - initial) * (phase / 0.4))
        elif phase < 0.7:
            return peak
        else:
            return round(peak - (peak - initial) * ((phase - 0.7) / 0.3))
    raise ValueError(f"Unknown workload pattern: {pattern}")


def run_experiment(config: ExperimentRequest, algorithm: str) -> dict[str, Any]:
    if config.min_replicas > config.max_replicas:
        raise ValueError("Minimum replicas must not exceed maximum replicas")
    is_minecraft = config.workload == "minecraft"
    rng = random.Random(73)
    replicas = config.min_replicas
    threshold = config.cpu_threshold
    controller = AdaptiveController(AdaptiveConfig(
        slo_ms=config.slo_ms, initial_threshold=config.cpu_threshold,
        min_threshold=min(40, config.cpu_threshold), max_threshold=max(85, config.cpu_threshold),
        decrease_step=config.decrease_step, increase_step=config.increase_step,
        warning_multiplier=config.warning_multiplier, critical_multiplier=config.critical_multiplier,
    ))
    points: list[dict[str, Any]] = []
    pending = replicas
    cooldown = 0
    for t in range(config.duration):
        users = workload_users(config.workload, t, config.duration, config.initial_users, config.peak_users)
        request_rate = users * 0.8
        if is_minecraft:
            # Proxy pod model: CPU driven by player connections per proxy replica
            cpu = min(100.0, 10 + users * 0.9 / max(1, replicas) + rng.uniform(-2, 2))
            memory = min(96.0, 30 + users * 0.15 / max(1, replicas))
            # Tick latency driven by total player count on the single fixed game pod
            latency = max(50.0, 60 + users * 0.55 + max(0, users - 80) * 0.35 + rng.uniform(-5, 5))
        else:
            cpu = min(100.0, 8 + request_rate * 0.62 / replicas + rng.uniform(-1.5, 1.5))
            memory = min(96.0, 24 + users * 0.12 / replicas)
            latency = max(35.0, 45 + 2.25 * (cpu / max(1, 100 - cpu)) + users * 0.025 + max(0, 3 - replicas) * 12)
        if algorithm == "adaptive":
            threshold = controller.update(latency)
        desired = desired_replicas(replicas, cpu, threshold if algorithm == "adaptive" else config.cpu_threshold, config.min_replicas, config.max_replicas)
        if desired != replicas:
            if cooldown <= 0:
                pending = desired
                cooldown = 4 if desired > replicas else 8
            else:
                cooldown -= 1
        else:
            cooldown = max(0, cooldown - 1)
        point: dict[str, Any] = {
            "t": t, "users": users, "cpu": round(cpu, 2), "memory": round(memory, 2),
            "request_rate": round(request_rate, 2), "response_time": round(latency, 2),
            "replicas": replicas, "threshold": round(threshold if algorithm == "adaptive" else config.cpu_threshold, 2),
            "slo_violation": latency > config.slo_ms, "algorithm": algorithm,
        }
        if is_minecraft:
            point["game_replicas"] = 1  # stateful game pod always fixed at 1
        points.append(point)
        if pending != replicas and (t + 1) % 4 == 0:
            replicas = pending
    return {"algorithm": algorithm, "metrics": points, "summary": summarize(points, config.slo_ms)}


def summarize(points: list[dict[str, Any]], slo: float) -> dict[str, Any]:
    latencies = sorted(p["response_time"] for p in points)
    mean = lambda key: round(sum(p[key] for p in points) / max(1, len(points)), 2)
    return {
        "avg_latency": mean("response_time"),
        "p50_latency": latencies[min(len(latencies) - 1, math.ceil(.50 * len(latencies)) - 1)],
        "p95_latency": latencies[min(len(latencies) - 1, math.ceil(.95 * len(latencies)) - 1)],
        "p99_latency": latencies[min(len(latencies) - 1, math.ceil(.99 * len(latencies)) - 1)],
        "slo_violation_pct": round(sum(p["slo_violation"] for p in points) * 100 / max(1, len(points)), 2),
        "avg_cpu": mean("cpu"),
        "peak_cpu": max(p["cpu"] for p in points),
        "avg_request_rate": mean("request_rate"),
        "avg_replicas": mean("replicas"),
        "peak_replicas": max(p["replicas"] for p in points),
        "scaling_events": sum(points[i]["replicas"] != points[i - 1]["replicas"] for i in range(1, len(points))),
        "slo_ms": slo,
    }


def execute(config: ExperimentRequest) -> dict[str, Any]:
    algorithms = ["conventional", "adaptive"] if config.algorithm == "both" else [config.algorithm]
    if any(a not in ("conventional", "adaptive") for a in algorithms):
        raise ValueError("algorithm must be conventional, adaptive, or both")
    started_at = datetime.now(timezone.utc)
    runs = {a: run_experiment(config, a) for a in algorithms}
    for run in runs.values():
        for point in run["metrics"]:
            point["timestamp"] = (started_at + timedelta(seconds=point["t"])).isoformat()
    return {"name": config.name, "config": config.model_dump(), "started_at": started_at.isoformat(), "mode": "simulation", "runs": runs}
