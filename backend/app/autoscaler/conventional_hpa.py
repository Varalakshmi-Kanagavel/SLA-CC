import math


def desired_replicas(current: int, cpu: float, target: float, minimum: int, maximum: int) -> int:
    if target <= 0:
        raise ValueError("CPU target must be positive")
    return max(minimum, min(maximum, math.ceil(current * cpu / target)))
