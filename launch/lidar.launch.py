#!/usr/bin/env python3
"""
Launch the YDLidar 4ROS (EAI 4ROS / TOF) LiDAR node.

Usage:
  ros2 launch robot_vision lidar.launch.py
  ros2 launch robot_vision lidar.launch.py port:=/dev/ttyUSB0

Topic published: /scan  (sensor_msgs/LaserScan)
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('robot_vision')
    params_file = os.path.join(pkg_share, 'config', 'ydlidar_4ros.yaml')

    port_arg = DeclareLaunchArgument(
        'port',
        default_value='/dev/ydlidar',
        description='Serial port for YDLidar 4ROS (e.g. /dev/ttyUSB0 or /dev/ydlidar)'
    )

    lidar_node = Node(
        package='ydlidar_ros2_driver',
        executable='ydlidar_ros2_driver_node',
        name='ydlidar_node',
        output='screen',
        parameters=[
            params_file,
            {'port': LaunchConfiguration('port')}
        ],
    )

    return LaunchDescription([
        port_arg,
        lidar_node,
    ])
