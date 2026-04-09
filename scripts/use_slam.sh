#!/bin/bash
# use_slam.sh — switch from lidar-only mode to SLAM mapping mode
# run once on the Jetson; persists across reboots
export XDG_RUNTIME_DIR=/run/user/$(id -u)
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus

echo "==> Stopping robot-lidar (conflicts with robot-slam)..."
systemctl --user stop robot-lidar || true
systemctl --user disable robot-lidar || true

echo "==> Enabling + starting robot-slam..."
systemctl --user enable robot-slam
systemctl --user start robot-slam

echo ""
echo "==> Done. SLAM mode active. Check status:"
echo "    systemctl --user status robot-slam"
echo "    journalctl --user -u robot-slam -f"
echo ""
echo "    Foxglove: ws://$(hostname -I | awk '{print $1}'):8765"
echo "    Import layout: foxglove/slam_dashboard.json"
