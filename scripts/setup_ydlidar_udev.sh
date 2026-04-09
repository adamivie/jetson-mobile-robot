#!/usr/bin/env bash
# setup_ydlidar_udev.sh
# Writes a persistent udev rule for YDLidar 4ROS using CP2102 VID/PID.
# Stable across USB port changes (does NOT use KERNELS path).

set -e

echo "=== YDLidar 4ROS udev setup ==="

# CP2102 USB-Serial VID:PID — Silicon Labs 10c4:ea60
VID="10c4"
PID="ea60"

# Verify the device is present
if ! lsusb | grep -qi "10c4:ea60\|Silicon Labs"; then
  echo "ERROR: No CP2102 (Silicon Labs 10c4:ea60) found. Plug in the YDLidar first."
  exit 1
fi

echo "Found CP2102 (Silicon Labs 10c4:ea60)"

RULE_FILE="/etc/udev/rules.d/99-ydlidar.rules"
echo "Writing udev rule to $RULE_FILE ..."
sudo tee "$RULE_FILE" > /dev/null <<'EOF'
# YDLidar 4ROS (EAI 4ROS) — CP2102 USB-Serial (Silicon Labs 10c4:ea60)
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", SYMLINK+="ydlidar", MODE="0666", GROUP="dialout"
EOF

# Add user to dialout group if needed
if ! groups | grep -q dialout; then
  echo "Adding $(whoami) to dialout group..."
  sudo usermod -aG dialout "$(whoami)"
  echo "NOTE: Log out and back in (or: newgrp dialout) for group change to take effect."
fi

# Reload and trigger udev
sudo udevadm control --reload-rules
sudo udevadm trigger
sleep 1

# Verify
if [ -e /dev/ydlidar ]; then
  echo ""
  echo "SUCCESS: /dev/ydlidar -> $(readlink /dev/ydlidar)"
  echo ""
  echo "Test with:"
  echo "  ros2 launch robot_vision lidar.launch.py"
  echo "  ros2 topic echo /scan --once"
else
  echo "WARNING: /dev/ydlidar symlink not created. Try replugging the USB cable."
fi
