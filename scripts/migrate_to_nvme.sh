#!/bin/bash
set -e

NVME=/dev/nvme0n1
MOUNT=/mnt/nvme

echo "=== Step 1: Partition NVMe ==="
sudo parted -s $NVME mklabel gpt
sudo parted -s $NVME mkpart primary ext4 0% 100%
sudo partprobe $NVME
sleep 2

echo "=== Step 2: Format ==="
sudo mkfs.ext4 -L jetson-nvme ${NVME}p1

echo "=== Step 3: Mount ==="
sudo mkdir -p $MOUNT
sudo mount ${NVME}p1 $MOUNT

echo "=== Step 4: rsync eMMC -> NVMe (this will take a few minutes) ==="
sudo rsync -aAXH --info=progress2 \
  --exclude=/proc \
  --exclude=/sys \
  --exclude=/dev \
  --exclude=/run \
  --exclude=/tmp \
  --exclude=/mnt \
  --exclude=/media \
  --exclude=/lost+found \
  / $MOUNT/

echo "=== Step 5: Recreate excluded dirs ==="
for d in proc sys dev run tmp mnt media; do
  sudo mkdir -p $MOUNT/$d
done

echo "=== Step 6: Update /etc/fstab on NVMe ==="
NVME_UUID=$(sudo blkid -s UUID -o value ${NVME}p1)
echo "NVMe UUID: $NVME_UUID"
sudo sed -i "s|UUID=[^ ]*\s\+/\s|UUID=${NVME_UUID} / |" $MOUNT/etc/fstab
echo "--- fstab on NVMe ---"
cat $MOUNT/etc/fstab

echo "=== Step 7: Update extlinux.conf to boot from NVMe ==="
sudo cp /boot/extlinux/extlinux.conf /boot/extlinux/extlinux.conf.emmc.bak
sudo sed -i "s|root=[^ ]*|root=${NVME}p1|g" /boot/extlinux/extlinux.conf
echo "--- extlinux.conf ---"
cat /boot/extlinux/extlinux.conf

echo ""
echo "=== DONE — reboot to verify: sudo reboot ==="
echo "NVMe UUID: $NVME_UUID"
