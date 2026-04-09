#!/usr/bin/env python3
"""
Send RC override directly via MAVLink - bypasses MAVROS.

Channel mapping (confirmed):
  Ch1 = Strafe      (right stick L/R) - mecanum sideways
  Ch2 = Right wheels
  Ch3 = Left wheels
  Ch4 = Rotate      (left stick L/R)

Usage: python3 rc_drive.py <left_pwm> <right_pwm> <duration_sec> [strafe_pwm] [rotate_pwm]
  PWM range: 1000=full reverse, 1500=stop, 2000=full forward
Examples:
  python3 rc_drive.py 2000 2000 2          # forward
  python3 rc_drive.py 1000 1000 2          # reverse
  python3 rc_drive.py 2000 1000 2          # spin left
  python3 rc_drive.py 1000 2000 2          # spin right
  python3 rc_drive.py 1500 1500 2 2000     # strafe right
  python3 rc_drive.py 1500 1500 2 1000     # strafe left
"""
import sys
import time
from pymavlink import mavutil

DEVICE = '/dev/pixhawk'
BAUD = 115200

left_pwm   = int(sys.argv[1])   if len(sys.argv) > 1 else 1500
right_pwm  = int(sys.argv[2])   if len(sys.argv) > 2 else 1500
duration   = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
strafe_pwm = int(sys.argv[4])   if len(sys.argv) > 4 else 65535
rotate_pwm = int(sys.argv[5])   if len(sys.argv) > 5 else 65535

print(f"Connecting to {DEVICE}...")
m = mavutil.mavlink_connection(DEVICE, baud=BAUD)
m.wait_heartbeat(timeout=10)
print(f"Connected - sysid={m.target_system}")

print("Setting MANUAL mode...")
m.mav.set_mode_send(
    m.target_system,
    mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
    0
)
time.sleep(0.5)

def make_channels(left, right, strafe=65535, rotate=65535):
    return [strafe, right, left, rotate, 65535, 65535, 65535, 65535]

print(f"left={left_pwm} right={right_pwm} strafe={strafe_pwm} rotate={rotate_pwm} dur={duration}s")
deadline = time.time() + duration
while time.time() < deadline:
    m.mav.rc_channels_override_send(
        m.target_system, m.target_component,
        *make_channels(left_pwm, right_pwm, strafe_pwm, rotate_pwm)
    )
    time.sleep(0.05)

print("Stopping...")
for _ in range(20):
    m.mav.rc_channels_override_send(
        m.target_system, m.target_component,
        *make_channels(1500, 1500, 1500, 1500)
    )
    time.sleep(0.05)

print("Done.")
