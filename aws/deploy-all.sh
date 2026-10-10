#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================================="
echo "Deploying SLA-Adaptive Autoscaler Suite to Kubernetes"
echo "=========================================================="

# 1. Build and import local Docker images into K3s (or push to registry)
echo "[1/4] Building container images..."
if command -v docker &> /dev/null; then
    docker build -t sla-cc-workload:latest "$ROOT_DIR/workload-app"
    docker build -t sla-cc-controller:latest "$ROOT_DIR/controller"

    # If running on K3s, import docker images into containerd
    if command -v k3s &> /dev/null; then
        echo "Importing images into K3s containerd cache..."
        docker save sla-cc-workload:latest | sudo k3s ctr images import -
        docker save sla-cc-controller:latest | sudo k3s ctr images import -
    fi
fi

# 2. Apply manifests in sequential order
echo "[2/4] Applying Kubernetes manifests..."
kubectl apply -f "$ROOT_DIR/k8s/00-namespace.yaml"
kubectl apply -f "$ROOT_DIR/k8s/01-rbac.yaml"
kubectl apply -f "$ROOT_DIR/k8s/02-webapp-deployment.yaml"
kubectl apply -f "$ROOT_DIR/k8s/03-webapp-service.yaml"
kubectl apply -f "$ROOT_DIR/k8s/04-webapp-hpa.yaml"
kubectl apply -f "$ROOT_DIR/k8s/05-controller-deployment.yaml"
kubectl apply -f "$ROOT_DIR/k8s/07-servicemonitor.yaml"

# 3. Optional Minecraft workload prompt
read -p "Deploy stateful Minecraft workload for resource contention benchmarking? [y/N]: " -n 1 -r || true
echo
if [[ ${REPLY:-n} =~ ^[Yy]$ ]]; then
    echo "Deploying Minecraft Server StatefulSet..."
    kubectl apply -f "$ROOT_DIR/k8s/06-minecraft-statefulset.yaml"
fi

# 4. Wait and display status
echo "[3/4] Waiting for pods to become ready..."
kubectl rollout status deployment/webapp-deployment -n sla-autoscaling --timeout=90s
kubectl rollout status deployment/adaptive-controller-deployment -n sla-autoscaling --timeout=90s

echo "[4/4] Current Deployment Status:"
kubectl get pods,hpa,svc -n sla-autoscaling

echo "=========================================================="
echo "Deployment successful!"
echo "Target Web Service: http://<NODE-IP>:30080"
echo "To follow controller logs: kubectl logs -f -l app=adaptive-controller -n sla-autoscaling"
echo "=========================================================="
