#!/bin/bash
# =============================================================================
# Jetson Orin Nano – ROS2 Humble + RealSense D455 + Vision stack setup
# Ubuntu 22.04 (Jammy) | CUDA 12.6 | JetPack 6.x
# Run as: bash setup_jetson.sh 2>&1 | tee setup_jetson.log
# =============================================================================
set -e

CYAN='\033[0;36m'; GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${CYAN}[SETUP]${NC} $1"; }
ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
die()  { echo -e "${RED}[ERR]${NC} $1"; exit 1; }

# ── 0. Sanity checks ──────────────────────────────────────────────────────────
[[ "$(lsb_release -cs)" == "jammy" ]] || die "Expected Ubuntu 22.04 Jammy"
log "Ubuntu 22.04 confirmed"

# ── 1. System update ─────────────────────────────────────────────────────────
log "Updating apt..."
sudo apt-get update -qq
sudo apt-get upgrade -y -qq

# ── 2. ROS2 Humble ───────────────────────────────────────────────────────────
if ! command -v ros2 &>/dev/null; then
  log "Installing ROS2 Humble..."
  sudo apt-get install -y -qq curl gnupg lsb-release software-properties-common
  sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
    -o /usr/share/keyrings/ros-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
    http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" \
    | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
  sudo apt-get update -qq
  # ros-humble-ros-base saves ~1 GB vs desktop on a space-tight Jetson
  sudo apt-get install -y -qq \
    ros-humble-ros-base \
    ros-humble-rclcpp \
    ros-humble-rclpy \
    ros-humble-sensor-msgs \
    ros-humble-geometry-msgs \
    ros-humble-nav-msgs \
    ros-humble-tf2 \
    ros-humble-tf2-ros \
    ros-humble-tf2-geometry-msgs \
    ros-humble-image-transport \
    ros-humble-image-transport-plugins \
    ros-humble-cv-bridge \
    ros-humble-vision-opencv \
    ros-humble-compressed-image-transport \
    ros-humble-diagnostic-updater \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-vcstool
  ok "ROS2 Humble installed"
else
  ok "ROS2 Humble already present"
fi

# Source ROS2 for rest of script
source /opt/ros/humble/setup.bash

# ── 3. rosdep init ───────────────────────────────────────────────────────────
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
  log "Initialising rosdep..."
  sudo rosdep init
fi
rosdep update --rosdistro humble -q
ok "rosdep ready"

# ── 4. librealsense2 (D455 support) ─────────────────────────────────────────
if ! dpkg -l librealsense2 &>/dev/null; then
  log "Installing Intel RealSense SDK (librealsense2)..."
  sudo mkdir -p /etc/apt/keyrings
  curl -sSf https://librealsense.intel.com/Debian/librealsense.pgp \
    | sudo tee /etc/apt/keyrings/librealsense.pgp > /dev/null
  echo "deb [signed-by=/etc/apt/keyrings/librealsense.pgp] \
    https://librealsense.intel.com/Debian/apt-repo $(lsb_release -cs) main" \
    | sudo tee /etc/apt/sources.list.d/librealsense.list > /dev/null
  sudo apt-get update -qq
  sudo apt-get install -y -qq \
    librealsense2 \
    librealsense2-dkms \
    librealsense2-utils \
    librealsense2-dev \
    librealsense2-dbg
  ok "librealsense2 installed"
else
  ok "librealsense2 already present"
fi

# ── 5. RealSense ROS2 wrapper ────────────────────────────────────────────────
if ! ros2 pkg list 2>/dev/null | grep -q realsense2_camera; then
  log "Installing realsense2_camera ROS2 package..."
  sudo apt-get install -y -qq ros-humble-realsense2-camera ros-humble-realsense2-description
  ok "realsense2_camera installed"
else
  ok "realsense2_camera already present"
fi

# ── 6. Additional vision / robotics packages ─────────────────────────────────
log "Installing additional vision & navigation packages..."
sudo apt-get install -y -qq \
  ros-humble-depth-image-proc \
  ros-humble-image-pipeline \
  ros-humble-pcl-ros \
  ros-humble-laser-geometry \
  ros-humble-nav2-bringup \
  ros-humble-robot-localization \
  ros-humble-slam-toolbox \
  ros-humble-rmw-cyclonedds-cpp \
  python3-opencv \
  python3-numpy \
  python3-scipy \
  libopencv-dev
