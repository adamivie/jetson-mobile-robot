from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    """
    Launch foxglove_bridge standalone.
    Connect from browser: https://app.foxglove.dev -> Open Connection -> WebSocket
    URL: ws://192.168.3.72:8765
    Or open Foxglove desktop app and use same URL.
    """
    port = LaunchConfiguration('port', default='8765')
    address = LaunchConfiguration('address', default='0.0.0.0')

    return LaunchDescription([
        DeclareLaunchArgument('port', default_value='8765',
                              description='WebSocket port for Foxglove Studio'),
        DeclareLaunchArgument('address', default_value='0.0.0.0',
                              description='Bind address (0.0.0.0 = all interfaces)'),

        Node(
            package='foxglove_bridge',
            executable='foxglove_bridge',
            name='foxglove_bridge',
            parameters=[{
                'port': port,
                'address': address,
                'tls': False,
                'topic_whitelist': ['.*'],   # all topics
                'param_whitelist': ['.*'],   # all params visible
                'max_qos_depth': 10,
                'num_threads': 4,
                'use_compression': False,    # disable for LAN — lower latency
            }],
            output='screen',
        ),
    ])
