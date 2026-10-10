import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable, Preformatted
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#475569"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(45, 11 * inch - 30, "SLA-Adaptive Autoscaling on AWS | Cloud Computing Project Blueprint")
            self.drawRightString(8.5 * inch - 45, 11 * inch - 30, "Team 10 - Research Deliverable")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.75)
            self.line(45, 11 * inch - 34, 8.5 * inch - 45, 11 * inch - 34)
        
        # Footer
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        footer_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 45, 24, footer_text)
        self.drawString(45, 24, "CONFIDENTIAL & ACADEMIC PROJECT BLUEPRINT - KUBERNETES AUTOSCALING ON AWS")
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.75)
        self.line(45, 33, 8.5 * inch - 45, 33)
        
        self.restoreState()

def build_pdf(filename="docs/SLA_Adaptive_Autoscaling_AWS_Implementation_Plan.pdf"):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=45,
        rightMargin=45,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    primary_color = colors.HexColor("#0f172a")     # Deep slate
    secondary_color = colors.HexColor("#1d4ed8")   # Vivid Blue
    dark_neutral = colors.HexColor("#1e293b")      # Text Dark
    light_bg = colors.HexColor("#f8fafc")          # Surface light
    border_color = colors.HexColor("#cbd5e1")
    callout_bg = colors.HexColor("#eff6ff")
    accent_green = colors.HexColor("#166534")
    accent_red = colors.HexColor("#991b1b")
    accent_amber = colors.HexColor("#b45309")
    
    doc_title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=primary_color,
        spaceAfter=3
    )
    
    doc_subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=secondary_color,
        spaceAfter=6
    )
    
    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=primary_color,
        spaceBefore=8,
        spaceAfter=3,
        keepWithNext=True
    )
    
    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=secondary_color,
        spaceBefore=6,
        spaceAfter=2,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=dark_neutral,
        spaceAfter=3
    )
    
    code_style = ParagraphStyle(
        'Code_Custom',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#0f172a")
    )
    
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        textColor=dark_neutral
    )
    
    table_cell_header = ParagraphStyle(
        'TableCellHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=10,
        textColor=colors.white
    )
    
    callout_style = ParagraphStyle(
        'CalloutText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.8,
        leading=10.5,
        textColor=colors.HexColor("#1e3a8a")
    )

    story = []

    # ==================== PAGE 1 ====================
    # Title & Metadata
    story.append(Paragraph("SLA-Adaptive Autoscaling for Cloud Applications Using Kubernetes", doc_title_style))
    story.append(Paragraph("AWS Cloud Migration, End-to-End Architecture & Complete Implementation Blueprint", doc_subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=secondary_color, spaceBefore=0, spaceAfter=5))

    meta_data = [
        [
            Paragraph("<b>Project:</b> SLA-Adaptive Kubernetes HPA on AWS", table_cell_style),
            Paragraph("<b>Evaluation Target:</b> Web Microservices + Stateful Gaming (Minecraft)", table_cell_style)
        ],
        [
            Paragraph("<b>Paper Reference:</b> SLA-Adaptive Threshold Adjustment for K8s HPA", table_cell_style),
            Paragraph("<b>Scope:</b> Real EKS/K3s Cluster, Prometheus PromQL, Locust Traffic", table_cell_style)
        ],
        [
            Paragraph("<b>Team 10 Members:</b> 23N217 Divya Nandhini &nbsp;|&nbsp; 23N243 Sai Karthi Balaji<br/>23N264 Varalakshmi K &nbsp;|&nbsp; 24N435 Saran M", table_cell_style),
            Paragraph("<b>Infrastructure Architecture:</b> AWS EKS (Option A) vs AWS EC2 K3s (Option B)", table_cell_style)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[270, 252])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), light_bg),
        ('BOX', (0,0), (-1,-1), 1, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 4))

    # 1. Executive Summary & Codebase Gap Analysis
    story.append(Paragraph("1. Executive Summary & Codebase Gap Analysis", h1_style))
    story.append(Paragraph(
        "<b>Current State in Git Repository (SLA-CC):</b> The current codebase is an academic prototype ('CloudScale Lab') written in FastAPI and React/TypeScript. It implements an in-memory simulation engine that models HPA replica growth and adaptive threshold shifts under predefined mathematical load shapes (ramp, spike, sawtooth). While the mathematical logic is verified, the prototype is purely simulated (<code>mode: simulation</code>) without real Kubernetes APIs, real Linux cgroups, or Prometheus metrics.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Objective of the AWS Implementation:</b> Transition this simulation prototype into a fully functional cloud deployment on Amazon Web Services (AWS). An autonomous in-cluster Python controller daemon will query live Prometheus metrics to dynamically tune the Kubernetes Horizontal Pod Autoscaler (HPA) target thresholds, evaluated under realistic Locust load testing.",
        body_style
    ))

    gap_data = [
        [
            Paragraph("Dimension", table_cell_header),
            Paragraph("Current Prototype (In Repo)", table_cell_header),
            Paragraph("Target AWS Implementation (Next Phase)", table_cell_header)
        ],
        [
            Paragraph("<b>Platform</b>", table_cell_style),
            Paragraph("Local in-memory synthetic state", table_cell_style),
            Paragraph("AWS EKS or AWS EC2 Ubuntu K3s Cluster (Kubernetes v1.28+)", table_cell_style)
        ],
        [
            Paragraph("<b>Telemetry</b>", table_cell_style),
            Paragraph("Math formula with seeded noise", table_cell_style),
            Paragraph("Live Prometheus server scraping application & node cgroups via PromQL", table_cell_style)
        ],
        [
            Paragraph("<b>Workload</b>", table_cell_style),
            Paragraph("None (pure synthetic calculations)", table_cell_style),
            Paragraph("Real containerized HTTP Microservice + Stateful Minecraft Server", table_cell_style)
        ],
        [
            Paragraph("<b>Autoscaling</b>", table_cell_style),
            Paragraph("Calculated within simulation loop", table_cell_style),
            Paragraph("Active K8s HPA patched dynamically via Python Kubernetes API Client", table_cell_style)
        ],
        [
            Paragraph("<b>Traffic Injection</b>", table_cell_style),
            Paragraph("Static array iteration", table_cell_style),
            Paragraph("Distributed Locust on AWS EC2 executing dynamic load test scenarios", table_cell_style)
        ],
        [
            Paragraph("<b>Dashboard</b>", table_cell_style),
            Paragraph("Local browser chart (Recharts)", table_cell_style),
            Paragraph("CloudScale Lab Web UI + Grafana Dashboards backed by live AWS metrics", table_cell_style)
        ]
    ]
    gap_table = Table(gap_data, colWidths=[95, 185, 242])
    gap_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('BOX', (0,0), (-1,-1), 1, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_bg]),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(gap_table)
    story.append(Spacer(1, 4))

    # 2. Target AWS Architecture Options
    story.append(Paragraph("2. AWS Cloud Architecture Deployment Models", h1_style))
    
    arch_data = [
        [
            Paragraph("Attribute", table_cell_header),
            Paragraph("Option A: AWS EKS (Managed Enterprise)", table_cell_header),
            Paragraph("Option B: AWS EC2 Multi-Node K3s (Recommended Budget)", table_cell_header)
        ],
        [
            Paragraph("<b>Control Plane</b>", table_cell_style),
            Paragraph("Managed AWS EKS Cluster (v1.28)", table_cell_style),
            Paragraph("Lightweight K3s server on 1x EC2 <code>t3.medium</code> instance", table_cell_style)
        ],
        [
            Paragraph("<b>Worker Compute</b>", table_cell_style),
            Paragraph("EKS Managed Node Group (2x <code>t3.medium</code>)", table_cell_style),
            Paragraph("1x EC2 <code>t3.medium</code> worker node running pods", table_cell_style)
        ],
        [
            Paragraph("<b>Load Generator</b>", table_cell_style),
            Paragraph("1x EC2 <code>t3.small</code> instance running Locust", table_cell_style),
            Paragraph("1x EC2 <code>t3.small</code> instance outside the cluster running Locust", table_cell_style)
        ],
        [
            Paragraph("<b>Storage & Ingress</b>", table_cell_style),
            Paragraph("AWS ALB + AWS EBS CSI Driver (gp3)", table_cell_style),
            Paragraph("K3s Traefik / NGINX Ingress + Local-Path / EBS CSI volume", table_cell_style)
        ],
        [
            Paragraph("<b>Estimated Cost</b>", table_cell_style),
            Paragraph("~$135 / month ($73 EKS fee + EC2 + NAT)", table_cell_style),
            Paragraph("<b>~$25 - $35 / month</b> (or ~$12/mo on Spot / Free Tier). No EKS fee.", table_cell_style)
        ]
    ]
    arch_table = Table(arch_data, colWidths=[95, 212, 215])
    arch_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('BOX', (0,0), (-1,-1), 1, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_bg]),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(arch_table)
    story.append(Spacer(1, 4))

    callout_data = [[
        Paragraph(
            "<b>Recommendation:</b> Option B (EC2 K3s) delivers 100% API compatibility with standard Kubernetes HPA at 75% lower cost, making it ideal for academic evaluation while preserving 1-click migration to EKS.",
            callout_style
        )
    ]]
    callout_table = Table(callout_data, colWidths=[522])
    callout_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), callout_bg),
        ('BOX', (0,0), (-1,-1), 1, secondary_color),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(callout_table)

    # ==================== PAGE 2 ====================
    story.append(PageBreak())

    # 3. Mathematical & Algorithmic Formulation
    story.append(Paragraph("3. SLA-Adaptive Controller Formulation & Feedback Loop", h1_style))
    story.append(Paragraph(
        "Standard Kubernetes HPA relies on fixed CPU targets: <code>desiredReplicas = ceil(currentReplicas * (currentCPU / targetCPU))</code>. Under non-linear latency increases, fixed targets trigger scaling too late, causing severe SLO violations. Our adaptive algorithm computes a dynamic target threshold <i>T<sub>cpu</sub>(t)</i> at each control cycle <i>Δt = 10s</i> based on observed P95 latency <i>R<sub>p95</sub>(t)</i> relative to the Service Level Objective (<i>SLO</i>):",
        body_style
    ))

    algo_rules = [
        [
            Paragraph("Observed Prometheus Latency", table_cell_header),
            Paragraph("Operating Regime", table_cell_header),
            Paragraph("Adaptive Action Applied to Kubernetes HPA Spec", table_cell_header)
        ],
        [
            Paragraph("<i>R<sub>p95</sub>(t) &ge; SLO &times; 1.5</i>", table_cell_style),
            Paragraph(f"<font color='{accent_red.hexval()}'><b>CRITICAL VIOLATION</b></font>", table_cell_style),
            Paragraph("<i>T<sub>cpu</sub>(t+1) = max(T<sub>min</sub>, T<sub>cpu</sub>(t) - 1.5 &times; &delta;<sub>down</sub>)</i><br/>Aggressively lowers threshold to force immediate pod scale-out.", table_cell_style)
        ],
        [
            Paragraph("<i>SLO &times; 1.2 &le; R<sub>p95</sub>(t) &lt; SLO &times; 1.5</i>", table_cell_style),
            Paragraph(f"<font color='{accent_amber.hexval()}'><b>WARNING BUFFER</b></font>", table_cell_style),
            Paragraph("<i>T<sub>cpu</sub>(t+1) = max(T<sub>min</sub>, T<sub>cpu</sub>(t) - &delta;<sub>down</sub>)</i><br/>Proactively lowers threshold before SLA violation occurs.", table_cell_style)
        ],
        [
            Paragraph("<i>0.8 &times; SLO &le; R<sub>p95</sub>(t) &lt; SLO &times; 1.2</i>", table_cell_style),
            Paragraph("<b>STABLE REGION</b>", table_cell_style),
            Paragraph("<i>T<sub>cpu</sub>(t+1) = T<sub>cpu</sub>(t)</i><br/>Holds current threshold; prevents controller thrashing.", table_cell_style)
        ],
        [
            Paragraph("<i>R<sub>p95</sub>(t) &lt; SLO &times; 0.8</i>", table_cell_style),
            Paragraph(f"<font color='{accent_green.hexval()}'><b>HEALTHY HEADROOM</b></font>", table_cell_style),
            Paragraph("<i>T<sub>cpu</sub>(t+1) = min(T<sub>max</sub>, T<sub>cpu</sub>(t) + &delta;<sub>up</sub>)</i><br/>Conservatively raises threshold to consolidate pods and save cost.", table_cell_style)
        ]
    ]
    algo_table = Table(algo_rules, colWidths=[150, 130, 242])
    algo_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('BOX', (0,0), (-1,-1), 1, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_bg]),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(algo_table)
    story.append(Spacer(1, 3))
    story.append(Paragraph(
        "<b>Asymmetric Safety:</b> Downward adjustments (&delta;<sub>down</sub> = 5% to 7.5%) act 5x faster than upward relaxation (&delta;<sub>up</sub> = 1%), preventing premature scale-down. A 60-second stabilization cooldown window prevents rapid pod flapping.",
        body_style
    ))

    # 4. End-to-End Implementation Modules
    story.append(Paragraph("4. Core Implementation Modules on AWS", h1_style))
    story.append(Paragraph(
        "<b>4.1. Workloads (Web Microservice & Minecraft Server):</b><br/>"
        "• <i>Stateless Web App:</i> FastAPI REST service exposing <code>/workload</code> (computes synthetic CPU load) and <code>/metrics</code> (Prometheus client). Configured with <code>cpu: 100m, memory: 128Mi</code> requests and <code>cpu: 500m, memory: 256Mi</code> limits.<br/>"
        "• <i>Stateful Gaming (Minecraft):</i> Deployed as a Kubernetes <code>StatefulSet</code> with AWS EBS gp3 volume. Serves real Minecraft protocol traffic to evaluate co-located cluster resource contention under stateful conditions.",
        body_style
    ))
    story.append(Paragraph(
        "<b>4.2. In-Cluster Metrics Pipeline:</b><br/>"
        "Prometheus scrapes application metrics every 5 seconds. The controller uses the following PromQL queries:<br/>"
        "• <i>P95 Latency:</i> <code>histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[1m])) by (le)) * 1000</code><br/>"
        "• <i>Pod CPU:</i> <code>sum(rate(container_cpu_usage_seconds_total{container='webapp'}[1m])) / sum(kube_pod_container_resource_requests{resource='cpu'}) * 100</code>",
        body_style
    ))
    story.append(Paragraph(
        "<b>4.3. Autonomous Adaptive Controller Daemon (Python In-Cluster Operator):</b><br/>"
        "Runs as a Kubernetes Deployment with RBAC permissions to patch HPA resources. Real operational code:",
        body_style
    ))

    code_text = (
        "import time, requests\n"
        "from kubernetes import client, config\n\n"
        "config.load_incluster_config()\n"
        "hpa_api = client.AutoscalingV2Api()\n"
        "PROM = 'http://prometheus-server.monitoring.svc.cluster.local'\n\n"
        "def run_control_cycle(slo_ms=200, current_target=70):\n"
        "    query = 'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[1m])) by (le)) * 1000'\n"
        "    resp = requests.get(f'{PROM}/api/v1/query', params={'query': query}).json()\n"
        "    p95 = float(resp['data']['result'][0]['value'][1])\n"
        "    if p95 >= slo_ms * 1.5: current_target = max(40, current_target - 7.5)\n"
        "    elif p95 >= slo_ms * 1.2: current_target = max(40, current_target - 5.0)\n"
        "    elif p95 < slo_ms * 0.8: current_target = min(85, current_target + 1.0)\n"
        "    body = [{'op': 'replace', 'path': '/spec/metrics/0/resource/target/averageUtilization', 'value': int(current_target)}]\n"
        "    hpa_api.patch_namespaced_horizontal_pod_autoscaler('webapp-hpa', 'sla-autoscaling', body)\n"
        "    return current_target"
    )
    story.append(Preformatted(code_text, code_style))

    # ==================== PAGE 3 ====================
    story.append(PageBreak())

    # 5. Scientific Evaluation Metrics
    story.append(Paragraph("5. Scientific Evaluation & Comparative Experiments", h1_style))
    story.append(Paragraph(
        "To rigorously validate the adaptive autoscaler, paired test runs execute identical Locust load profiles across two configurations: (1) Conventional HPA with fixed 70% CPU threshold, and (2) SLA-Adaptive HPA.",
        body_style
    ))

    eval_data = [
        [
            Paragraph("Evaluation Metric", table_cell_header),
            Paragraph("Formula / Measurement Method", table_cell_header),
            Paragraph("Expected Research Finding", table_cell_header)
        ],
        [
            Paragraph("<b>SLO Violation Rate (%)</b>", table_cell_style),
            Paragraph("<i>(Violated time steps / Total time steps) &times; 100</i>", table_cell_style),
            Paragraph("&gt; 50% reduction in SLA violations during flash crowds.", table_cell_style)
        ],
        [
            Paragraph("<b>P95 Latency Degradation</b>", table_cell_style),
            Paragraph("Peak P95 latency recorded during workload transitions.", table_cell_style),
            Paragraph("Peak latency remains constrained within the warning band.", table_cell_style)
        ],
        [
            Paragraph("<b>Scaling Delay (Lag)</b>", table_cell_style),
            Paragraph("Seconds from traffic surge start until pod readiness.", table_cell_style),
            Paragraph("Proactive threshold lowering reduces lag by 20-30 seconds.", table_cell_style)
        ],
        [
            Paragraph("<b>Replica Efficiency & Cost</b>", table_cell_style),
            Paragraph("Average pod count & AWS EC2 instance hours consumed.", table_cell_style),
            Paragraph("Higher threshold during idle periods lowers cloud infrastructure cost.", table_cell_style)
        ],
        [
            Paragraph("<b>Controller Flapping</b>", table_cell_style),
            Paragraph("Count of scale-up / scale-down oscillating events.", table_cell_style),
            Paragraph("Asymmetric damping prevents excessive churn.", table_cell_style)
        ]
    ]
    eval_table = Table(eval_data, colWidths=[120, 202, 200])
    eval_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('BOX', (0,0), (-1,-1), 1, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_bg]),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(eval_table)
    story.append(Spacer(1, 4))

    # 6. Step-by-Step Implementation Roadmap
    story.append(Paragraph("6. Step-by-Step Implementation Roadmap (Phases 1 to 5)", h1_style))

    phases = [
        ("Phase 1: AWS Infrastructure Provisioning (Days 1 - 2)",
         "• Launch AWS VPC (2 public subnets, Internet Gateway, Security Groups for K8s ports 6443, 80, 443).<br/>"
         "• Provision 2x <code>t3.medium</code> Ubuntu 22.04 EC2 instances (1 Master, 1 Worker) or 1 EKS cluster.<br/>"
         "• Install K3s using <code>curl -sfL https://get.k3s.io | sh -</code> and install Kubernetes Metrics Server.<br/>"
         "• Verify cluster health: <code>kubectl get nodes -o wide</code>."),

        ("Phase 2: Observability Stack Deployment (Days 3 - 4)",
         "• Deploy Prometheus and Grafana via Helm: <code>helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring --create-namespace</code>.<br/>"
         "• Configure Prometheus ServiceMonitor to scrape the web app's <code>/metrics</code> endpoint every 5s.<br/>"
         "• Create Grafana dashboards visualizing real-time Pod CPU, Memory, Request Rate, and Latency quantiles."),

        ("Phase 3: Workload Containerization & Deployment (Days 5 - 6)",
         "• Build Docker image for the target web application instrumented with Prometheus client metrics.<br/>"
         "• Push image to AWS ECR; deploy <code>webapp-deployment.yaml</code> and <code>webapp-hpa.yaml</code> in namespace <code>sla-autoscaling</code>.<br/>"
         "• Deploy stateful Minecraft game server StatefulSet with AWS EBS gp3 volume for real-world background workload benchmarking."),

        ("Phase 4: Adaptive Controller Daemon Build & In-Cluster Deployment (Days 7 - 9)",
         "• Refactor <code>backend/app/autoscaler/adaptive_controller.py</code> and <code>backend/app/metrics/prometheus.py</code> to execute against live Prometheus.<br/>"
         "• Apply RBAC manifests (ClusterRole, ClusterRoleBinding, ServiceAccount) granting HPA patch permissions.<br/>"
         "• Deploy the controller container to Kubernetes; verify active threshold patching with <code>kubectl get hpa -w</code>."),

        ("Phase 5: Locust Load Testing, Benchmarking & Research Report (Days 10 - 12)",
         "• Deploy Locust on an external EC2 instance; execute Ramp, Spike, and Sawtooth test profiles against the application.<br/>"
         "• Run Test Series A (Fixed 70% HPA) and Test Series B (SLA-Adaptive HPA) under identical traffic seeds.<br/>"
         "• Export Prometheus telemetry to CSV; generate comparative graphs (SLO violations, P95 latency, replica efficiency).<br/>"
         "• Connect CloudScale Lab frontend to the live AWS backend for live project demonstration.")
    ]

    for title, desc in phases:
        story.append(Paragraph(f"<b>{title}</b>", h2_style))
        story.append(Paragraph(desc, body_style))

    story.append(Spacer(1, 4))
    summary_box = [
        [
            Paragraph("<b>Final Deliverables Checklist:</b><br/>"
                      "&check; <b>Running AWS Kubernetes Cluster</b> with live Prometheus & Grafana telemetry.<br/>"
                      "&check; <b>Adaptive Controller Daemon</b> actively modulating HPA thresholds based on live P95 latency.<br/>"
                      "&check; <b>Empirical Dataset (CSV/JSON)</b> comparing Fixed HPA vs SLA-Adaptive HPA across 4 workload patterns.<br/>"
                      "&check; <b>CloudScale Lab Web UI</b> integrated with live AWS metrics for interactive demonstration.<br/>"
                      "&check; <b>Final Academic Project Report</b> containing architecture diagrams, methodology, and results.", callout_style)
        ]
    ]
    sum_table = Table(summary_box, colWidths=[522])
    sum_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), light_bg),
        ('BOX', (0,0), (-1,-1), 1, secondary_color),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(sum_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF successfully built: {filename}")

if __name__ == "__main__":
    output_path = sys.argv[1] if len(sys.argv) > 1 else "docs/SLA_Adaptive_Autoscaling_AWS_Implementation_Plan.pdf"
    build_pdf(output_path)