ok "Vision packages installed"

# ── 7. Shell environment ─────────────────────────────────────────────────────
BASHRC="$HOME/.bashrc"
add_if_missing() {
  grep -qF "$1" "$BASHRC" || echo "$1" >> "$BASHRC"
}
log "Configuring ~/.bashrc..."
add_if_missing "source /opt/ros/humble/setup.bash"
add_if_missing "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp"
add_if_missing "export RCUTILS_COLORIZED_OUTPUT=1"
# Source workspace overlay if it exists
add_if_missing "[ -f ~/ros2_ws/install/setup.bash ] && source ~/ros2_ws/install/setup.bash"
ok ".bashrc updated"

# ── 8. Create ROS2 workspace skeleton ───────────────────────────────────────
WS=~/ros2_ws
PKG=robot_vision
PKG_DIR=$WS/src/$PKG

if [ ! -d "$WS/src" ]; then
  log "Creating ROS2 workspace at $WS..."
  mkdir -p "$WS/src"
fi

if [ ! -d "$PKG_DIR" ]; then
  log "Scaffolding $PKG package..."
  mkdir -p "$PKG_DIR/$PKG"
  mkdir -p "$PKG_DIR/launch"
  mkdir -p "$PKG_DIR/config"

  # package.xml
  cat > "$PKG_DIR/package.xml" << 'PKGXML'
<?xml version="1.0"?>
<package format="3">
  <name>robot_vision</name>
  <version>0.1.0</version>
  <description>ROS2 vision pipeline for mobile robot with RealSense D455</description>
  <maintainer email="slurd@jetson">slurd</maintainer>
  <license>MIT</license>

  <depend>rclpy</depend>
  <depend>sensor_msgs</depend>
  <depend>geometry_msgs</depend>
  <depend>cv_bridge</depend>
  <depend>image_transport</depend>
  <depend>tf2_ros</depend>
  <depend>depth_image_proc</depend>
  <depend>pcl_ros</depend>
  <depend>realsense2_camera</depend>

  <buildtool_depend>ament_python</buildtool_depend>
  <test_depend>ament_lint_auto</test_depend>
  <test_depend>ament_lint_common</test_depend>

  <export>
    <build_type>ament_python</build_type>
  </export>
</package>
PKGXML

  # setup.py
  cat > "$PKG_DIR/setup.py" << 'SETUPPY'
from setuptools import setup
import os
from glob import glob

package_name = 'robot_vision'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    entry_points={
        'console_scripts': [
            'depth_processor = robot_vision.depth_processor:main',
            'obstacle_detector = robot_vision.obstacle_detector:main',
        ],
    },
)
SETUPPY

  # resource marker
  mkdir -p "$PKG_DIR/resource"
  touch "$PKG_DIR/resource/$PKG"

  # setup.cfg
  cat > "$PKG_DIR/setup.cfg" << 'SETUPCFG'
[develop]
script_dir=$base/lib/robot_vision
[install]
install_scripts=$base/lib/robot_vision
SETUPCFG

  # __init__.py
  touch "$PKG_DIR/$PKG/__init__.py"

  # depth_processor.py – subscribes to D455 depth, publishes obstacle distances
  cat > "$PKG_DIR/$PKG/depth_processor.py" << 'DEPTHPY'
