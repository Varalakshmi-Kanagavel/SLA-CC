import math
from locust import HttpUser, task, between, LoadTestShape

class WebAppUser(HttpUser):
    wait_time = between(0.05, 0.2)

    @task(5)
    def standard_workload(self):
        # Medium CPU computation
        self.client.get("/workload?iterations=12000&sleep_ms=5", name="standard_workload")

    @task(2)
    def heavy_workload(self):
        # Intensive CPU computation
        self.client.get("/workload?iterations=25000&sleep_ms=15", name="heavy_workload")

    @task(1)
    def health_check(self):
        self.client.get("/health", name="health")


class CustomLoadShape(LoadTestShape):
    """
    Parametric Load Shape implementing:
    1. Ramp-Up (0 -> 120s): 10 to 150 users
    2. Flash Crowd Spike (120 -> 240s): Burst to 400 users
    3. Diurnal Wave (240 -> 480s): Oscillating between 80 and 250 users
    4. Cool-down (480 -> 600s): Drop to 20 users
    """
    stages = [
        {"duration": 120, "users": 150, "spawn_rate": 5},
        {"duration": 240, "users": 400, "spawn_rate": 25},
        {"duration": 360, "users": 100, "spawn_rate": 10},
        {"duration": 480, "users": 280, "spawn_rate": 15},
        {"duration": 600, "users": 20,  "spawn_rate": 10},
    ]

    def tick(self):
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                tick_data = (stage["users"], stage["spawn_rate"])
                return tick_data

        return None
