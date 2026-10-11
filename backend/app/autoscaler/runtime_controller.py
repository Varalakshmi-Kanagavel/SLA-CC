"""Deterministic SLO controller logic used by the Kubernetes runtime adapter."""
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import math
from math import isfinite
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RuntimeConfig:
    slo_ms: float = 200.0
    initial_target: float = 70.0
    min_target: float = 40.0
    max_target: float = 85.0
    warning_multiplier: float = 1.2
    critical_multiplier: float = 1.5
    healthy_multiplier: float = 0.8
    normal_decrease: float = 5.0
    critical_decrease: float = 7.5
    increase: float = 1.0
    cooldown_seconds: float = 60.0
    max_metric_age_seconds: float = 30.0

    def __post_init__(self):
        values = (self.slo_ms, self.initial_target, self.min_target, self.max_target,
                  self.warning_multiplier, self.critical_multiplier, self.healthy_multiplier,
                  self.normal_decrease, self.critical_decrease, self.increase,
                  self.cooldown_seconds, self.max_metric_age_seconds)
        if not all(isfinite(value) for value in values):
            raise ValueError("Controller settings must be finite numbers")
        if self.slo_ms <= 0 or not 0 < self.min_target <= self.max_target <= 100:
            raise ValueError("SLO must be positive and CPU bounds must satisfy 0 < min <= max <= 100")
        if not self.min_target <= self.initial_target <= self.max_target:
            raise ValueError("Initial CPU target must be within the configured bounds")
        if not 0 < self.healthy_multiplier < self.warning_multiplier < self.critical_multiplier:
            raise ValueError("Latency multipliers must satisfy 0 < healthy < warning < critical")
        if min(self.normal_decrease, self.critical_decrease, self.increase) <= 0:
            raise ValueError("Threshold adjustment steps must be positive")
        if self.cooldown_seconds < 0 or self.max_metric_age_seconds <= 0:
            raise ValueError("Cooldown must be non-negative and maximum metric age must be positive")

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        import os
        return cls(
            slo_ms=float(os.getenv("SLO_MS", "200")),
            initial_target=float(os.getenv("INITIAL_CPU_TARGET", os.getenv("INITIAL_THRESHOLD", "70"))),
            min_target=float(os.getenv("MIN_CPU_TARGET", os.getenv("MIN_THRESHOLD", "40"))),
            max_target=float(os.getenv("MAX_CPU_TARGET", os.getenv("MAX_THRESHOLD", "85"))),
            warning_multiplier=float(os.getenv("WARNING_MULTIPLIER", "1.2")),
            critical_multiplier=float(os.getenv("CRITICAL_MULTIPLIER", "1.5")),
            healthy_multiplier=float(os.getenv("HEALTHY_MULTIPLIER", "0.8")),
            normal_decrease=float(os.getenv("NORMAL_DECREASE", os.getenv("DECREASE_STEP", "5"))),
            critical_decrease=float(os.getenv("CRITICAL_DECREASE", "7.5")),
            increase=float(os.getenv("INCREASE_STEP", "1")),
            cooldown_seconds=float(os.getenv("COOLDOWN_SECONDS", "60")),
            max_metric_age_seconds=float(os.getenv("MAX_METRIC_AGE_SECONDS", "30")),
        )


@dataclass(frozen=True)
class LatencyObservation:
    p95_ms: Optional[float]
    observed_at: Optional[datetime]
    error: Optional[str] = None


@dataclass(frozen=True)
class Decision:
    old_target: float
    new_target: float
    reason: str
    hpa_average_utilization: int
    changed: bool
    previous_adjustment: Optional[datetime]


class AdaptiveRuntimeController:
    """Adjusts HPA target policy; HPA itself calculates replica counts."""

    def __init__(self, config: RuntimeConfig, target: Optional[float] = None):
        if not 0 < config.min_target <= config.max_target <= 100:
            raise ValueError("CPU target bounds must satisfy 0 < min <= max <= 100")
        if not config.min_target <= (target if target is not None else config.initial_target) <= config.max_target:
            raise ValueError("Initial target must be within configured bounds")
        self.config = config
        self.target = target if target is not None else config.initial_target
        self.last_adjustment: Optional[datetime] = None

    def observe(self, observation: LatencyObservation, now: Optional[datetime] = None) -> Decision:
        now = now or datetime.now(timezone.utc)
        old = self.target
        old_adjustment = self.last_adjustment
        reason = self._invalid_reason(observation, now)
        if reason is None and self.last_adjustment is not None:
            age = (now - self.last_adjustment).total_seconds()
            if age < self.config.cooldown_seconds:
                reason = "cooldown"
        if reason is None:
            latency = float(observation.p95_ms)  # validated above
            c = self.config
            if latency >= c.slo_ms * c.critical_multiplier:
                self.target = max(c.min_target, self.target - c.critical_decrease)
                reason = "critical_latency"
            elif latency >= c.slo_ms * c.warning_multiplier:
                self.target = max(c.min_target, self.target - c.normal_decrease)
                reason = "warning_latency"
            elif latency >= c.slo_ms * c.healthy_multiplier:
                reason = "within_slo_hold"
            else:
                self.target = min(c.max_target, self.target + c.increase)
                reason = "healthy_headroom"
        changed = self.target != old
        if changed:
            self.last_adjustment = now
        decision = Decision(old, self.target, reason, int(round(self.target)), changed, old_adjustment)
        logger.info("latency_p95_ms=%s decision=%s target_old=%s target_new=%s error=%s",
                    observation.p95_ms, reason, old, self.target, observation.error)
        return decision

    def rollback(self, decision: Decision) -> None:
        """Undo a proposed change when Kubernetes rejects the HPA patch."""
        if decision.changed and self.target == decision.new_target:
            self.target = decision.old_target
            self.last_adjustment = decision.previous_adjustment
            logger.warning("HPA target change rolled back old=%s requested=%s", decision.new_target, decision.old_target)

    def _invalid_reason(self, observation: LatencyObservation, now: datetime) -> Optional[str]:
        if observation.error:
            return "metrics_error"
        if observation.p95_ms is None or observation.observed_at is None:
            return "metrics_missing"
        try:
            value = float(observation.p95_ms)
        except (TypeError, ValueError):
            return "metrics_invalid"
        if not math.isfinite(value) or value < 0:
            return "metrics_invalid"
        if not isinstance(observation.observed_at, datetime) or observation.observed_at.tzinfo is None or now.tzinfo is None:
            return "metrics_invalid_timestamp"
        age = (now - observation.observed_at).total_seconds()
        if age < -5 or age > self.config.max_metric_age_seconds:
            return "metrics_stale"
        return None
