import time
from dataclasses import dataclass
from typing import Tuple

@dataclass
class AdaptiveConfig:
    slo_ms: float = 200.0
    initial_threshold: float = 70.0
    min_threshold: float = 40.0
    max_threshold: float = 85.0
    decrease_step: float = 5.0
    increase_step: float = 1.0
    warning_multiplier: float = 1.2
    critical_multiplier: float = 1.5
    cooldown_seconds: float = 30.0  # Anti-flapping stabilization window

class AdaptiveController:
    """
    SLA-Aware Feedback Controller for Kubernetes Horizontal Pod Autoscaler.
    Dynamically adjusts targetCPUUtilizationPercentage based on live latency percentiles.
    """
    def __init__(self, config: AdaptiveConfig):
        self.config = config
        self.threshold = float(config.initial_threshold)
        self.last_adjustment_time = 0.0
        self.last_action = "INITIALIZED"

    def update(self, latency_ms: float) -> Tuple[float, str]:
        c = self.config
        now = time.time()
        time_since_last_change = now - self.last_adjustment_time

        # Check critical condition (emergency scale-out)
        if latency_ms >= c.slo_ms * c.critical_multiplier:
            # Emergency decrease ignores normal cooldown to protect SLO
            new_threshold = self.threshold - (c.decrease_step * 1.5)
            action = f"CRITICAL_VIOLATION (Latency: {latency_ms:.1f}ms >= {c.slo_ms * c.critical_multiplier:.1f}ms)"
        elif latency_ms >= c.slo_ms * c.warning_multiplier:
            if time_since_last_change < c.cooldown_seconds:
                return round(self.threshold, 2), f"COOLDOWN_ACTIVE (Elapsed: {time_since_last_change:.1f}s < {c.cooldown_seconds}s)"
            new_threshold = self.threshold - c.decrease_step
            action = f"WARNING_BUFFER (Latency: {latency_ms:.1f}ms >= {c.slo_ms * c.warning_multiplier:.1f}ms)"
        elif latency_ms < c.slo_ms * 0.8:
            if time_since_last_change < c.cooldown_seconds:
                return round(self.threshold, 2), f"COOLDOWN_ACTIVE (Elapsed: {time_since_last_change:.1f}s < {c.cooldown_seconds}s)"
            new_threshold = self.threshold + c.increase_step
            action = f"HEALTHY_HEADROOM (Latency: {latency_ms:.1f}ms < {c.slo_ms * 0.8:.1f}ms)"
        else:
            return round(self.threshold, 2), f"STABLE_ZONE (Latency: {latency_ms:.1f}ms within safe SLA bound)"

        # Apply clamp
        clamped_threshold = min(c.max_threshold, max(c.min_threshold, new_threshold))
        
        if clamped_threshold != self.threshold:
            self.threshold = clamped_threshold
            self.last_adjustment_time = now
            self.last_action = action
            return round(self.threshold, 2), f"THRESHOLD_UPDATED: {action}"
        
        return round(self.threshold, 2), f"CLAMP_REACHED: {action}"
