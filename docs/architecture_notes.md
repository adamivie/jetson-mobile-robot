# Architecture & Design Notes
**Last updated:** 2026-04-06

This document captures design decisions, constraints, and integration logic for the
full robot stack. Read this before making changes to any node, launch file, or config.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Jetson Orin Nano                          │
│                                                             │
│  ┌─────────────┐   ┌──────────────┐   ┌─────────────────┐  │
│  │micro_ros_    │   │  px4_bridge  │   │  depth_processor│  │
│  │agent UDP8888│──▶│  NED→ENU     │──▶│  D455 depth     │  │
│  └─────────────┘   │  /odom       │   │  → obstacle_dist│  │
│         ▲          │  /imu/data   │   └────────┬────────┘  │
│         │          └──────────────┘            │           │
│  ┌──────┴──────┐                     ┌─────────▼────────┐  │
│  │ Pixhawk 6X  │   ┌──────────────┐  │ obstacle_detector│  │
│  │ uXRCE-DDS   │   │ rplidar_node │  │ → /obstacle_det  │  │
│  │ Ethernet    │   │ /scan        │  └──────────────────┘  │
│  └─────────────┘   └──────┬───────┘                        │
│                           │                                 │
│                    ┌──────▼───────┐                         │
│                    │ slam_toolbox │                         │
│                    │ /map         │                         │
│                    │ /tf map→odom │                         │
│                    └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘
         │ Ethernet (192.168.3.x)
┌────────┴──────────────┐
│   Pixhawk 6X           │
│   PX4 v1.14+           │
│   ICM-42688-P (IMU)    │
│   ICM-20649D (IMU2)    │
│   EKF2 running onboard │
│   uXRCE-DDS → UDP:8888 │
└───────────────────────┘

Hardware on robot:
  - Intel RealSense D455    (USB3, /dev/realsense)
  - RPLidar S2L             (USB, /dev/rplidar via udev)
  - Pixhawk 6X              (Ethernet, 192.168.3.x)
```

---

## Frame Convention — Critical

PX4 and ROS2 use **opposite coordinate frames**. This is the most common source of
bugs in PX4+ROS2 integrations. The `px4_bridge` node handles all conversions.

| | X | Y | Z | Rotation |
|---|---|---|---|---|
| **PX4 world** | North | East | Down (NED) | |
| **PX4 body** | Forward | Right | Down (FRD) | |
| **ROS2 world** | East | North | Up (ENU) | |
| **ROS2 body** | Forward | Left | Up (FLU) | |

### Conversion formulas in `px4_bridge.py`:
- Position: `(x,y,z)_ENU = (y, x, -z)_NED`
- Velocity: same swap
- Quaternion: apply static rotation `Rz(+90°) · Rx(180°)` via scipy
- Angular velocity / acceleration: `(p, -q, -r)` (flip Y and Z)

**Do not** apply any additional frame transforms downstream — `slam_toolbox`,
`robot_localization`, and Nav2 all expect standard ENU/FLU.

---

## PX4 Configuration (QGroundControl)

When Pixhawk 6X arrives, set these parameters before connecting:

| Parameter | Value | Notes |
|---|---|---|
| `UXRCE_DDS_CFG` | `1000` | Enable uXRCE-DDS on Ethernet port |
| `UXRCE_DDS_AG_IP` | `3232236360` | 192.168.3.72 as uint32: `(192<<24)+(168<<16)+(3<<8)+72` |
| `UXRCE_DDS_PRT` | `8888` | Must match `px4_slam.launch.py` arg |
| `UXRCE_DDS_PTCFG` | `0` | Client mode (Jetson is the agent) |
| `MAV_SYS_ID` | `1` | |
| `EKF2_AID_MASK` | TBD | Set after deciding GPS/vision odometry sources |

### IP as uint32 formula:
```python
ip = "192.168.3.72"
parts = [int(x) for x in ip.split('.')]
uint32 = (parts[0]<<24) + (parts[1]<<16) + (parts[2]<<8) + parts[3]
# = 3232236360
```

---

## Workspace Layout

```
~/ros2_ws/                          ← colcon workspace
  src/
    robot_vision/                   ← our package (ament_python)
      robot_vision/
        depth_processor.py          ← D455 depth → obstacle distance
        obstacle_detector.py        ← obstacle distance → stop flag
        px4_bridge.py               ← PX4 NED/FRD → ROS2 ENU/FLU
        __init__.py
      launch/
        robot_vision.launch.py      ← D455 only stack
        slam.launch.py              ← RPLidar + slam_toolbox
        px4_slam.launch.py          ← Full stack: PX4 + lidar + SLAM
      config/
        d455.yaml                   ← RealSense D455 camera params
        slam_toolbox.yaml           ← SLAM params (5cm res, 25m range)
      package.xml
      setup.py
      setup.cfg

