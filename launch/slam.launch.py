#!/usr/bin/env python3
"""
SLAM launch — YDLidar 4ROS + slam_toolbox (async online mapping).

Publishes:
  /map          (nav_msgs/OccupancyGrid)  — live map, viewable in Foxglove 3D panel
  /map_metadata (nav_msgs/MapMetaData)
  /scan         (sensor_msgs/LaserScan)   — from lidar

TF tree:
  map → odom → base_link → laser
  (odom→base_link is identity until odometry source added)

Usage:
  ros2 launch robot_vision slam.launch.py
  ros2 launch robot_vision slam.launch.py port:=/dev/ttyUSB0
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('robot_vision')
    lidar_params  = os.path.join(pkg_share, 'config', 'ydlidar_4ros.yaml')
    slam_params   = os.path.join(pkg_share, 'config', 'slam_toolbox.yaml')

    return LaunchDescription([

        DeclareLaunchArgument('port', default_value='/dev/ydlidar',
                              description='YDLidar serial port'),
        DeclareLaunchArgument('use_sim_time', default_value='false'),

        # ── YDLidar 4ROS driver ──────────────────────────────────────────────
        Node(
            package='ydlidar_ros2_driver',
            executable='ydlidar_ros2_driver_node',
            name='ydlidar_ros2_driver_node',
            output='screen',
            parameters=[
                lidar_params,
                {'port': LaunchConfiguration('port')},
            ],
        ),

        # ── Static TF: base_link → laser (lidar centered, flat on robot) ────
        # Adjust x/y/z/yaw if lidar is offset from robot center
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='base_to_laser_tf',
            arguments=['0', '0', '0.1',   # x y z  (lidar 10cm above base)
                       '0', '0', '0',      # roll pitch yaw
                       'base_link', 'laser'],
            output='screen',
        ),

        # ── Static TF: odom → base_link (identity until odometry added) ─────
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='odom_to_base_tf',
            arguments=['0', '0', '0',
                       '0', '0', '0',
                       'odom', 'base_link'],
            output='screen',
        ),

        # ── slam_toolbox async online mapping ────────────────────────────────
        Node(
            package='slam_toolbox',
            executable='async_slam_toolbox_node',
            name='slam_toolbox',
            output='screen',
            parameters=[
                slam_params,
                {'use_sim_time': LaunchConfiguration('use_sim_time')},
            ],
        ),

    ])

