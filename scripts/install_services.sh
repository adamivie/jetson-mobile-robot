#!/bin/bash
# install_services.sh — install and enable robot systemd user services
# Run once on the Jetson: bash ~/install_services.sh
set -e

UNIT_DIR="$HOME/.config/systemd/user"
mkdir -p "$UNIT_DIR"

echo "==> Installing service files..."
cp ~/robot-foxglove.service "$UNIT_DIR/robot-foxglove.service"
cp ~/robot-lidar.service    "$UNIT_DIR/robot-lidar.service"

echo "==> Enabling systemd user linger (services start at boot without login)..."
sudo loginctl enable-linger "$USER"

echo "==> Reloading systemd user daemon..."
systemctl --user daemon-reload

echo "==> Enabling services..."
systemctl --user enable robot-foxglove.service
systemctl --user enable robot-lidar.service

echo ""
echo "==> Done. Services will autostart on next boot."
echo "    To start them now:"
echo "      systemctl --user start robot-foxglove"
echo "      systemctl --user start robot-lidar"
echo ""
echo "    Useful commands:"
echo "      systemctl --user status robot-foxglove"
echo "      systemctl --user status robot-lidar"
echo "      journalctl --user -u robot-foxglove -f"
echo "      journalctl --user -u robot-lidar -f"
echo "      systemctl --user restart robot-foxglove"
echo "      systemctl --user stop robot-lidar"
