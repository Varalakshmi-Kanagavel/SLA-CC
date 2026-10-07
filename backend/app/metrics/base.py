from typing import Protocol

class MetricsProvider(Protocol):
    def get_mode(self) -> str: ...
