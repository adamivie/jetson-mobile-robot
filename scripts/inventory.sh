#!/bin/bash
echo "=== HELD PACKAGES ==="
apt-mark showhold

echo ""
echo "=== ROS2 HUMBLE PACKAGES ==="
dpkg -l | grep ros-humble | awk '{print $2, $3}' | sort

echo ""
echo "=== PYTHON PACKAGES (key) ==="
python3 -c "import scipy; print('scipy', scipy.__version__)"
python3 -c "import cv2; print('cv2', cv2.__version__)" 2>/dev/null || echo "cv2: not directly importable (ok)"

echo ""
echo "=== UDEV RULES ==="
cat /etc/udev/rules.d/99-rplidar.rules 2>/dev/null || echo "none"

echo ""
echo "=== NETWORK ==="
ip -4 addr show | grep inet | grep -v 127
