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
| **FC** | Pixhawk 6X — ArduRover firmware, USB-C → `/dev/pixhawk` (ttyACM0) |
| **Drive** | 4-wheel mecanum, skid-steer frame — Ch1=strafe, Ch2=right, Ch3=left, Ch4=rotate |
| **SSH** | `Host jetson` → `slurd@10.0.0.104` (WiFi, DHCP) · `Host jetson-usb` → `slurd@192.168.55.1` (USB-C, always stable) |

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
| MAVROS | 2.14.0 | `ros-humble-mavros` + extras, GeographicLib datasets |
| pymavlink | latest | direct RC override (TX-free drive) |

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
/dev/pixhawk                     ← udev symlink → ttyACM0 (VID=1209, PID=5740)
/etc/udev/rules.d/99-ydlidar.rules
/etc/udev/rules.d/99-pixhawk.rules
```

### In this repo (`c:\jetson1\`)
```
robot_vision/
  jetson_stats_node.py           ← jtop ROS2 node (10 topics @ 1 Hz)
  depth_processor.py             ← D455 depth → obstacle distance
  obstacle_detector.py           ← obstacle stop flag
  px4_bridge.py                  ← Pixhawk uXRCE-DDS bridge (unused — ArduRover uses MAVROS)
  mecanum_drive_node.py          ← /cmd_vel → MAVLink RC override @ 20 Hz
launch/
  foxglove.launch.py             ← launches jetson_stats + foxglove_bridge
  robot_vision.launch.py         ← D455 camera launch
  lidar.launch.py                ← YDLidar 4ROS launch
  slam.launch.py                 ← LiDAR + SLAM toolbox
  mavros.launch.py               ← MAVROS ArduRover bridge
  mecanum_drive.launch.py        ← mecanum_drive_node (cmd_vel → RC override)
config/
  mavros.yaml                    ← fcu_url=/dev/pixhawk:115200, no plugin_allowlist
  ydlidar_4ros.yaml              ← official Yahboom params (TG30/4ROS)
  slam_config.yaml
scripts/
  robot-foxglove.service         ← systemd user service
  robot-lidar.service            ← systemd user service
  robot-mavros.service           ← systemd user service (After=robot-foxglove)
  robot-drive.service            ← systemd user service (After=robot-mavros)
  install_services.sh            ← install + enable all 4 services
  rc_drive.py                    ← manual pymavlink RC override test script
  read_rc.py                     ← read live RC channel values from Pixhawk
  disable_rc_failsafe.py         ← set FS_THR_ENABLE=0, FS_GCS_ENABLE=0 etc.
  pull_px4_params.py             ← dump all 936 ArduRover params
foxglove/
  robot_dashboard.json           ← Foxglove layout (import via Layouts menu)
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

All services are **enabled and start automatically at boot** via systemd user linger.

| Service | Launches | After | Notes |
|---------|----------|-------|-------|
| `robot-foxglove` | `foxglove.launch.py` (bridge + jetson_stats) | — | always on |
| `robot-lidar` | `lidar.launch.py` (YDLidar 4ROS only) | — | **disabled when SLAM active** |
| `robot-slam` | `slam.launch.py` (YDLidar + slam_toolbox) | `robot-foxglove` | **conflicts with robot-lidar** |
| `robot-mavros` | `mavros.launch.py` (MAVROS ArduRover bridge) | `robot-foxglove` | always on |
| `robot-drive` | `mecanum_drive.launch.py` (cmd_vel → RC override) | `robot-mavros` | always on |

> **SLAM vs lidar-only:** Only one of `robot-slam` / `robot-lidar` can run at a time — both own `/dev/ydlidar`.
> Use the helper scripts to switch:
> ```bash
> bash ~/use_slam.sh    # switch to SLAM mode (disables robot-lidar, enables robot-slam)
> bash ~/use_lidar.sh   # switch back to lidar-only
> ```

```bash
# Status
systemctl --user status robot-foxglove robot-slam robot-mavros robot-drive

# Logs (live)
journalctl --user -u robot-foxglove -f
journalctl --user -u robot-slam -f
journalctl --user -u robot-mavros -f
journalctl --user -u robot-drive -f

# Restart after code changes
systemctl --user restart robot-foxglove
systemctl --user restart robot-slam
systemctl --user restart robot-mavros
systemctl --user restart robot-drive
```

