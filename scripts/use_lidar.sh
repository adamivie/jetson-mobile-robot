#!/bin/bash
# use_lidar.sh — switch back from SLAM mode to lidar-only mode
export XDG_RUNTIME_DIR=/run/user/$(id -u)
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus

echo "==> Stopping robot-slam..."
systemctl --user stop robot-slam || true
systemctl --user disable robot-slam || true

echo "==> Enabling + starting robot-lidar..."
systemctl --user enable robot-lidar
systemctl --user start robot-lidar

echo ""
echo "==> Done. Lidar-only mode active."
echo "    systemctl --user status robot-lidar"
