# Experiment plan

1. Fix a workload pattern, duration, initial users, peak users, and SLO.
2. Run both policies with those identical inputs.
3. Save the configuration and every simulated time step with the result.
4. Compare response-time distribution, SLO violations, CPU, replicas, and scaling events.
5. Export CSV/JSON and record that the run uses synthetic simulation.
6. Repeat with multiple workload shapes and parameter settings; do not generalize from a single run.
