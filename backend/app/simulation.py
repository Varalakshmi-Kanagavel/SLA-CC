import math
import random
from dataclasses import asdict
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
    raise ValueError(f"Unknown workload pattern: {pattern}")


def run_experiment(config: ExperimentRequest, algorithm: str) -> dict[str, Any]:
    if config.min_replicas > config.max_replicas:
        raise ValueError("Minimum replicas must not exceed maximum replicas")
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
        points.append({"t": t, "users": users, "cpu": round(cpu, 2), "memory": round(memory, 2), "request_rate": round(request_rate, 2), "response_time": round(latency, 2), "replicas": replicas, "threshold": round(threshold if algorithm == "adaptive" else config.cpu_threshold, 2), "slo_violation": latency > config.slo_ms, "algorithm": algorithm})
        if pending != replicas and (t + 1) % 4 == 0:
            replicas = pending
    return {"algorithm": algorithm, "metrics": points, "summary": summarize(points, config.slo_ms)}


def summarize(points: list[dict[str, Any]], slo: float) -> dict[str, Any]:
    latencies = sorted(p["response_time"] for p in points)
    mean = lambda key: round(sum(p[key] for p in points) / max(1, len(points)), 2)
    return {"avg_latency": mean("response_time"), "p95_latency": latencies[min(len(latencies)-1, math.ceil(.95*len(latencies))-1)], "slo_violation_pct": round(sum(p["slo_violation"] for p in points) * 100 / max(1, len(points)), 2), "avg_cpu": mean("cpu"), "peak_cpu": max(p["cpu"] for p in points), "avg_replicas": mean("replicas"), "peak_replicas": max(p["replicas"] for p in points), "scaling_events": sum(points[i]["replicas"] != points[i-1]["replicas"] for i in range(1,len(points))), "slo_ms": slo}


def execute(config: ExperimentRequest) -> dict[str, Any]:
    algorithms = ["conventional", "adaptive"] if config.algorithm == "both" else [config.algorithm]
    if any(a not in ("conventional", "adaptive") for a in algorithms):
        raise ValueError("algorithm must be conventional, adaptive, or both")
    runs = {a: run_experiment(config, a) for a in algorithms}
    return {"name": config.name, "config": config.model_dump(), "runs": runs}
