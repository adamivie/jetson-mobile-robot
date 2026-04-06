#!/bin/bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash 2>/dev/null
export AMENT_PREFIX_PATH="$HOME/ros2_ws/install/robot_vision:$AMENT_PREFIX_PATH"
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

nohup ros2 launch robot_vision foxglove.launch.py > ~/.ros/foxglove_bridge.log 2>&1 &
echo $! > ~/.ros/foxglove_bridge.pid
echo "Started foxglove_bridge (PID $(cat ~/.ros/foxglove_bridge.pid))"
sleep 3
tail -5 ~/.ros/foxglove_bridge.log
