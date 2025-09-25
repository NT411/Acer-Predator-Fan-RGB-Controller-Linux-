#!/usr/bin/env python3
import usb.core, usb.util

VENDOR_ID = 0x04f2   # change to your Vendor ID
PRODUCT_ID = 0x0117  # change to your Product ID
INTERFACE = 3        # change if needed
PAYLOAD = bytes.fromhex('08 00 01 00 30 06 00 be')

dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
if dev:
    if dev.is_kernel_driver_active(INTERFACE):
        dev.detach_kernel_driver(INTERFACE)
    usb.util.claim_interface(dev, INTERFACE)
    dev.ctrl_transfer(0x21, 0x09, 0x0300, INTERFACE, PAYLOAD)
    usb.util.release_interface(dev, INTERFACE)
