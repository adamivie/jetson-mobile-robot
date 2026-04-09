from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('device',       default_value='/dev/pixhawk'),
        DeclareLaunchArgument('baud',         default_value='115200'),
        DeclareLaunchArgument('max_linear',   default_value='1.0'),
        DeclareLaunchArgument('max_angular',  default_value='1.0'),
        DeclareLaunchArgument('override_hz',  default_value='20.0'),
        DeclareLaunchArgument('cmd_timeout',  default_value='0.5'),

        Node(
            package='robot_vision',
            executable='mecanum_drive_node',
            name='mecanum_drive_node',
            output='screen',
            parameters=[{
                'device':      LaunchConfiguration('device'),
                'baud':        LaunchConfiguration('baud'),
                'max_linear':  LaunchConfiguration('max_linear'),
                'max_angular': LaunchConfiguration('max_angular'),
                'override_hz': LaunchConfiguration('override_hz'),
                'cmd_timeout': LaunchConfiguration('cmd_timeout'),
            }],
        ),
    ])
