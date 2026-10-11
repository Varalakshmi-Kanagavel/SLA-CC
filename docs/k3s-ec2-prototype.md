# CloudScale workload on the existing K3s EC2 node

This is a reviewable first-deployment procedure for the benchmark workload only. It does not install monitoring, create an HPA, apply any manifest, or change AWS. The commands are split by machine. Run the Windows commands on the development laptop and the EC2 commands in an SSH session on the Ubuntu K3s host.

## Images in this repository

| Purpose | Build context and Dockerfile | Image | Needed now? |
| --- | --- | --- | --- |
| Benchmark FastAPI workload | `workload-app/`, `workload-app/Dockerfile` | `cloudscale-workload:prototype` | Yes. This is the pod targeted by the Kubernetes Deployment and Service. |
| Adaptive controller | `backend/`, `backend/Dockerfile.controller` | `cloudscale-controller:prototype` | No. Keep it for a later phase after Prometheus and the controller's live behavior are verified. |
| CloudScale research API | `backend/`, `backend/Dockerfile` | `cloudscale-api:prototype` | Not part of this K3s workload-only deployment. It is the simulation/research API, not the benchmark target workload. |
| Dashboard | `frontend/`, `frontend/Dockerfile` | No production image defined; current Dockerfile runs Vite dev server | Not needed for the benchmark pod. |

There is also an older controller implementation under `controller/Dockerfile`; the current numbered Kubernetes controller manifest uses `backend/Dockerfile.controller`. Do not substitute those images without deciding which controller implementation is intended.

If you later prepare that controller image on Windows, its exact build command is:

```powershell
docker build --platform linux/amd64 -f .\backend\Dockerfile.controller -t cloudscale-controller:prototype .\backend
```

Do not transfer or deploy it in this workload-only phase. It needs a reachable Prometheus API and the controller's write-enabled Kubernetes configuration before it can manage an HPA; neither is set up here.

The target app in `workload-app/app.py` listens on port 8080, implements `GET /health`, exposes Prometheus client metrics at `GET /metrics`, and offers `GET /workload` to generate CPU and latency load. The metrics include the `http_request_duration_seconds` histogram buckets expected by the controller query. The CloudScale research API's health endpoint is `/api/health`; that is a different service and is not used for these probes.

The workload Deployment is deliberately one replica at first. It requests 100m CPU and 128Mi memory and is limited to 500m CPU and 256Mi memory. These are cautious starting values for a lightweight Python service on the described 2 GiB node; observe actual use before increasing replicas or enabling an HPA. `/workload` defaults to CPU hashing plus a 10 ms sleep; use low request concurrency initially because CPU is capped at 500m.

## 1. Windows laptop: build, smoke-test, and export

Run in PowerShell from the project root (`C:\Varu_Workspace\Projects\cc-project`). Docker Desktop must be running. The EC2 `t3.small` is x86_64, so explicitly build a Linux amd64 image.

```powershell
docker build --platform linux/amd64 -f .\workload-app\Dockerfile -t cloudscale-workload:prototype .\workload-app
docker run --rm -d --name cloudscale-workload -p 18080:8080 cloudscale-workload:prototype
$health = Invoke-RestMethod http://localhost:18080/health
if ($health.status -ne 'ok') { throw 'Workload /health did not return status=ok' }
$metrics = Invoke-WebRequest http://localhost:18080/metrics
if ($metrics.StatusCode -ne 200 -or $metrics.Content -notmatch 'http_request_duration_seconds_bucket') { throw 'Workload /metrics check failed' }
Invoke-RestMethod 'http://localhost:18080/workload?iterations=15000&sleep_ms=10'
docker rm -f cloudscale-workload
docker save -o .\cloudscale-workload-prototype.tar cloudscale-workload:prototype
Get-Item .\cloudscale-workload-prototype.tar | Select-Object Name,Length
```

Expected smoke-test results: `/health` returns `status: ok`; `/metrics` returns HTTP 200 and Prometheus text; `/workload` returns `status: completed`. The resulting tar archive contains the workload image only. It contains no credentials or private keys.

## 2. Transfer the archive to EC2

The simplest path is SCP if the laptop can reach the EC2 public or private address over SSH and the existing security group/network permits TCP 22 from the laptop's current public IP. In the same PowerShell session used for both SCP commands below, set these variables once, replacing the DNS/IP with the address you already use for SSH. Ubuntu EC2 images commonly use `ubuntu`; use your configured SSH username if different. The SSH key must already be available to your SSH client or agent; never put it into the repository or image.

```powershell
$Ec2User = 'ubuntu'
$Ec2Host = 'REPLACE_WITH_EC2_PUBLIC_DNS_OR_REACHABLE_IP'
$SshTarget = "${Ec2User}@${Ec2Host}"
scp .\cloudscale-workload-prototype.tar "${SshTarget}:/tmp/cloudscale-workload-prototype.tar"
```