> **Note:** `systemctl --user` over non-interactive SSH requires:
> `export XDG_RUNTIME_DIR=/run/user/1000 && export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus`
> The PowerShell `jstart`/`jstop` aliases handle this automatically.

### Re-installing after Jetson rebuild
```bash
scp scripts/robot-foxglove.service scripts/robot-lidar.service scripts/robot-slam.service scripts/robot-mavros.service scripts/robot-drive.service scripts/install_services.sh scripts/use_slam.sh scripts/use_lidar.sh jetson-usb:~/
ssh jetson-usb "bash ~/install_services.sh && bash ~/use_slam.sh"
```

---

## SLAM (slam_toolbox — lidar-only, no encoders)

### How it works without wheel encoders
slam_toolbox builds maps via **pure scan-matching** — it doesn't need odometry to accumulate a map.
The `odom→base_link` transform is a static identity TF (robot appears stationary in odom frame).
slam_toolbox uses consecutive scan correlation to estimate motion. Works well indoors at walking speed.

**Limitation:** Without odometry, `minimum_travel_distance` and `minimum_travel_heading` must be `0.0`
so every scan is processed (not just scans after detected motion). This is set in `config/slam_toolbox.yaml`.

### TF Tree
```
map → odom → base_link → laser
       ↑           ↑
  slam_toolbox  static TF   (odom→base_link = identity until encoders added)
  publishes     (0,0,0.1m)
  map→odom
```

### Topics published
| Topic | Type | Notes |
|-------|------|-------|
| `/map` | OccupancyGrid | Live 5cm resolution map |
| `/map_metadata` | MapMetaData | Map dimensions |
| `/scan` | LaserScan | 10 Hz, ~1970 pts, frame `laser` |
| `/tf` | TF | `map→odom` (slam_toolbox), `base_link→laser` (static), `odom→base_link` (static identity) |

### Save / load a map
```bash
# Save current map to file (while SLAM is running)
ssh jetson "source /opt/ros/humble/setup.bash && source ~/ros2_ws/install/setup.bash && export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp && ros2 service call /slam_toolbox/save_map slam_toolbox/srv/SaveMap '{name: {data: /home/slurd/maps/mymap}}'"

# Serialise the full pose graph (reloadable)
ros2 service call /slam_toolbox/serialize_map slam_toolbox/srv/SerializePoseGraph '{filename: {data: /home/slurd/maps/mymap}}'
```

### Foxglove SLAM Dashboard
- **File:** `foxglove/slam_dashboard.json` — import via **Layouts → Import from file**
- **Connection:** `ws://10.0.0.104:8765`
- **3D panel:** `/map` (blue fill) + `/scan` (turbo), top-down view, follows `base_link`
- **FC State panel:** `/mavros/state.system_status` (4=active) + VFR HUD speed/heading
- **IMU panel:** `/mavros/mavros/data` angular velocity X/Y/Z  ← MAVROS 2.14 uses double namespace
- **cmd_vel publish panel:** pre-filled forward command

> **MAVROS 2.14 topic namespace quirk:** IMU is at `/mavros/mavros/data` (not `/mavros/imu/data`).
> `connected`/`armed` are booleans — Foxglove Plot can't graph them. Use `system_status` (int) instead.

---

## Pixhawk 6X / ArduRover

### Hardware
- **Connection:** USB-C (Pixhawk) → USB-A (Jetson) → `/dev/pixhawk` (udev symlink → ttyACM0)
- **udev rule:** `/etc/udev/rules.d/99-pixhawk.rules` — VID=1209, PID=5740, MODE=0666
- **Firmware:** ArduRover (confirmed — 936 params, `FRAME_CLASS=2`, `FRAME_TYPE=3`)
- **Frame:** Skid steer with mecanum wheels

