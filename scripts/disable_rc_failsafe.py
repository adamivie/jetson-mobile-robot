#!/usr/bin/env python3
"""
Disable RC/TX requirement on ArduRover so it runs TX-free.
Sets params via MAVLink then saves to EEPROM.
"""
import time
import sys
from pymavlink import mavutil

DEVICE = '/dev/pixhawk'
BAUD = 115200

print(f"Connecting to {DEVICE}...")
m = mavutil.mavlink_connection(DEVICE, baud=BAUD)
m.wait_heartbeat(timeout=10)
print(f"Connected — sysid={m.target_system}")

def set_param(name, value, ptype=9):  # 9 = MAV_PARAM_TYPE_REAL32
    m.mav.param_set_send(
        m.target_system, m.target_component,
        name.encode('utf-8'),
        float(value),
        ptype
    )
    # Wait for ACK
    deadline = time.time() + 3
    while time.time() < deadline:
        msg = m.recv_match(type='PARAM_VALUE', blocking=True, timeout=1)
        if msg and msg.param_id.strip('\x00') == name:
            print(f"  SET {name} = {msg.param_value}")
            return True
    print(f"  WARN: No ACK for {name}")
    return False

print("\nDisabling RC/TX requirements...")

# Disable throttle failsafe (no TX needed)
set_param('FS_THR_ENABLE', 0)

# Disable GCS failsafe
set_param('FS_GCS_ENABLE', 0)

# Disable RC override expiry (-1 = never expire)
set_param('RC_OVERRIDE_TIME', -1)

# Allow arming without RC
set_param('ARMING_CHECK', 0)
set_param('ARMING_REQUIRE', 0)

# Allow GUIDED without GPS
set_param('GUIDED_OPTIONS', 8)

print("\nSaving to EEPROM...")
m.mav.command_long_send(
    m.target_system, m.target_component,
    mavutil.mavlink.MAV_CMD_PREFLIGHT_STORAGE,
    0, 1, 0, 0, 0, 0, 0, 0
)
time.sleep(2)
print("Done. Rebooting FC...")
m.mav.command_long_send(
    m.target_system, m.target_component,
    mavutil.mavlink.MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN,
    0, 1, 0, 0, 0, 0, 0, 0
)
time.sleep(3)
print("Reboot command sent. Wait 5s then reconnect.")
