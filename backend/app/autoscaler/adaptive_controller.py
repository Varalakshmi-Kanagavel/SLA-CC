from dataclasses import dataclass


@dataclass
class AdaptiveConfig:
    slo_ms: float = 200
    initial_threshold: float = 70
    min_threshold: float = 40
    max_threshold: float = 85
    decrease_step: float = 5
    increase_step: float = 1
    warning_multiplier: float = 1.2
    critical_multiplier: float = 1.5


class AdaptiveController:
    """Paper-inspired SLO feedback controller; not a reproduction of a paper."""

    def __init__(self, config: AdaptiveConfig):
        self.config = config
        self.threshold = config.initial_threshold

    def update(self, latency_ms: float) -> float:
        c = self.config
        if latency_ms >= c.slo_ms * c.critical_multiplier:
            self.threshold -= c.decrease_step * 1.5
        elif latency_ms > c.slo_ms * c.warning_multiplier:
            self.threshold -= c.decrease_step
        elif latency_ms < c.slo_ms * 0.8:
            self.threshold += c.increase_step
        self.threshold = min(c.max_threshold, max(c.min_threshold, self.threshold))
        return round(self.threshold, 2)
