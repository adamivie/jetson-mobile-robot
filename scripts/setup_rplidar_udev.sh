#!/bin/bash
# udev rule for RPLidar S2L (CP2102 USB-UART, VID 10c4 PID ea60)
echo 'KERNEL=="ttyUSB*", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", SYMLINK+="rplidar", MODE="0666"' \
  | sudo tee /etc/udev/rules.d/99-rplidar.rules
sudo udevadm control --reload-rules
echo "udev rule written:"
cat /etc/udev/rules.d/99-rplidar.rules
