#!/bin/bash
set -e

echo "[*] Stopping and removing systemd service..."
sudo systemctl stop fix-keyboard.service || true
sudo systemctl disable fix-keyboard.service || true
sudo rm -f /etc/systemd/system/fix-keyboard.service
sudo systemctl daemon-reload

echo "[*] Removing Python helper..."
sudo rm -f /usr/local/bin/fix_keyboard.py

echo "[*] Removing predator alias from ~/.bashrc..."
sed -i '/alias predator=/d' ~/.bashrc

echo "[*] Removing facer driver..."
sudo rmmod facer || true
sudo rm -f /lib/modules/$(uname -r)/extra/facer.ko
sudo depmod -a

echo "[*] Restoring acer_wmi..."
sudo modprobe acer_wmi || true

echo "[*] Cleaning module config..."
sudo rm -f /etc/modules-load.d/facer.conf
sudo rm -f /etc/modprobe.d/blacklist-acer.conf

echo "[*] Cleaning build artifacts..."
rm -f src/Makefile
make -C /lib/modules/$(uname -r)/build M=$(pwd)/src clean || true

echo "[*] Uninstall complete. Reboot recommended."