#!/usr/bin/env python3
"""
depth_processor.py
Subscribes to RealSense D455 depth image and RGB image, publishes a
PointCloud2 and a simple forward-obstacle distance Float32.
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, PointCloud2
from std_msgs.msg import Float32
from cv_bridge import CvBridge
import numpy as np


class DepthProcessor(Node):
    def __init__(self):
        super().__init__('depth_processor')

        # Parameters
        self.declare_parameter('depth_topic', '/camera/camera/depth/image_rect_raw')
        self.declare_parameter('roi_width_frac', 0.3)   # centre-ROI width fraction
        self.declare_parameter('roi_height_frac', 0.4)  # centre-ROI height fraction
        self.declare_parameter('min_valid_depth_m', 0.3)
        self.declare_parameter('max_valid_depth_m', 6.0)

        depth_topic = self.get_parameter('depth_topic').value

        self.bridge = CvBridge()

        self.sub_depth = self.create_subscription(
            Image, depth_topic, self.depth_cb, 10)

        self.pub_obstacle_dist = self.create_publisher(Float32, '~/obstacle_distance_m', 10)

        self.get_logger().info(f'DepthProcessor started, listening on {depth_topic}')

    def depth_cb(self, msg: Image):
        # Convert depth image (16UC1, millimetres) to float32 metres
        depth_raw = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
        depth_m = depth_raw.astype(np.float32) / 1000.0

        h, w = depth_m.shape
        rw = self.get_parameter('roi_width_frac').value
        rh = self.get_parameter('roi_height_frac').value
        min_d = self.get_parameter('min_valid_depth_m').value
        max_d = self.get_parameter('max_valid_depth_m').value

        # Centre ROI
        x0 = int(w * (0.5 - rw / 2))
        x1 = int(w * (0.5 + rw / 2))
        y0 = int(h * (0.5 - rh / 2))
        y1 = int(h * (0.5 + rh / 2))
        roi = depth_m[y0:y1, x0:x1]

        valid = roi[(roi > min_d) & (roi < max_d)]
        if valid.size == 0:
            return

        min_dist = float(np.percentile(valid, 5))  # 5th-percentile = closest obstacle
        out = Float32()
        out.data = min_dist
        self.pub_obstacle_dist.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = DepthProcessor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
DEPTHPY

  # obstacle_detector.py – publishes Twist stop/go commands based on obstacle distance
  cat > "$PKG_DIR/$PKG/obstacle_detector.py" << 'OBSTPY'
#!/usr/bin/env python3
"""
obstacle_detector.py
Simple safety layer: listens to obstacle distance, publishes a stop flag.
"""
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32, Bool


class ObstacleDetector(Node):
    def __init__(self):
        super().__init__('obstacle_detector')
        self.declare_parameter('stop_distance_m', 0.6)

        self.sub = self.create_subscription(
            Float32, '/depth_processor/obstacle_distance_m', self.dist_cb, 10)
        self.pub = self.create_publisher(Bool, '~/obstacle_detected', 10)
        self.get_logger().info('ObstacleDetector started')

    def dist_cb(self, msg: Float32):
        stop_dist = self.get_parameter('stop_distance_m').value
        out = Bool()
        out.data = msg.data < stop_dist
        if out.data:
            self.get_logger().warn(f'Obstacle at {msg.data:.2f}m — STOP')
        self.pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = ObstacleDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
OBSTPY

  # Launch file – D455 camera + depth_processor + obstacle_detector
  cat > "$PKG_DIR/launch/robot_vision.launch.py" << 'LAUNCHPY'
"""
robot_vision.launch.py
Launches: RealSense D455 camera → depth_processor → obstacle_detector
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('stop_distance_m', default_value='0.6',
                              description='Obstacle stop distance in metres'),

        # RealSense D455 camera node
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
                'pointcloud.stream_filter': 2,  # RS2_STREAM_DEPTH
            }],
            output='screen',
        ),

        # Depth processor
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

        # Obstacle detector / safety layer
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
LAUNCHPY

  # D455 camera config
  cat > "$PKG_DIR/config/d455.yaml" << 'CAMYAML'
# RealSense D455 parameters for realsense2_camera_node
camera:
  ros__parameters:
    enable_color: true
    enable_depth: true
    align_depth.enable: true
    pointcloud.enable: true
    depth_module.profile: "640x480x30"
    rgb_camera.profile: "640x480x30"
    # D455-specific: enable global shutter, better for motion
    depth_module.global_time_enabled: true
    spatial_filter.enable: true
    temporal_filter.enable: true
    hole_filling_filter.enable: true
CAMYAML

  ok "$PKG package scaffolded"
fi

# ── 9. Build workspace ───────────────────────────────────────────────────────
log "Building ROS2 workspace (first build may take a few minutes)..."
cd "$WS"
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release 2>&1
ok "Workspace built"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN} Setup complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Plug in RealSense D455, then:"
echo "    source ~/.bashrc"
echo "    ros2 launch robot_vision robot_vision.launch.py"
echo ""
echo "  Useful checks:"
echo "    rs-enumerate-devices -S          # verify D455 detected"
echo "    ros2 topic list                  # see all active topics"
echo "    ros2 topic echo /depth_processor/obstacle_distance_m"
echo "    ros2 topic echo /obstacle_detector/obstacle_detected"
echo ""
