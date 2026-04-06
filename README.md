# Jetson Orin Nano — Mobile Robotics Platform

> **Hardware:** NVIDIA Jetson Orin Nano  
> **OS:** Ubuntu 22.04 LTS (Jammy) — JetPack 6.x  
> **CUDA:** 12.6 | **TensorRT:** 10.3 | **cuDNN:** 9.3  
> **Camera:** Intel RealSense D455 *(pending installation)*  
> **Storage:** eMMC 28 GB → NVMe migration planned  
> **Host dev machine:** Windows 11, user `Jerome`, SSH alias `jetson`

---

## Repository Layout

```
jetson1/
├── robot_vision/          # ROS2 Python package source
│   ├── __init__.py
│   ├── depth_processor.py       # Depth → obstacle distance node
│   └── obstacle_detector.py     # Safety stop publisher
├── launch/
│   └── robot_vision.launch.py   # Full stack launch (cam + processors)
├── config/
│   └── d455.yaml                # RealSense D455 camera parameters
├── scripts/
│   └── fix_bashrc.py            # One-shot bashrc repair utility
├── package.xml
├── setup.py
├── setup.cfg
├── setup_jetson.sh              # Full environment bootstrap script
└── README.md
```

---

## Quick Start

### 1. SSH to Jetson

```bash
ssh jetson          # resolves via ~/.ssh/config → slurd@192.168.3.72
```

### 2. Verify ROS2 environment

```bash
source ~/.bashrc
ros2 doctor
ros2 pkg list | grep -E 'robot_vision|realsense'
```

### 3. Launch full vision stack (requires D455 plugged in)

```bash
ros2 launch robot_vision robot_vision.launch.py
# Override stop distance:
ros2 launch robot_vision robot_vision.launch.py stop_distance_m:=0.8
```

### 4. Monitor topics

```bash
ros2 topic list
ros2 topic echo /depth_processor/obstacle_distance_m
ros2 topic echo /obstacle_detector/obstacle_detected
```

---

## Environment Setup (from scratch)

Run the bootstrap script once on a fresh JetPack install:

```bash
scp setup_jetson.sh jetson:~/
ssh jetson "bash ~/setup_jetson.sh 2>&1 | tee ~/setup_jetson.log"
```

What it installs:
- ROS2 Humble (ros-base + all vision/nav packages)
- `librealsense2` + `realsense2_camera` via ROS apt repo
- `ros-humble-slam-toolbox`, `nav2`, `robot-localization`, `pcl-ros`
- CycloneDDS as the RMW implementation
- `~/ros2_ws` with the `robot_vision` package

---

## Installed Stack

| Component | Version |
|---|---|
| ROS2 | Humble (2026-03 packages) |
| librealsense2 | 2.57.7 (via `ros-humble-librealsense2`) |
| realsense2_camera | 4.57.7 |
| CUDA | 12.6 |
| TensorRT | 10.3.0.30 |
| cuDNN | 9.3.0 |
| CycloneDDS | RMW default |
| OpenCV | 4.5.4 (system) |
| Python | 3.10 |

---

## ROS2 Node Reference

### `depth_processor`

**Package:** `robot_vision`  
**Executable:** `ros2 run robot_vision depth_processor`

| Parameter | Default | Description |
|---|---|---|
| `depth_topic` | `/camera/camera/depth/image_rect_raw` | Input depth image topic |
| `roi_width_frac` | `0.3` | Centre ROI width as fraction of frame |
| `roi_height_frac` | `0.4` | Centre ROI height as fraction of frame |
| `min_valid_depth_m` | `0.3` | Minimum valid depth (metres) |
| `max_valid_depth_m` | `6.0` | Maximum valid depth (metres) |

**Publishes:** `~/obstacle_distance_m` (`std_msgs/Float32`) — 5th-percentile distance of closest object in ROI.

---

### `obstacle_detector`

**Package:** `robot_vision`  
**Executable:** `ros2 run robot_vision obstacle_detector`

| Parameter | Default | Description |
|---|---|---|
| `stop_distance_m` | `0.6` | Distance threshold to trigger stop flag |

**Subscribes:** `/depth_processor/obstacle_distance_m`  
**Publishes:** `~/obstacle_detected` (`std_msgs/Bool`)

---

## SSH & Key Setup (Windows host)

Keys are in `~/.ssh/`. The Jetson uses `id_ed25519`.

`~/.ssh/config` entry:
```
Host jetson
  HostName 192.168.3.72
  User slurd
  IdentityFile ~/.ssh/id_ed25519
  IdentitiesOnly yes
```

Passwordless sudo is configured via `/etc/sudoers.d/slurd`.

---

## Pending / Next Steps

- [ ] **NVMe migration** — clone eMMC → NVMe, update boot config
- [ ] **D455 camera** — plug in, run `rs-enumerate-devices -S`, launch stack
- [ ] **URDF / robot model** — add robot description package
- [ ] **Nav2 bringup** — configure costmaps, waypoint following
- [ ] **Static IP** — assign `192.168.3.72` as static or reserve via DHCP
- [ ] **mDNS hostname** — configure `jetson.local` for hostname-based SSH
