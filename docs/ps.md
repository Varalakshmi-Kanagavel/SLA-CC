SLA-Adaptive Autoscaling for Cloud
Applications Using Kubernetes
1. Problem Statement
Cloud applications experience fluctuating workloads, making it difficult to allocate computing
resources efficiently. Fixed resource allocation can lead to underutilization during low demand
and degraded performance during peak demand. Conventional autoscaling mechanisms, such
as Kubernetes Horizontal Pod Autoscaler (HPA), primarily rely on predefined resource utilization
thresholds, which may not adequately adapt to changing workloads or service-level
requirements. This project addresses the challenge of dynamically adjusting autoscaling
thresholds to maintain application performance while optimizing resource utilization in a private
cloud environment.
2. Objective of the Project
To implement and evaluate an SLA-aware autoscaling mechanism based on the research paper
SLA-Adaptive Threshold Adjustment for a Kubernetes Horizontal Pod Autoscaler. The project
aims to compare conventional threshold-based autoscaling with adaptive threshold adjustment,
evaluating their impact on application performance, resource utilization, and service-level
objective (SLO) violations.
3. Cloud Services Used
● Proxmox VE: Provides the private cloud infrastructure and virtual machines.
● Ubuntu Server: Hosts the Kubernetes cluster and application workloads.
● K3s (Kubernetes): Provides container orchestration and autoscaling through HPA.
● Prometheus and Grafana: Collect application and infrastructure metrics and visualize
performance.
● Python: Implements the adaptive threshold adjustment mechanism.
● Locust: Generates controlled workloads for experimentation.
4. Brief Description of the Proposed Solution
A lightweight Kubernetes cluster will be deployed on Ubuntu virtual machines hosted on the
existing Proxmox server. A containerized application will be deployed and configured with
Kubernetes HPA. An adaptive autoscaling controller will be implemented using the
threshold-adjustment principles described in the selected research paper. The controller will use
monitored resource utilization and application performance metrics to adjust scaling thresholds
dynamically. The system will be evaluated under varying workloads and compared against
conventional HPA. The existing Minecraft server will also be incorporated as an additional
workload to study resource utilization and performance under real-world gaming activity. Since
Minecraft is stateful, its integration will be designed appropriately rather than assuming that
additional replicas automatically share the same game world.
5. Expected Outcome
The project is expected to deliver a functional private cloud environment with adaptive
autoscaling, demonstrating how dynamic threshold adjustment can improve resource utilization
while maintaining application performance. Experimental results will compare conventional and
adaptive autoscaling using metrics such as CPU and memory consumption, response time,
scaling delay, and SLO violations. The Minecraft workload will provide an additional practical
evaluation of resource management under gaming workloads. The final deliverables will include
the implementation, monitoring dashboard, experimental results, and a report comparing the
findings with the selected research paper.
By team 10
23N217
23N243
Divya Nandhini
Sai Karthi Balaji
23N264
24N435
Varalakshmi K
Saran M
