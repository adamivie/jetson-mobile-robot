#!/bin/bash
# Kill all processes started by the foxglove launch file
pkill -f foxglove_bridge 2>/dev/null
pkill -f jetson_stats_node 2>/dev/null
pkill -f "robot_vision/jetson_stats" 2>/dev/null   # installed executable name
pkill -f "ros2 run robot_vision jetson_stats" 2>/dev/null
pkill -f "ros2 launch robot_vision foxglove" 2>/dev/null
pkill -f test_foxglove 2>/dev/null
sleep 2
# Confirm everything is gone
REMAINING=$(pgrep -f "foxglove_bridge\|robot_vision/jetson_stats\|jetson_stats_node" | wc -l)
if [ "$REMAINING" -gt 0 ]; then
    echo "WARNING: $REMAINING process(es) still running — forcing SIGKILL"
    pkill -9 -f foxglove_bridge 2>/dev/null
    pkill -9 -f "robot_vision/jetson_stats" 2>/dev/null
    pkill -9 -f jetson_stats_node 2>/dev/null
    sleep 1
fi
ss -tlnp | grep 8765 && echo "WARNING: port still in use" || echo "port 8765 clear"
