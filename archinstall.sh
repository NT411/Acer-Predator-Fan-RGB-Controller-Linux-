#!/bin/bash
set -e

echo "[*] Installing system packages..."
sudo pacman -Sy --needed --noconfirm \
    python python-pip python-pyusb libusb base-devel linux-headers

echo "[*] Building and installing facer kernel module..."
sudo mkdir -p /lib/modules/$(uname -r)/extra

# Create Makefile
cat > src/Makefile << 'EOF'
obj-m += facer.o

all:
	$(MAKE) -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules

clean:
	$(MAKE) -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean
EOF

# Build kernel module
make -C /lib/modules/$(uname -r)/build M=$(pwd)/src modules

# Install kernel module
sudo cp src/facer.ko /lib/modules/$(uname -r)/extra/
sudo depmod -a

# Blacklist acer_wmi
echo "blacklist acer_wmi" | sudo tee /etc/modprobe.d/blacklist-acer.conf > /dev/null

# Load facer at boot
echo "facer" | sudo tee /etc/modules-load.d/facer.conf > /dev/null

# Enable EC sysfs write support
echo "options ec_sys write_support=1" | sudo tee /etc/modprobe.d/ec_sys.conf > /dev/null
echo "ec_sys" | sudo tee /etc/modules-load.d/ec_sys.conf > /dev/null

# Reload modules
sudo modprobe -r acer_wmi 2>/dev/null || true
sudo modprobe -r ec_sys 2>/dev/null || true
sudo modprobe ec_sys write_support=1
sudo modprobe facer || sudo insmod /lib/modules/$(uname -r)/extra/facer.ko

echo "[*] Copying Python helper script..."
sudo cp fix_keyboard.py /usr/local/bin/fix_keyboard.py
sudo chmod +x /usr/local/bin/fix_keyboard.py

echo "[*] Installing systemd service..."
sudo cp fix-keyboard.service /etc/systemd/system/fix-keyboard.service
sudo systemctl daemon-reload
sudo systemctl enable fix-keyboard.service

echo "[*] Adding 'predator' alias to ~/.bashrc..."
if ! grep -q "alias predator=" ~/.bashrc; then
  echo "alias predator='sudo python3 $(pwd)/main.py'" >> ~/.bashrc
fi

echo "[*] Installation complete!"
echo "You can now run: sudo python3 main.py"
echo "If it doesn't work immediately, reboot and try again."

