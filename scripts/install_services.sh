#!/bin/bash
# install_services.sh — install and enable robot systemd user services
# Run once on the Jetson: bash ~/install_services.sh
set -e

UNIT_DIR="$HOME/.config/systemd/user"
mkdir -p "$UNIT_DIR"

echo "==> Installing service files..."
cp ~/robot-foxglove.service "$UNIT_DIR/robot-foxglove.service"
cp ~/robot-lidar.service    "$UNIT_DIR/robot-lidar.service"
cp ~/robot-mavros.service   "$UNIT_DIR/robot-mavros.service"
cp ~/robot-drive.service    "$UNIT_DIR/robot-drive.service"
cp ~/robot-slam.service     "$UNIT_DIR/robot-slam.service"

echo "==> Enabling systemd user linger (services start at boot without login)..."
sudo loginctl enable-linger "$USER"

echo "==> Reloading systemd user daemon..."
systemctl --user daemon-reload

echo "==> Enabling services..."
systemctl --user enable robot-foxglove.service
systemctl --user enable robot-lidar.service
systemctl --user enable robot-mavros.service
systemctl --user enable robot-drive.service
# robot-slam is installed but NOT auto-enabled — it conflicts with robot-lidar.
# Enable one or the other:  systemctl --user enable robot-slam  (disables lidar-only)
#                            systemctl --user enable robot-lidar (lidar without SLAM)
echo "    NOTE: robot-slam.service installed but not enabled by default."
echo "          It conflicts with robot-lidar (both own /dev/ydlidar)."
echo "          To switch to SLAM mode run: bash ~/use_slam.sh"

echo ""
echo "==> Done. Services will autostart on next boot."
echo "    To start them now:"
echo "      systemctl --user start robot-foxglove"
echo "      systemctl --user start robot-lidar"
echo "      systemctl --user start robot-mavros"
echo "      systemctl --user start robot-drive"
echo ""
echo "    Useful commands:"
echo "      systemctl --user status robot-foxglove"
echo "      systemctl --user status robot-lidar"
echo "      systemctl --user status robot-mavros"
echo "      systemctl --user status robot-drive"
echo "      journalctl --user -u robot-foxglove -f"
echo "      journalctl --user -u robot-lidar -f"
echo "      journalctl --user -u robot-mavros -f"
echo "      journalctl --user -u robot-drive -f"
echo "      systemctl --user restart robot-foxglove"
echo "      systemctl --user stop robot-lidar"
echo "      systemctl --user stop robot-mavros"
echo "      systemctl --user stop robot-drive"