~/px4_ws/                           ← PX4 msgs + micro_ros_agent (build when Pixhawk arrives)
  src/
    px4_msgs/                       ← branch release/1.14
    micro_ros_agent/                ← branch humble
```

### Key env vars (in ~/.bashrc):
```bash
source /opt/ros/humble/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export RCUTILS_COLORIZED_OUTPUT=1
[ -f ~/ros2_ws/install/setup.bash ] && source ~/ros2_ws/install/setup.bash
export AMENT_PREFIX_PATH="$HOME/ros2_ws/install/robot_vision:$AMENT_PREFIX_PATH"
# Add when px4_ws is built:
# [ -f ~/px4_ws/install/setup.bash ] && source ~/px4_ws/install/setup.bash
```

---

## Installed Software Versions (as of 2026-04-06)

### OS / Platform
| Package | Version |
|---|---|
| Ubuntu | 22.04.5 LTS Jammy |
| Kernel | 5.15.148-tegra (JetPack 6) |
| CUDA | 12.6 |
| TensorRT | 10.3.0.30 |
| cuDNN | 9.3.0.75 |
| scipy | 1.8.0 |
| OpenCV (cv2) | 4.5.4 |

### ROS2 Humble (key packages)
| Package | Version |
|---|---|
| ros-humble-ros-base | 0.10.0 |
| ros-humble-rclpy | 3.3.21 |
| ros-humble-realsense2-camera | 4.57.7 |
| ros-humble-librealsense2 | 2.57.7 |
| ros-humble-rplidar-ros | 2.1.4 |
| ros-humble-slam-toolbox | 2.6.10 |
| ros-humble-nav2-bringup | 1.1.20 |
| ros-humble-robot-localization | 3.5.4 |
| ros-humble-rmw-cyclonedds-cpp | 1.3.4 |
| ros-humble-pcl-ros | 2.4.5 |
| ros-humble-depth-image-proc | 3.0.9 |
| ros-humble-tf2-ros | 0.25.20 |

### apt-mark held (must not be upgraded)
```
cuda-toolkit-12
cuda-toolkit-12-6
cudnn-local-tegra-repo-ubuntu2204-9.3.0
l4t-cuda-tegra-repo-ubuntu2204-12-6-local
libcudnn9-cuda-12
nvidia-l4t-kernel
nvidia-l4t-kernel-dtbs
nvidia-l4t-kernel-headers
nvidia-l4t-kernel-oot-headers
nvidia-l4t-kernel-oot-modules
tensorrt
```

---

## Storage

| Device | Size | Mount | Notes |
|---|---|---|---|
| `nvme0n1p1` | 238.5 GB | `/` (root) | Fanxiang S500Pro 256GB — **active** |
| `mmcblk0p1` | 27.7 GB | `/media/slurd/752d27c0-...` | eMMC — passive backup, auto-mounts |
| Available | ~196 GB | | As of migration date |

eMMC is left intact as a fallback. To boot back to eMMC if NVMe fails, edit
`/boot/extlinux/extlinux.conf` and change `root=` back to `mmcblk0p1`.
The original eMMC extlinux.conf is backed up at `/boot/extlinux/extlinux.conf.emmc.bak`.

---

## Networking

| Device | IP | Interface | Notes |
|---|---|---|---|
| Jetson | `192.168.3.72` (DHCP) | `enP8p1s0` | **Set a DHCP reservation in router** |
| Pixhawk 6X | TBD | Jetson ethernet or switch | Configure after hardware arrives |
| Docker bridge | `172.17.0.1` | `docker0` | Docker installed, not actively used |

> ⚠️ **The Jetson IP is DHCP.** If the router reassigns it, the PX4 `UXRCE_DDS_AG_IP`
> param and SSH config will be wrong. Set a MAC-based DHCP reservation or configure
> a static IP via netplan before deploying.

### Set static IP via netplan (do this before robot deployment):
```bash
# /etc/netplan/01-static.yaml
network:
  version: 2
  ethernets:
    enP8p1s0:
      addresses: [192.168.3.72/24]
      gateway4: 192.168.3.1
      nameservers:
        addresses: [8.8.8.8, 8.8.4.4]
