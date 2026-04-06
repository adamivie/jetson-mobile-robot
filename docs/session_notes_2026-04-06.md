# Session Notes — Jetson Orin Nano Setup
**Date:** 2026-04-06  
**Host:** Windows 11 (`Jerome@Adam-Laptop`)  
**Target:** NVIDIA Jetson Orin Nano @ `192.168.3.72`, user `slurd`

---

## What Was Done

### 1. Discovery & SSH
- Jetson found at `192.168.3.72` via ARP table (subnet `192.168.3.0/24`, host on Wi-Fi `192.168.3.61`)
- SSH port 22 confirmed open
- Existing `id_ed25519` key used — pushed to `~/.ssh/authorized_keys` via one-time password SSH
- Passwordless sudo configured: `/etc/sudoers.d/slurd` with `NOPASSWD: ALL`
- `Host jetson` alias added to `~/.ssh/config`

### 2. Baseline System State (at session start)
- Ubuntu 22.04.5 LTS (Jammy), kernel `5.15.148-tegra`
- CUDA 12.6, TensorRT 10.3, cuDNN 9.3 — all pre-installed via JetPack 6
- **No ROS2, no librealsense** at start
- Storage: 28 GB eMMC, ~4.8 GB free at start → freed to 2.7 GB after `apt clean` + `autoremove`

### 3. ROS2 Humble Install
- Added ROS2 apt repo, installed `ros-humble-ros-base` plus:
  - `cv-bridge`, `image-transport`, `image-transport-plugins`, `vision-opencv`
  - `tf2`, `tf2-ros`, `tf2-geometry-msgs`
  - `depth-image-proc`, `image-pipeline`, `pcl-ros`, `laser-geometry`
  - `nav2-bringup`, `robot-localization`, `slam-toolbox`
  - `rmw-cyclonedds-cpp` (set as default RMW)
  - `colcon`, `rosdep`, `vcstool`
- `rosdep init` + `rosdep update` completed

### 4. RealSense SDK
- **Intel's direct apt repo failed** — GPG key mismatch (`FB0B24895113F120` not matching downloaded `.pgp`), keyservers unreachable from Jetson
- **Fix:** Installed via ROS apt repo instead — `ros-humble-realsense2-camera` bundles `ros-humble-librealsense2 2.57.7`
- This is the correct approach for JetPack systems anyway (avoids DKMS kernel module conflicts)

### 5. robot_vision ROS2 Package
- Created `~/ros2_ws/src/robot_vision/` (ament_python)
- Two nodes: `depth_processor` (D455 depth → obstacle distance) and `obstacle_detector` (safety stop flag)
- Launch file: `robot_vision.launch.py` — starts camera node + both processors
- D455 config: `config/d455.yaml`
- Built with `colcon build --symlink-install`
- **Known quirk:** `ament_python` packages don't self-register in `AMENT_PREFIX_PATH` — fixed by manually exporting in `.bashrc`

### 6. .bashrc State (end of session)
```bash
source /opt/ros/humble/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export RCUTILS_COLORIZED_OUTPUT=1
[ -f ~/ros2_ws/install/setup.bash ] && source ~/ros2_ws/install/setup.bash
export AMENT_PREFIX_PATH="$HOME/ros2_ws/install/robot_vision:$AMENT_PREFIX_PATH"
```

---

## Known Issues / Watch-outs

| Issue | Status | Notes |
|---|---|---|
| Intel RealSense apt repo key mismatch | ✅ Worked around | Use `ros-humble-realsense2-camera` instead of Intel's repo |
| `ament_python` not in `AMENT_PREFIX_PATH` | ✅ Fixed | Manual export in `.bashrc` |
| `set -e` in setup script exits on RealSense key failure | ✅ Fixed manually | Will update `setup_jetson.sh` |
| eMMC 96% full after install | ✅ OK for now | NVMe migration planned same day |
| `.bashrc` AMENT line corrupted by PowerShell quoting | ✅ Fixed | Use `fix_bashrc.py` if it recurs |
| Jetson static IP not set | ⏳ Pending | Currently DHCP, risk of IP change |

---

## NVMe Migration Plan (next task)

1. Install NVMe SSD into M.2 slot
2. From Jetson: `sudo apt-get install -y nvme-cli`
3. Identify NVMe device: `lsblk`
4. Flash NVMe with eMMC image using `dd` or NVIDIA's `nvme-clone` approach:
   ```bash
   sudo dd if=/dev/mmcblk0 of=/dev/nvme0n1 bs=4M status=progress conv=fsync
   ```
   Or use `rsync` for a live copy:
   ```bash
   sudo rsync -aAXH --exclude={/dev,/proc,/sys,/run,/tmp} / /mnt/nvme/
   ```
5. Update `/boot/extlinux/extlinux.conf` root device to NVMe
6. Reboot and verify

---

## Useful Commands Cheatsheet

```bash
# SSH
ssh jetson

# ROS2 health
ros2 doctor
ros2 topic list
ros2 node list

# robot_vision
ros2 launch robot_vision robot_vision.launch.py
ros2 topic echo /depth_processor/obstacle_distance_m
ros2 topic echo /obstacle_detector/obstacle_detected

# RealSense (once camera plugged in)
rs-enumerate-devices -S
ros2 run realsense2_camera realsense2_camera_node

# System
df -h /
free -h
nvtop          # GPU monitor (install: sudo apt install nvtop)
jtop           # Jetson monitor (install: sudo pip3 install jetson-stats)
```
