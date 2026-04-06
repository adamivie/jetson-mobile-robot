# Jetson Mobile Robot — Persistent Session Notes

> Auto-updated: 2026-04-06  
> Repo: `adamivie/jetson-mobile-robot` · branch `main`

---

## Hardware

| Component | Detail |
|-----------|--------|
| **SBC** | NVIDIA Jetson Orin Nano 8GB Developer Kit |
| **OS** | Ubuntu 22.04.x Jammy |
| **JetPack** | 6.x — R36 rev 4.7 (kernel `5.15.148-tegra`) |
| **CUDA** | 12.6 |
| **Storage** | NVMe `nvme0n1p1` — 234G total, ~27G used, 196G free (root) |
| **Camera** | Intel RealSense D455 (USB-C) |
| **LiDAR** | RPLidar S2L (USB) |
| **FC** | Pixhawk 6X (Ethernet — hardware pending) |
| **SSH** | `Host jetson` → `slurd@192.168.3.72` · key `id_ed25519` · passwordless sudo |

---

## Software Stack

| Package | Version | Notes |
|---------|---------|-------|
| ROS2 | Humble (ros-base) | CycloneDDS RMW |
| foxglove-bridge | 3.2.5 | WebSocket port 8765 |
| jetson-stats (jtop) | 4.3.2 | systemd service `jtop` |
| librealsense2 | latest | D455 driver |
| OpenCV | 4.5.4 | system python3 |
| rplidar_ros | humble | S2L driver |

---

## Key File Locations

### On the Jetson (`~/`)
```
~/ros2_ws/src/robot_vision/      ← ROS2 package source
~/ros2_ws/install/               ← colcon install output
~/start_foxglove.sh              ← start bridge + stats node
~/kill_foxglove.sh               ← kill ALL related processes (fixed 2026-04-06)
~/.ros/foxglove_bridge.log       ← bridge log
~/.ros/foxglove_bridge.pid       ← bridge PID
```

### In this repo (`c:\jetson1\`)
```
robot_vision/
  jetson_stats_node.py           ← jtop ROS2 node (10 topics @ 1 Hz)
  depth_processor.py             ← D455 depth → obstacle distance
  obstacle_detector.py           ← obstacle stop flag
  px4_bridge.py                  ← Pixhawk uXRCE-DDS bridge
launch/
  foxglove.launch.py             ← launches jetson_stats + foxglove_bridge
  robot_vision.launch.py         ← D455 camera launch
  slam.launch.py                 ← RPLidar + SLAM toolbox
  px4_slam.launch.py             ← full stack with Pixhawk
foxglove/
  robot_dashboard.json           ← Foxglove layout (import via Layouts menu)
scripts/
  start_foxglove.sh
  kill_foxglove.sh
config/
  slam_config.yaml
setup.py
```

---

## ROS2 Topics

### Jetson System Stats (`/jetson/*`)
| Topic | Type | Value |
|-------|------|-------|
| `/jetson/cpu_percent` | Float32MultiArray | per-core % |
| `/jetson/gpu_percent` | Float32 | GPU load % |
| `/jetson/memory_used_mb` | Float32 | RAM used |
| `/jetson/memory_total_mb` | Float32 | RAM total |
| `/jetson/temp/cpu` | Float32 | ~47°C idle |
| `/jetson/temp/gpu` | Float32 | ~48°C idle |
| `/jetson/temp/soc` | Float32 | ~47°C idle (soc0 zone) |
| `/jetson/temp/tj` | Float32 | ~48°C idle (junction peak) |
| `/jetson/power_mw` | Float32 | board power mW |
| `/jetson/uptime_s` | Float32 | seconds since boot |
| `/jetson/diagnostics` | DiagnosticArray | WARN if Tj > 85°C |

### jtop temperature key names (Orin Nano — all lowercase)
`cpu`, `gpu`, `soc0`, `soc1`, `soc2`, `tj` — cv0/1/2 offline (-256°C)

---

## Operational Commands

```bash
# Start everything
ssh jetson "bash ~/start_foxglove.sh"

# Restart cleanly (ALWAYS use kill first — prevents zombie node accumulation)
ssh jetson "bash ~/kill_foxglove.sh && sleep 2 && bash ~/start_foxglove.sh"

# Check log
ssh jetson "tail -f ~/.ros/foxglove_bridge.log"

# Verify stats topics
ssh jetson "source /opt/ros/humble/setup.bash && source ~/ros2_ws/install/setup.bash && RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ros2 topic echo /jetson/temp/soc --once"

# Rebuild after code changes
ssh jetson "cd ~/ros2_ws && colcon build --packages-select robot_vision --symlink-install"

# Deploy + restart in one line
scp c:\jetson1\robot_vision\jetson_stats_node.py jetson:~/ros2_ws/src/robot_vision/robot_vision/jetson_stats_node.py && ssh jetson "bash ~/kill_foxglove.sh && sleep 1 && bash ~/start_foxglove.sh"

# Foxglove connection
# URL: ws://192.168.3.72:8765
# Layout: foxglove/robot_dashboard.json  (Layouts → Import from file)
```

