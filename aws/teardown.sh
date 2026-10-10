#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "Tearing down SLA-CC resources from Kubernetes..."
kubectl delete -f "$ROOT_DIR/k8s/01-rbac.yaml" --ignore-not-found=true
kubectl delete namespace sla-autoscaling --ignore-not-found=true

echo "Cleanup complete."
