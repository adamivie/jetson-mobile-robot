#!/bin/bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash 2>/dev/null
export AMENT_PREFIX_PATH="$HOME/ros2_ws/install/robot_vision:$AMENT_PREFIX_PATH"
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

echo "=== STORAGE ==="
df -h /

echo ""
echo "=== ROS2 PACKAGES ==="
ros2 pkg list | grep -E "robot_vision|realsense"

echo ""
echo "=== EXECUTABLES ==="
ros2 pkg executables robot_vision

echo ""
echo "=== AMENT_PREFIX_PATH ==="
echo $AMENT_PREFIX_PATH

echo ""
echo "=== WORKSPACE ==="
ls ~/ros2_ws/install/

echo ""
echo "=== BASHRC (last 8 lines) ==="
tail -8 ~/.bashrc