---

## Known Bugs / Gotchas

### 1. Zombie node accumulation → SoC temp spikes to 0
**Symptom:** Foxglove Temps plot shows SoC (yellow) spiking to 0 every second  
**Root cause:** `kill_foxglove.sh` was matching `jetson_stats_node` but the installed colcon binary is named `jetson_stats`. Each `start_foxglove.sh` stacked a new instance; old instances published `0.0` before jtop initialised.  
**Fix:** `kill_foxglove.sh` now kills `robot_vision/jetson_stats` pattern. Commit `f0e8e9f`.  
**Prevention:** Always `kill` before `start`. Never run `start_foxglove.sh` twice without killing first.

### 2. Foxglove Plot schema (v2.49.0)
Correct schema — learned from live export:
```json
"paths": [{ "value": "/topic.field", "id": "uuid-string",
            "label": "Name", "color": "#hex",
            "timestampMethod": "receiveTime", "enabled": true }],
"foxglovePanelTitle": "Panel Title"
```
Wrong keys that were tried first: `series[]`, `paths[].messagePath`, `title`

### 3. jtop `uptime` is `datetime.timedelta`
`float(stats.get('uptime'))` crashes. Use `uptime_val.total_seconds()` with `hasattr` guard.

### 4. ROS2 CLI hangs / "!rclpy.ok()" error
The ROS2 daemon goes stale after multiple node crashes. Fix: `kill -9 $(pgrep -f ros2cli.daemon)`

### 5. `ros2 topic echo` needs explicit env
`ssh jetson "ros2 ..."` fails — no ROS2 in PATH over non-interactive SSH.  
Use: `ssh jetson "source /opt/ros/humble/setup.bash && source ~/ros2_ws/install/setup.bash && RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ros2 ..."`

---

## Foxglove Dashboard Layout

File: `foxglove/robot_dashboard.json` — import via **Layouts → Import from file**

| Panel | Topics |
|-------|--------|
| 3D | LiDAR, map, TF — follows `base_link` |
| Image (RGB) | `/camera/camera/color/image_raw` |
| Image (Depth) | `/camera/camera/depth/image_rect_raw` |
| Plot: Obstacle | distance + stop flag |
| Plot: IMU | angular velocity X/Y/Z |
| Plot: Accel | linear acceleration X/Y/Z |
| Plot: Jetson Load | GPU % + RAM MB |
| Plot: Temps | CPU / GPU / SoC / Tj(peak) |
| Plot: Power | board power mW |
| State Transitions | obstacle flag |
| Diagnostics | `/jetson/diagnostics` |
| Log | `/rosout` |

---

## Pending Hardware Tasks

| Task | Command |
|------|---------|
| **D455 camera** | `ssh jetson "bash ~/start_foxglove.sh"` then `ros2 launch robot_vision robot_vision.launch.py` |
| **RPLidar S2L** | Check `ls /dev/rplidar` then `ros2 launch robot_vision slam.launch.py` |
| **Static IP** | DHCP reservation for `192.168.3.72` before robot goes mobile |
| **Pixhawk 6X** | `bash ~/build_px4_ws.sh` → QGC params → `ros2 launch robot_vision px4_slam.launch.py` |

### Pixhawk 6X QGC Parameters (when hardware arrives)
```
UXRCE_DDS_CFG = 1000          (Ethernet)
UXRCE_DDS_AG_IP = 3232236360  (= 192.168.3.72)
UXRCE_DDS_PRT = 8888
```

---

## Git History (key commits)

| Commit | Description |
|--------|-------------|
| `f0e8e9f` | fix: kill script matches installed binary name `jetson_stats` — **root cause of SoC spikes** |
| `d352d70` | fix: use jtop callback to guarantee fresh data on publish |
| `afa1583` | fix: cache last-good temp values (intermediate attempt) |
| `a0db3af` | fix: correct Foxglove Plot schema — paths[].id + foxglovePanelTitle |
| `a0749ff` | fix: jtop temp keys lowercase on Orin Nano; add Tj(peak) topic |
