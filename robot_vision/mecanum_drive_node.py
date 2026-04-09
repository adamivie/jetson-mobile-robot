#!/usr/bin/env python3
"""
mecanum_drive_node — ROS2 cmd_vel → MAVLink RC override for mecanum rover.

Subscribes to /cmd_vel (geometry_msgs/Twist) and sends RC channel overrides
directly via pymavlink (does NOT use MAVROS, no serial port conflict).

Channel mapping (confirmed physical):
  Ch1 = Strafe      (linear.y)  : 1000=left,  1500=stop, 2000=right
  Ch2 = Right wheels (linear.x) : 1000=rev,   1500=stop, 2000=fwd
  Ch3 = Left wheels  (linear.x) : 1000=rev,   1500=stop, 2000=fwd
  Ch4 = Rotate       (angular.z): 1000=right,  1500=stop, 2000=left

Velocity → PWM scaling (tuneable via ROS params):
  max_linear  = 1.0 m/s  → ±500 PWM units from 1500 center
  max_angular = 1.0 rad/s → ±500 PWM units from 1500 center
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from pymavlink import mavutil
import threading
import time


class MecanumDriveNode(Node):
    def __init__(self):
        super().__init__('mecanum_drive_node')

        # ── ROS parameters ──────────────────────────────────────────────────
        self.declare_parameter('device',       '/dev/pixhawk')
        self.declare_parameter('baud',         115200)
        self.declare_parameter('max_linear',   1.0)    # m/s maps to ±500 PWM
        self.declare_parameter('max_angular',  1.0)    # rad/s maps to ±500 PWM
        self.declare_parameter('override_hz',  20.0)   # RC override publish rate
        self.declare_parameter('cmd_timeout',  0.5)    # secs without cmd → stop

        self.device      = self.get_parameter('device').value
        self.baud        = self.get_parameter('baud').value
        self.max_linear  = self.get_parameter('max_linear').value
        self.max_angular = self.get_parameter('max_angular').value
        self.override_hz = self.get_parameter('override_hz').value
        self.cmd_timeout = self.get_parameter('cmd_timeout').value

        # ── State ────────────────────────────────────────────────────────────
        self._lock          = threading.Lock()
        self._last_cmd      = None          # Twist
        self._last_cmd_time = 0.0
        self._mav           = None
        self._connected     = False

        # ── Connect to Pixhawk in background thread ──────────────────────────
        self._connect_thread = threading.Thread(target=self._connect, daemon=True)
        self._connect_thread.start()

        # ── Subscription ────────────────────────────────────────────────────
        self.sub = self.create_subscription(Twist, '/cmd_vel', self._cmd_cb, 10)

        # ── RC override timer ────────────────────────────────────────────────
        period = 1.0 / self.override_hz
        self.timer = self.create_timer(period, self._send_override)

        self.get_logger().info(
            f'mecanum_drive_node started — device={self.device} '
            f'max_linear={self.max_linear} max_angular={self.max_angular}'
        )

    # ── MAVLink connection ───────────────────────────────────────────────────
    def _connect(self):
        while rclpy.ok():
            try:
                self.get_logger().info(f'Connecting to {self.device}...')
                mav = mavutil.mavlink_connection(self.device, baud=self.baud)
                mav.wait_heartbeat(timeout=15)
                # Set MANUAL mode (mode 0 for ArduRover custom mode)
                mav.mav.set_mode_send(
                    mav.target_system,
                    mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                    0   # MANUAL
                )
                time.sleep(0.3)
                with self._lock:
                    self._mav = mav
                    self._connected = True
                self.get_logger().info(
                    f'Connected — sysid={mav.target_system}'
                )
                break
            except Exception as e:
                self.get_logger().error(f'MAVLink connect failed: {e}  retrying in 5s...')
                time.sleep(5)

    # ── cmd_vel callback ─────────────────────────────────────────────────────
    def _cmd_cb(self, msg: Twist):
        with self._lock:
            self._last_cmd      = msg
            self._last_cmd_time = time.time()

    # ── Velocity → PWM helpers ───────────────────────────────────────────────
    def _vel_to_pwm(self, vel: float, max_vel: float) -> int:
        """Map [-max_vel, +max_vel] → [1000, 2000] with 1500 center."""
        scale = max(min(vel / max_vel, 1.0), -1.0)
        return int(1500 + scale * 500)

    def _make_channels(self, fwd: float, strafe: float, yaw: float):
        """Return 8-channel RC override list.
        Ch1=strafe, Ch2=right, Ch3=left, Ch4=rotate (1-indexed).
        63535 = passthrough (let TX control that channel).
        """
        ch_fwd    = self._vel_to_pwm(fwd,    self.max_linear)
        ch_strafe = self._vel_to_pwm(strafe, self.max_linear)
        # yaw: positive angular.z = turn left → left wheels slow, right wheels speed up
        ch_left  = self._vel_to_pwm(fwd - yaw * self.max_linear, self.max_linear)
        ch_right = self._vel_to_pwm(fwd + yaw * self.max_linear, self.max_linear)
        ch_rotate = self._vel_to_pwm(-yaw,  self.max_angular)   # Ch4 sign matches TX
        # [ch1, ch2, ch3, ch4, ch5, ch6, ch7, ch8]
        return [ch_strafe, ch_right, ch_left, ch_rotate, 65535, 65535, 65535, 65535]

    # ── RC override send ─────────────────────────────────────────────────────
    def _send_override(self):
        with self._lock:
            if not self._connected or self._mav is None:
                return

            now = time.time()
            if (self._last_cmd is not None and
                    (now - self._last_cmd_time) <= self.cmd_timeout):
                cmd = self._last_cmd
                channels = self._make_channels(
                    cmd.linear.x,
                    cmd.linear.y,
                    cmd.angular.z
                )
            else:
                # Timeout or no command — send stop
                channels = [1500, 1500, 1500, 1500, 65535, 65535, 65535, 65535]

            try:
                self._mav.mav.rc_channels_override_send(
                    self._mav.target_system,
                    self._mav.target_component,
                    *channels
                )
            except Exception as e:
                self.get_logger().warn(f'RC override send failed: {e}')
                with self._lock:
                    self._connected = False
                    self._mav = None
                # Reconnect
                self._connect_thread = threading.Thread(
                    target=self._connect, daemon=True
                )
                self._connect_thread.start()


def main(args=None):
    rclpy.init(args=args)
    node = MecanumDriveNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Send stop before shutting down
        with node._lock:
            if node._connected and node._mav:
                stop = [1500, 1500, 1500, 1500, 65535, 65535, 65535, 65535]
                for _ in range(10):
                    node._mav.mav.rc_channels_override_send(
                        node._mav.target_system,
                        node._mav.target_component,
                        *stop
                    )
                    time.sleep(0.05)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
