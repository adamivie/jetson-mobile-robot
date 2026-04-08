# Jetson Mobile Robot — Persistent Session Notes

> Auto-updated: 2026-04-08  
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
| **LiDAR** | YDLidar 4ROS / TG30 (USB, CP2102) — 30m TOF, 20K sps, 10 Hz |
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
| YDLidar SDK | 1.2.19 | built from source → `/usr/local` |
| ydlidar_ros2_driver | 1.0.1 (humble branch) | in `~/ros2_ws` |

---

## Key File Locations

### On the Jetson (`~/`)
```
~/ros2_ws/src/robot_vision/      ← ROS2 package source
~/ros2_ws/install/               ← colcon --merge-install output (single prefix)
~/start_foxglove.sh              ← start bridge + stats node
~/kill_foxglove.sh               ← kill ALL related processes
~/.ros/foxglove_bridge.log       ← bridge log
~/.ros/foxglove_bridge.pid       ← bridge PID
/dev/ydlidar                     ← udev symlink → ttyUSB0 (CP2102, persistent)
/etc/udev/rules.d/99-ydlidar.rules
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
  lidar.launch.py                ← YDLidar 4ROS launch
  slam.launch.py                 ← LiDAR + SLAM toolbox
  px4_slam.launch.py             ← full stack with Pixhawk
foxglove/
  robot_dashboard.json           ← Foxglove layout (import via Layouts menu)
scripts/
  start_foxglove.sh
  kill_foxglove.sh
  setup_ydlidar_udev.sh          ← auto-detects CP210x, writes udev rule
config/
  ydlidar_4ros.yaml              ← official Yahboom params (TG30/4ROS)
  slam_config.yaml
setup.py
```

---

## ROS2 Topics

### LiDAR (`/scan`)
| Topic | Type | Notes |
|-------|------|-------|
| `/scan` | LaserScan | 10 Hz, 2030 pts/scan, frame `laser` |

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

## Autostart (systemd user services)

Both services are **enabled and start automatically at boot** via systemd user linger.

| Service | Launches | Unit file |
|---------|----------|-----------|
| `robot-foxglove` | `foxglove.launch.py` (bridge + jetson_stats) | `~/.config/systemd/user/robot-foxglove.service` |
| `robot-lidar` | `lidar.launch.py` (YDLidar 4ROS) | `~/.config/systemd/user/robot-lidar.service` |

```bash
# Status
systemctl --user status robot-foxglove robot-lidar

# Logs (live)
journalctl --user -u robot-foxglove -f
journalctl --user -u robot-lidar -f

# Restart after code changes
systemctl --user restart robot-foxglove
systemctl --user restart robot-lidar

# Disable autostart
systemctl --user disable robot-lidar
```

> **Note:** `systemctl --user` over non-interactive SSH requires:
> `export XDG_RUNTIME_DIR=/run/user/1000 && export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus`
> The PowerShell `jstart`/`jstop` aliases handle this automatically.

### Re-installing after Jetson rebuild
```bash
scp scripts/robot-foxglove.service scripts/robot-lidar.service scripts/install_services.sh jetson:~/
ssh jetson "bash ~/install_services.sh"
```

---

## Operational Commands

```bash
# Start full stack (Foxglove bridge + jetson_stats)
ssh jetson "bash ~/start_foxglove.sh"

# Start lidar (separate terminal / session)
ssh jetson "source /opt/ros/humble/setup.bash && source ~/ros2_ws/install/setup.bash && ros2 launch robot_vision lidar.launch.py"

# Restart Foxglove cleanly (ALWAYS kill first — prevents bind error on port 8765)
ssh jetson "bash ~/kill_foxglove.sh && sleep 2 && bash ~/start_foxglove.sh"

# Kill stale foxglove_bridge holding port 8765
ssh jetson "fuser -k 8765/tcp && pkill -f foxglove_bridge; pkill -f jetson_stats"

# Check log
ssh jetson "tail -f ~/.ros/foxglove_bridge.log"

# Verify lidar scanning
ssh jetson "source /opt/ros/humble/setup.bash && source ~/ros2_ws/install/setup.bash && ros2 topic hz /scan --window 5"

# Verify stats topics
ssh jetson "source /opt/ros/humble/setup.bash && source ~/ros2_ws/install/setup.bash && RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ros2 topic echo /jetson/temp/soc --once"

# Rebuild after code changes
ssh jetson "cd ~/ros2_ws && colcon build --merge-install --packages-select robot_vision"

# Deploy config + restart in one line
scp c:\jetson1\config\ydlidar_4ros.yaml jetson:~/ros2_ws/install/share/robot_vision/config/ydlidar_4ros.yaml

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

### 6. `colcon build` must use `--merge-install`
Isolated install (default) does not add `ament_python` packages (e.g. `robot_vision`) to `AMENT_PREFIX_PATH` reliably. Always use:
```bash
colcon build --merge-install
```
Install tree is `~/ros2_ws/install/` as a **single prefix** (no per-package subdirectories).

### 7. YDLidar YAML silently ignored → wrong baudrate
**Symptom:** Node logs `connected [/dev/ydlidar:230400]` even after changing the YAML.  
**Root cause:** Launch file had `name='ydlidar_node'` but the YAML key is `ydlidar_ros2_driver_node:`. ROS2 matches params by node name — mismatch = all params ignored, SDK falls back to compiled-in default (230400).  
**Fix:** Set `name='ydlidar_ros2_driver_node'` in `lidar.launch.py`. Commit `2735482`.

### 8. YDLidar 4ROS correct params (TG30 hardware)
From official Yahboom `ydlidar_4ros.yaml`:
```yaml
lidar_type: 0        # TYPE_TOF — NOT 1 (triangulation)
sample_rate: 20      # 20K sps — NOT 5
resolution_fixed: true   # NOT fixed_resolution (SDK ignores unknown keys)
reversion: false
inverted: true
range_max: 64.0
range_min: 0.01
baudrate: 512000
```

### 9. Foxglove bridge `Bind Error` on restart
**Symptom:** `Couldn't initialize websocket server: Bind Error` — previous instance still holding port 8765.  
**Fix:** `fuser -k 8765/tcp` before restarting. The `kill_foxglove.sh` script handles this.

---

## Foxglove Dashboard Layout

File: `foxglove/robot_dashboard.json` — import via **Layouts → Import from file**

| Panel | Topics |
|-------|--------|
| 3D | `/scan` (LaserScan, turbo colormap), `/map`, `/camera/color/image_raw`, `/odom` — follows `base_link` |
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

| Task | Notes |
|------|-------|
| **D455 camera** | `ros2 launch robot_vision robot_vision.launch.py` |
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
| `2735482` | fix: correct 4ROS params from official Yahboom YAML (lidar_type TOF, 20K sps, node name match) |
| `cadfcf4` | feat: YDLidar 4ROS integration (SDK, driver, udev, config, launch) |
| `f0e8e9f` | fix: kill script matches installed binary name `jetson_stats` — **root cause of SoC spikes** |
| `d352d70` | fix: use jtop callback to guarantee fresh data on publish |
| `afa1583` | fix: cache last-good temp values (intermediate attempt) |
| `a0db3af` | fix: correct Foxglove Plot schema — paths[].id + foxglovePanelTitle |
| `a0749ff` | fix: jtop temp keys lowercase on Orin Nano; add Tj(peak) topic |
