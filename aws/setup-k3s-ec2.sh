#!/usr/bin/env bash
set -euo pipefail

echo "=========================================================="
echo "SLA-Adaptive Autoscaling: AWS EC2 K3s Cluster Provisioner"
echo "Target OS: Ubuntu 22.04 / 24.04 LTS on AWS EC2"
echo "=========================================================="

# 1. Update and install prerequisites
echo "[1/6] Updating system packages..."
sudo apt-get update -y
sudo apt-get install -y curl wget git apt-transport-https ca-certificates gnupg lsb-release

# 2. Install K3s (Lightweight Kubernetes)
echo "[2/6] Installing K3s..."
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--write-kubeconfig-mode 644" sh -

# Configure local kubeconfig
mkdir -p "$HOME/.kube"
sudo cp /etc/rancher/k3s/k3s.yaml "$HOME/.kube/config"
sudo chown "$(id -u):$(id -g)" "$HOME/.kube/config"
export KUBECONFIG="$HOME/.kube/config"

echo "Kubernetes nodes ready:"
kubectl get nodes -o wide

# 3. Install Helm 3
echo "[3/6] Installing Helm 3..."
if ! command -v helm &> /dev/null; then
    curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
fi

# 4. Install Kubernetes Metrics Server (Required for HPA CPU metrics)
echo "[4/6] Installing Kubernetes Metrics Server..."
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml || true
# Allow insecure TLS in test environment for metrics-server
kubectl patch deployment metrics-server -n kube-system --type='json' \
  -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]' || true

# 5. Deploy Prometheus & Grafana stack via Helm
echo "[5/6] Deploying Prometheus & Grafana Observability Stack..."
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
  --set prometheus.service.type=NodePort \
  --set prometheus.service.nodePort=30090 \
  --set grafana.service.type=NodePort \
  --set grafana.service.nodePort=30030

# 6. Verify installation
echo "[6/6] Verifying cluster deployments..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=prometheus -n monitoring --timeout=180s || true

echo "=========================================================="
echo "Cluster Bootstrap Complete!"
echo "Prometheus NodePort:  http://<EC2-PUBLIC-IP>:30090"
echo "Grafana NodePort:     http://<EC2-PUBLIC-IP>:30030 (admin / prom-operator)"
echo "Next step: Run ./aws/deploy-all.sh to deploy the application and adaptive controller."
echo "=========================================================="
