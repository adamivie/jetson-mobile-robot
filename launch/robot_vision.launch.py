"""
robot_vision.launch.py
Launches: RealSense D455 → depth_processor → obstacle_detector
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('stop_distance_m', default_value='0.6',
                              description='Obstacle stop distance in metres'),

        Node(
            package='realsense2_camera',
            executable='realsense2_camera_node',
            name='camera',
            namespace='camera',
            parameters=[{
                'enable_color': True,
                'enable_depth': True,
                'enable_infra1': False,
                'enable_infra2': False,
                'depth_module.profile': '640x480x30',
                'rgb_camera.profile': '640x480x30',
                'align_depth.enable': True,
                'pointcloud.enable': True,
            }],
            output='screen',
        ),

        Node(
            package='robot_vision',
            executable='depth_processor',
            name='depth_processor',
            parameters=[{
                'depth_topic': '/camera/camera/depth/image_rect_raw',
                'roi_width_frac': 0.3,
                'roi_height_frac': 0.4,
                'min_valid_depth_m': 0.3,
                'max_valid_depth_m': 6.0,
            }],
            output='screen',
        ),

        Node(
            package='robot_vision',
            executable='obstacle_detector',
            name='obstacle_detector',
            parameters=[{
                'stop_distance_m': LaunchConfiguration('stop_distance_m'),
            }],
            output='screen',
        ),
    ])