```

---

## Known Issues & Workarounds

### 1. PowerShell SSH quoting corrupts bash strings
Multi-line commands and heredocs fail when sent from PowerShell via SSH. Strings
containing `$`, `\`, or `|` get mangled by pwsh before reaching the Jetson shell.

**Workaround:** Write scripts locally, `scp` them, then `ssh jetson "bash ~/script.sh"`.
Never try to write multi-line bash inline from PowerShell.

### 2. `ament_python` packages not in `AMENT_PREFIX_PATH` by default
Colcon does not add ament_python install prefixes to `AMENT_PREFIX_PATH` automatically.
`ros2 pkg executables robot_vision` returns "Package not found" without the manual export.

**Fix:** Manually added to `~/.bashrc`:
```bash
export AMENT_PREFIX_PATH="$HOME/ros2_ws/install/robot_vision:$AMENT_PREFIX_PATH"
```

### 3. Intel RealSense apt repo GPG key mismatch
Intel's direct apt repo (`packages.intel.com`) returns key `FB0B24895113F120` which
does not match their published `.pgp` file. Keyservers are unreachable from the Jetson.

**Fix:** Use the ROS apt repo versions instead:
```bash
sudo apt-get install ros-humble-realsense2-camera ros-humble-realsense2-description
```
This pulls `ros-humble-librealsense2` as a dep. Works cleanly, no DKMS/kernel conflicts.

### 4. `micro_ros_agent` not in apt repo for Humble
Must be built from source. Script at `scripts/build_px4_ws.sh`. Takes ~10 min.
Requires `px4_msgs` at branch `release/1.14` to match PX4 firmware version.

### 5. ROS2 not in PATH for non-interactive SSH sessions
`~/.bashrc` is not sourced in non-interactive SSH (`ssh jetson "ros2 ..."`).

**Workaround:** Use `ssh jetson "bash -i -c 'ros2 ...'"` for one-liners, or
use `bash ~/script.sh` for anything more complex.

---

## Node Reference

### `depth_processor` (`robot_vision/depth_processor.py`)
| Item | Value |
|---|---|
| Subscribes | `/camera/camera/depth/image_rect_raw` (16UC1) |
| Publishes | `~/obstacle_distance_m` (Float32, metres) |
| Parameters | `depth_topic`, `roi_width_frac` (0.3), `roi_height_frac` (0.4), `min_valid_depth_m` (0.3), `max_valid_depth_m` (6.0) |
| Algorithm | 5th-percentile distance within centre ROI of depth frame |

### `obstacle_detector` (`robot_vision/obstacle_detector.py`)
| Item | Value |
|---|---|
| Subscribes | `/depth_processor/obstacle_distance_m` |
| Publishes | `~/obstacle_detected` (Bool) |
| Parameters | `stop_distance_m` (0.6 m) |

### `px4_bridge` (`robot_vision/px4_bridge.py`)
| Item | Value |
|---|---|
| Subscribes | `/fmu/out/vehicle_odometry`, `/fmu/out/sensor_combined`, `/fmu/out/vehicle_attitude` |
| Publishes | `/odom` (nav_msgs/Odometry), `/imu/data` (sensor_msgs/Imu) |
| Broadcasts | TF: `odom` → `base_link` |
| QoS | BEST_EFFORT + TRANSIENT_LOCAL (must match PX4 publisher profile) |
| Dependency | `scipy` (quaternion rotation), `px4_msgs` (built in `~/px4_ws`) |

---

## Pending Tasks

| Task | Notes |
|---|---|
| Set DHCP reservation or static IP | Router or netplan — do before robot leaves desk |
| Build `~/px4_ws` | Run `scripts/build_px4_ws.sh` when Pixhawk arrives |
| Configure PX4 parameters | QGroundControl — see parameter table above |
| Verify D455 camera | `ros2 launch robot_vision robot_vision.launch.py` |
| Verify RPLidar S2L | Plug in USB → `ls /dev/rplidar` → `ros2 launch robot_vision slam.launch.py` |
| URDF / robot_description | Needed for Nav2 and proper TF tree |
| `robot_localization` EKF config | Fuse `/odom` + `/imu/data` for better odometry estimate |
| Nav2 tuning | costmap params, planner selection, controller tuning |
| Full stack integration test | `ros2 launch robot_vision px4_slam.launch.py` |
