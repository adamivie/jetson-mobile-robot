from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    slam_params = PathJoinSubstitution(
        [FindPackageShare('robot_vision'), 'config', 'slam_toolbox.yaml']
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),

        # RPLidar S2L driver
        Node(
            package='rplidar_ros',
            executable='rplidar_node',
            name='rplidar',
            parameters=[{
                'serial_port': '/dev/rplidar',
                'serial_baudrate': 1000000,
                'frame_id': 'laser',
                'inverted': False,
                'angle_compensate': True,
                'scan_mode': 'Standard',
            }],
            output='screen',
        ),

        # slam_toolbox in async online mapping mode
        Node(
            package='slam_toolbox',
            executable='async_slam_toolbox_node',
            name='slam_toolbox',
            parameters=[slam_params, {'use_sim_time': use_sim_time}],
            output='screen',
        ),

        # Foxglove bridge — connect at ws://192.168.3.72:8765
        Node(
            package='foxglove_bridge',
            executable='foxglove_bridge',
            name='foxglove_bridge',
            parameters=[{
                'port': 8765,
                'address': '0.0.0.0',
                'tls': False,
                'topic_whitelist': ['.*'],
                'param_whitelist': ['.*'],
                'max_qos_depth': 10,
                'num_threads': 4,
                'use_compression': False,
            }],
            output='screen',
        ),
    ])
