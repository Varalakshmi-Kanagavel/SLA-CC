import pytest
from controller.adaptive_controller import AdaptiveController, AdaptiveConfig

def test_controller_initialization():
    config = AdaptiveConfig(
        slo_ms=200,
        initial_threshold=70,
        min_threshold=40,
        max_threshold=85
    )
    ctl = AdaptiveController(config)
    assert ctl.threshold == 70.0

def test_critical_sla_violation_triggers_rapid_drop():
    config = AdaptiveConfig(slo_ms=200, initial_threshold=70, decrease_step=5.0, cooldown_seconds=0)
    ctl = AdaptiveController(config)
    
    # Latency 350ms >= 200 * 1.5 (300ms) -> Critical violation -> drops by 1.5 * 5 = 7.5
    thresh, action = ctl.update(350.0)
    assert thresh == 62.5
    assert "CRITICAL_VIOLATION" in action

def test_warning_triggers_single_step():
    config = AdaptiveConfig(slo_ms=200, initial_threshold=70, decrease_step=5.0, cooldown_seconds=0)
    ctl = AdaptiveController(config)
    
    # Latency 260ms >= 200 * 1.2 (240ms) and < 300ms -> Warning -> drops by 5.0
    thresh, action = ctl.update(260.0)
    assert thresh == 65.0
    assert "WARNING_BUFFER" in action

def test_headroom_triggers_cautious_increase():
    config = AdaptiveConfig(slo_ms=200, initial_threshold=70, increase_step=1.0, cooldown_seconds=0)
    ctl = AdaptiveController(config)
    
    # Latency 120ms < 200 * 0.8 (160ms) -> Headroom -> raises by 1.0
    thresh, action = ctl.update(120.0)
    assert thresh == 71.0
    assert "HEALTHY_HEADROOM" in action

def test_clamp_bounds():
    config = AdaptiveConfig(slo_ms=200, initial_threshold=42, min_threshold=40, max_threshold=85, decrease_step=5.0, cooldown_seconds=0)
    ctl = AdaptiveController(config)
    
    thresh, _ = ctl.update(500.0)
    assert thresh == 40.0 # Clamped to min
    
    ctl.threshold = 84.5
    thresh, _ = ctl.update(50.0)
    assert thresh == 85.0 # Clamped to max
