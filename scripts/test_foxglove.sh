#!/bin/bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash 2>/dev/null
export AMENT_PREFIX_PATH="$HOME/ros2_ws/install/robot_vision:$AMENT_PREFIX_PATH"
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

ros2 launch robot_vision foxglove.launch.py &
sleep 5
echo "=== Port check ==="
ss -tlnp | grep 8765
echo "=== Log ==="
cat /tmp/foxglove.log 2>/dev/null || echo "(no log file)"