If the laptop cannot reach EC2, this command will not work. Use an already-approved transfer route, such as uploading the archive to an existing private S3 bucket and downloading it from EC2 using its existing authorized IAM role, or use a bastion/VPN already available to you. This guide does not create a bucket, change security groups, or assume any such route exists. Keep the archive private and remove it from the transfer location after import.

## 3. EC2 host: inspect capacity and import

Run these commands in the Ubuntu SSH session. They inspect the host and import the image; they do not change AWS infrastructure or create Kubernetes resources.

```bash
df -h /
free -h
sudo k3s kubectl get nodes -o wide
```

K3s uses containerd; specify the `k8s.io` containerd namespace explicitly so kubelet can see the imported image. This is the `k3s ctr` form of K3s' documented `ctr -n k8s.io` image management.

```bash
sudo k3s ctr -n k8s.io images import /tmp/cloudscale-workload-prototype.tar
sudo k3s ctr -n k8s.io images ls | grep 'cloudscale-workload'
rm /tmp/cloudscale-workload-prototype.tar
```

Confirm the node is `Ready` and has enough free disk before importing. With the described 2.9 GB free, this small Python workload image should fit: it uses `python:3.11-slim` plus FastAPI, Uvicorn, and prometheus-client, so the archive and extracted layers should consume a few hundred MB rather than gigabytes. The exact archive size is reported on Windows by `Get-Item`; K3s temporarily needs room for both the uploaded archive and extracted image layers, so recheck `df -h /` immediately before import. Remove the archive after verifying the image. If K3s is multi-node, import the image on every node that could run this pod; this one-node procedure assumes the described single EC2 K3s node. The Deployment uses `imagePullPolicy: Never`, so Kubernetes will fail clearly rather than trying a public registry if the image is absent.

## 4. EC2 host: review and deploy the workload only

First, from Windows PowerShell at the project root, copy the three reviewed manifests. This is separate from the image transfer above and needs the same existing SSH path:

```powershell
scp .\k8s\00-namespace.yaml .\k8s\02-webapp-deployment.yaml .\k8s\03-webapp-service.yaml "${SshTarget}:/tmp/"
```

These are the proposed live-deployment commands for the EC2 SSH session. Review the files and commands first; no command below has been run as part of preparation. The namespace file is included because the other two manifests target `sla-autoscaling`.

```bash
sudo k3s kubectl apply -f /tmp/00-namespace.yaml
sudo k3s kubectl apply -f /tmp/02-webapp-deployment.yaml
sudo k3s kubectl apply -f /tmp/03-webapp-service.yaml
```

The Deployment starts one pod and the Service is `ClusterIP`, so it is not directly exposed to the internet. No HPA, Prometheus, Grafana, controller, ingress, or AWS resource is created by these three manifests.

## 5. EC2 host: verify the deployment and endpoints

```bash
sudo k3s kubectl -n sla-autoscaling rollout status deployment/webapp-deployment --timeout=120s
sudo k3s kubectl -n sla-autoscaling get pods -o wide
sudo k3s kubectl -n sla-autoscaling get deployment,service,endpoints
sudo k3s kubectl -n sla-autoscaling describe pod -l app=webapp
```

In one EC2 terminal, start a temporary local port-forward:

```bash
sudo k3s kubectl -n sla-autoscaling port-forward service/webapp-service 18080:8080
```

In a second EC2 terminal, call the forwarded Service:

```bash
curl -fsS http://127.0.0.1:18080/health
curl -fsS http://127.0.0.1:18080/metrics | head
curl -fsS 'http://127.0.0.1:18080/workload?iterations=15000&sleep_ms=10'
```

Stop the port-forward with Ctrl+C. Check that `/health` returns 200, `/metrics` includes `http_request_duration_seconds_bucket`, the workload request completes, the pod is Ready, and the Service has an endpoint. `metrics-server` can be checked with `sudo k3s kubectl top pod -n sla-autoscaling` after the pod has been running long enough to collect samples; this is not a Prometheus installation.

## Pending before autoscaling research runs

The workload-only smoke test does not validate autoscaling. Prometheus is absent on the reported cluster, so the adaptive controller's configured Prometheus URL will not resolve until an operator separately installs/configures Prometheus. Do not deploy the controller or either HPA yet. Next, validate scrape configuration and the histogram query, then test the conventional HPA and adaptive controller as separate runs, recording CPU, P95 latency, replicas, and SLO violations. The current HPA manifests request a minimum of two replicas and can reach twelve; those settings need a resource-capacity review for a 2 GiB node before any HPA test.
