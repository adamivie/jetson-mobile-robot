#!/usr/bin/env python3
import sys
import time
from pymavlink import mavutil

DEVICE = '/dev/ttyACM0'
BAUD = 57600

print(f"Connecting to {DEVICE} @ {BAUD}...")
m = mavutil.mavlink_connection(DEVICE, baud=BAUD)

print("Waiting for heartbeat...")
hb = m.wait_heartbeat(timeout=15)
if not hb:
    print("ERROR: No heartbeat received")
    sys.exit(1)

print(f"Heartbeat OK — sysid={m.target_system} compid={m.target_component}")
print("Requesting all params...")
m.mav.param_request_list_send(m.target_system, m.target_component)

params = {}
deadline = time.time() + 20
while time.time() < deadline:
    msg = m.recv_match(type='PARAM_VALUE', blocking=True, timeout=1)
    if msg:
        params[msg.param_id] = msg.param_value

print(f"\nTotal params fetched: {len(params)}\n")

# Key params to display
keys = [
    'SYS_AUTOSTART',   # vehicle/airframe type
    'MAV_TYPE',
    'UXRCE_DDS_CFG',   # DDS port config
    'SERIAL0_BAUD',
    'GND_MAX_THR',     # rover throttle
    'GND_SPEED_MAX',
    'GND_SPEED_TRIM',
    'GND_WP_RADIUS',
    'GND_L1_PERIOD',
    'GND_L1_DAMPING',
    'GND_THR_MAX',
    'GND_THR_MIN',
    'GND_THR_CRUISE',
    'NAV_ACC_RAD',
    'COM_DISARM_LAND',
    'EKF2_AID_MASK',
    'EKF2_HGT_REF',
]

print("=== Key Params ===")
for k in keys:
    if k in params:
        print(f"  {k:30s} = {params[k]}")
    else:
        print(f"  {k:30s} = (not found)")

# Save all params to file
with open('/tmp/px4_params.txt', 'w') as f:
    for k, v in sorted(params.items()):
        f.write(f"{k}={v}\n")
print("\nAll params saved to /tmp/px4_params.txt")
