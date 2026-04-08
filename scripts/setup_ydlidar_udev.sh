#!/usr/bin/env bash
# setup_ydlidar_udev.sh
# Run AFTER plugging in the YDLidar 4ROS USB cable.
# Detects the CP2102 device, writes a persistent udev rule,
# and creates the /dev/ydlidar symlink.

set -e

echo "=== YDLidar 4ROS udev setup ==="

# Find the ttyUSB device for the CP2102 (Silicon Labs)
DEVICE=""
for dev in /dev/ttyUSB*; do
  if udevadm info -a -n "$dev" 2>/dev/null | grep -q "CP210"; then
    DEVICE="$dev"
    break
  fi
done

if [ -z "$DEVICE" ]; then
  echo "ERROR: No CP210x device found on /dev/ttyUSB*"
  echo "       Make sure the YDLidar 4ROS is plugged in and the CP2102 driver is loaded."
  echo "       Try: lsusb | grep -i 'silicon labs'"
  exit 1
fi

echo "Found CP210x on: $DEVICE"

# Get the KERNELS (USB path) value for a stable udev rule
KERNELS=$(udevadm info -a -n "$DEVICE" | grep KERNELS | head -2 | tail -1 | tr -d ' ' | cut -d'"' -f2)
echo "KERNELS (USB path): $KERNELS"

# Write udev rule
RULE_FILE="/etc/udev/rules.d/99-ydlidar.rules"
echo "Writing udev rule to $RULE_FILE ..."
sudo tee "$RULE_FILE" > /dev/null <<EOF
# YDLidar 4ROS (EAI 4ROS) — CP2102 USB-Serial
SUBSYSTEM=="tty", KERNELS=="$KERNELS", SYMLINK+="ydlidar", MODE="0666", GROUP="dialout"
EOF

# Add user to dialout group if needed
if ! groups | grep -q dialout; then
  echo "Adding $(whoami) to dialout group..."
  sudo usermod -aG dialout "$(whoami)"
  echo "NOTE: You will need to log out and back in (or run: newgrp dialout) for group change to take effect."
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
  echo "WARNING: /dev/ydlidar symlink not created yet."
  echo "Try unplugging and replugging the USB cable, then check: ls -la /dev/ydlidar"
fi
