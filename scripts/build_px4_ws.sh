#!/bin/bash
# Build micro_ros_agent and px4_msgs from source in ~/px4_ws
# Run once after PX4/Pixhawk arrives. Safe to re-run.
set -e

source /opt/ros/humble/setup.bash

WS=~/px4_ws
mkdir -p $WS/src
cd $WS

echo "=== Cloning px4_msgs ==="
if [ ! -d src/px4_msgs ]; then
  git clone https://github.com/PX4/px4_msgs.git src/px4_msgs --branch release/1.14 --depth 1
fi

echo "=== Cloning micro_ros_agent ==="
if [ ! -d src/micro_ros_agent ]; then
  git clone https://github.com/micro-ROS/micro-ROS-Agent.git src/micro_ros_agent --branch humble --depth 1
fi

echo "=== Installing build deps ==="
sudo apt-get install -y \
  python3-colcon-common-extensions \
  python3-pip \
  ros-humble-rmw-cyclonedds-cpp

pip3 install --user -q catkin_pkg empy lark

echo "=== Building (this takes ~5-10 min) ==="
cd $WS
colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release --symlink-install 2>&1

echo ""
echo "=== Done. Add to ~/.bashrc: ==="
echo "[ -f ~/px4_ws/install/setup.bash ] && source ~/px4_ws/install/setup.bash"
echo ""
echo "=== To start the agent (UDP, default PX4 ethernet port): ==="
echo "ros2 run micro_ros_agent micro_ros_agent udp4 --port 8888"
