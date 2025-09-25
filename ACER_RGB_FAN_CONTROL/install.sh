#!/bin/bash
set -e

echo "[*] Installing dependencies..."
sudo apt update
sudo apt install -y python3 python3-pip python3-usb libusb-1.0-0 \
    build-essential linux-headers-$(uname -r) \
    python3-dev libncurses5-dev libncursesw5-dev

echo "[*] Building and installing facer driver..."
sudo mkdir -p /lib/modules/$(uname -r)/extra

# Always regenerate Makefile
cat > src/Makefile << 'EOF'
obj-m += facer.o

all:
	$(MAKE) -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules

clean:
	$(MAKE) -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean
EOF

# Build module
make -C /lib/modules/$(uname -r)/build M=$(pwd)/src modules

# Copy to modules directory
sudo cp src/facer.ko /lib/modules/$(uname -r)/extra/
sudo depmod -a

# Blacklist stock acer_wmi
echo "blacklist acer_wmi" | sudo tee /etc/modprobe.d/blacklist-acer.conf > /dev/null

# Ensure facer loads at boot
echo "facer" | sudo tee /etc/modules-load.d/facer.conf > /dev/null

# Enable EC sysfs with write support (permanent)
echo "options ec_sys write_support=1" | sudo tee /etc/modprobe.d/ec_sys.conf > /dev/null
echo "ec_sys" | sudo tee /etc/modules-load.d/ec_sys.conf > /dev/null

# Reload modules now
sudo modprobe -r acer_wmi 2>/dev/null || true
sudo modprobe -r ec_sys 2>/dev/null || true
sudo modprobe ec_sys write_support=1
sudo modprobe facer || sudo insmod /lib/modules/$(uname -r)/extra/facer.ko

echo "[*] Copying Python helpers..."
sudo cp fix_keyboard.py /usr/local/bin/fix_keyboard.py
sudo chmod +x /usr/local/bin/fix_keyboard.py

sudo cp fix-keyboard.service /etc/systemd/system/fix-keyboard.service
sudo systemctl daemon-reload
sudo systemctl enable fix-keyboard.service

echo "[*] Adding predator alias..."
if ! grep -q "alias predator=" ~/.bashrc; then
  echo "alias predator='sudo python3 $(pwd)/main.py'" >> ~/.bashrc
fi

echo "[*] Done.Type : sudo python3 main.py : If it does not work reboot run sudo python3 main.py again"

