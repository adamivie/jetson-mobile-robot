#!/bin/bash
pkill -f foxglove_bridge 2>/dev/null
pkill -f test_foxglove 2>/dev/null
sleep 2
ss -tlnp | grep 8765 && echo "WARNING: port still in use" || echo "port 8765 clear"
