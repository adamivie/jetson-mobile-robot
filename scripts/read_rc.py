#!/usr/bin/env python3
"""
Read RC channels from ArduRover and display live.
Move each stick to identify channel mapping.
"""
import time
from pymavlink import mavutil

DEVICE = '/dev/pixhawk'
BAUD = 115200

print(f"Connecting to {DEVICE}...")
m = mavutil.mavlink_connection(DEVICE, baud=BAUD)
m.wait_heartbeat(timeout=10)
print(f"Connected — sysid={m.target_system}")
print("\nMove sticks to identify channels. Ctrl+C to stop.\n")
print(f"{'Ch1':>6} {'Ch2':>6} {'Ch3':>6} {'Ch4':>6} {'Ch5':>6} {'Ch6':>6} {'Ch7':>6} {'Ch8':>6}")
print("-" * 56)

try:
    while True:
        msg = m.recv_match(type='RC_CHANNELS', blocking=True, timeout=1)
        if msg:
            print(f"\r{msg.chan1_raw:>6} {msg.chan2_raw:>6} {msg.chan3_raw:>6} {msg.chan4_raw:>6} "
                  f"{msg.chan5_raw:>6} {msg.chan6_raw:>6} {msg.chan7_raw:>6} {msg.chan8_raw:>6}", end='', flush=True)
except KeyboardInterrupt:
    print("\nDone.")
