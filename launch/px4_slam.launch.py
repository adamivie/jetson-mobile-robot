from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    """
    Launch the full PX4 + Jetson ROS2 stack:
      1. micro_ros_agent   — bridges PX4 uXRCE-DDS over UDP to ROS2
      2. px4_bridge        — NED/FRD → ENU/FLU frame conversion, publishes /odom + /imu/data
      3. rplidar_node      — RPLidar S2L laser scan
      4. slam_toolbox      — online async SLAM using lidar + odom

    PX4 configuration required (QGroundControl → Parameters):
      UXRCE_DDS_CFG  = 1000   (Ethernet)
      UXRCE_DDS_AG_IP = <Jetson IP as uint32, e.g. 192.168.3.72 = 3232236360>
      UXRCE_DDS_PRT  = 8888
      MAV_SYS_ID     = 1
    """
    px4_agent_port = LaunchConfiguration('px4_agent_port', default='8888')
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')

    return LaunchDescription([
        DeclareLaunchArgument('px4_agent_port', default_value='8888',
                              description='UDP port for micro_ros_agent (must match PX4 UXRCE_DDS_PRT)'),
        DeclareLaunchArgument('use_sim_time', default_value='false'),

        # micro_ros_agent — listens for PX4 uXRCE-DDS on UDP
        ExecuteProcess(
            cmd=['ros2', 'run', 'micro_ros_agent', 'micro_ros_agent',
                 'udp4', '--port', px4_agent_port],
            output='screen',
            name='micro_ros_agent',
        ),

        # PX4 bridge — NED→ENU frame conversion
        Node(
            package='robot_vision',
            executable='px4_bridge',
            name='px4_bridge',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time}],
        ),

        # RPLidar S2L
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

        # slam_toolbox — online async mapping
        Node(
            package='slam_toolbox',
            executable='async_slam_toolbox_node',
            name='slam_toolbox',
            parameters=[
                '/home/slurd/ros2_ws/src/robot_vision/config/slam_toolbox.yaml',
                {'use_sim_time': use_sim_time},
            ],
            output='screen',
        ),
    ])
