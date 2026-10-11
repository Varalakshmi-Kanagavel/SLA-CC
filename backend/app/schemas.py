from typing import List

from pydantic import BaseModel, Field


class ExperimentRequest(BaseModel):
    name: str = "Research run"
    workload: str = "spike"
    duration: int = Field(default=120, ge=20, le=900)
    initial_users: int = Field(default=10, ge=1, le=10000)
    peak_users: int = Field(default=300, ge=1, le=10000)
    slo_ms: float = Field(default=200, gt=0, le=10000)
    cpu_threshold: float = Field(default=70, gt=0, le=100)
    algorithm: str = "both"
    min_replicas: int = Field(default=1, ge=1, le=100)
    max_replicas: int = Field(default=10, ge=1, le=100)
    warning_multiplier: float = Field(default=1.2, gt=1)
    critical_multiplier: float = Field(default=1.5, gt=1)
    decrease_step: float = Field(default=5, gt=0, le=30)
    increase_step: float = Field(default=1, gt=0, le=10)


class SimulationRequest(ExperimentRequest):
    pass


class BatchRequest(BaseModel):
    name: str = "Batch sweep"
    scenarios: List[ExperimentRequest]
