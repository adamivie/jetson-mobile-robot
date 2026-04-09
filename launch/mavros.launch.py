from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    mavros_config = os.path.join(
        get_package_share_directory('robot_vision'),
        'config',
        'mavros.yaml'
    )

    return LaunchDescription([
        Node(
            package='mavros',
            executable='mavros_node',
            name='mavros',
            output='screen',
            parameters=[
                mavros_config,
                {
                    'fcu_url': '/dev/pixhawk:115200',
                    'gcs_url': '',
                    'target_system_id': 1,
                    'target_component_id': 1,
                    'fcu_protocol': 'v2.0',
                },
            ],
        ),
    ])
