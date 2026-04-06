#!/bin/bash
set -e

echo "=== Holding NVIDIA/JetPack/CUDA/TensorRT packages ==="
sudo apt-mark hold \
  nvidia-l4t-kernel \
  nvidia-l4t-kernel-dtbs \
  nvidia-l4t-kernel-headers \
  nvidia-l4t-kernel-oot-modules \
  nvidia-l4t-kernel-oot-headers \
  cuda-toolkit-12-6 \
  cuda-toolkit-12 \
  tensorrt \
  libcudnn9-cuda-12 \
  cudnn-local-tegra-repo-ubuntu2204-9.3.0 \
  l4t-cuda-tegra-repo-ubuntu2204-12-6-local

echo ""
echo "=== Currently held packages ==="
apt-mark showhold

echo ""
echo "=== Running apt update ==="
sudo apt-get update

echo ""
echo "=== Packages that will be upgraded (preview) ==="
apt list --upgradable 2>/dev/null | grep -v WARNING

echo ""
echo "=== Running apt upgrade ==="
sudo apt-get upgrade -y

echo ""
echo "=== Running apt autoremove ==="
sudo apt-get autoremove -y

echo ""
echo "=== Storage after upgrade ==="
df -h /

echo ""
echo "=== Done. Held packages (still pinned): ==="
apt-mark showhold