### Key ArduRover Params
| Param | Value | Notes |
|-------|-------|-------|
| `FRAME_CLASS` | 2 | Rover |
| `FRAME_TYPE` | 3 | Skid steer |
| `SERVO1_FUNCTION` | 33 | Steering |
| `SERVO3_FUNCTION` | 35 | Throttle |
| `CRUISE_SPEED` | 2.0 | m/s |
| `ARMING_CHECK` | 0 | Disabled |
| `ARMING_REQUIRE` | 0 | Disabled |
| `FS_THR_ENABLE` | 0 | RC failsafe off |
| `FS_GCS_ENABLE` | 0 | GCS failsafe off |
| `RC_OVERRIDE_TIME` | -1 | Override never expires |

### RC Channel Mapping (confirmed physical)
| Channel | Function | 1000 | 1500 | 2000 |
|---------|----------|------|------|------|
| Ch1 | Strafe | Left | Stop | Right |
| Ch2 | Right wheels | Reverse | Stop | Forward |
| Ch3 | Left wheels | Reverse | Stop | Forward |
| Ch4 | Rotate | Right | Stop | Left |

### cmd_vel → RC Override Mapping
| `cmd_vel` field | RC channel | Notes |
|-----------------|-----------|-------|
| `linear.x` | Ch2 + Ch3 | Forward/reverse both wheel sets |
| `linear.y` | Ch1 | Strafe (mecanum only) |
| `angular.z` | Ch4 + differential Ch2/Ch3 | Rotate |

### Drive Commands
```bash
# Forward at 50%
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist '{linear: {x: 0.5}}'

# Strafe right
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist '{linear: {y: 0.5}}'

# Rotate left
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist '{angular: {z: 0.5}}'

# Combined diagonal + rotate
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist '{linear: {x: 0.3, y: 0.2}, angular: {z: -0.1}}'
```
> **Important:** Publish at ≥ 2 Hz — `mecanum_drive_node` stops wheels after 0.5s without a message.

### Manual RC Override (test / debug)
```bash
# Stop MAVROS first (serial port conflict with direct pymavlink)
systemctl --user stop robot-mavros robot-drive

python3 ~/rc_drive.py <left_pwm> <right_pwm> <duration> [strafe_pwm] [rotate_pwm]
# e.g. forward: python3 ~/rc_drive.py 2000 2000 2
# e.g. strafe right: python3 ~/rc_drive.py 1500 1500 2 2000

systemctl --user start robot-mavros robot-drive
```

### MAVROS Topics
| Topic | Type | Notes |
|-------|------|-------|
| `/mavros/state` | State | `connected`, `armed`, `mode` |
| `/mavros/imu/data` | Imu | 50 Hz |
| `/mavros/battery` | BatteryState | |
| `/cmd_vel` | Twist | **mecanum_drive_node** subscribes here |



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
| **Static IP** | DHCP reservation for `10.0.0.104` before robot goes mobile |
| **Nav stack** | Nav2 with `/cmd_vel` → already wired to mecanum drive (needs encoders for full autonomy) |
| **Wheel encoders** | Add to drive motors → real odom → Nav2 local planner |
| **Foxglove gamepad** | Publish `/cmd_vel` from Foxglove joystick panel |

---

## Git History (key commits)

| Commit | Description |
|--------|-------------|
| `ba944d6` | fix: Foxglove dashboard — correct MAVROS topic paths for v2.14 namespace |
| `513dad5` | feat: Foxglove SLAM dashboard — map 3D, cmd_vel publish, MAVROS IMU/state, temps |
| `bc74c55` | fix: ydlidar udev rule VID/PID not KERNELS path (was mapping to Pixhawk port) |
| `3993cd8` | feat: SLAM launch — YDLidar 4ROS + slam_toolbox, static TFs |
| `d303972` | feat: mecanum cmd_vel node + drive scripts + robot-drive service |
| `7284f80` | feat: MAVROS ArduRover bridge — launch, config, systemd service |
| `2735482` | fix: correct 4ROS params from official Yahboom YAML (lidar_type TOF, 20K sps, node name match) |
| `cadfcf4` | feat: YDLidar 4ROS integration (SDK, driver, udev, config, launch) |
| `f0e8e9f` | fix: kill script matches installed binary name `jetson_stats` — root cause of SoC spikes |
| `a0db3af` | fix: correct Foxglove Plot schema — paths[].id + foxglovePanelTitle |
| `a0749ff` | fix: jtop temp keys lowercase on Orin Nano; add Tj(peak) topic |
