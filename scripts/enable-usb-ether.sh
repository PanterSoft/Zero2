#!/bin/bash
set -e

# Enable USB Gadget Ethernet (usb0) for SSH over USB

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"; exit 1
fi

USB_IP=${USB_IP:-10.10.20.1}

echo "Enabling USB Ethernet gadget..."

modprobe g_ether || true
ip link set usb0 up || true
ip addr add ${USB_IP}/24 dev usb0 || true

echo "USB gadget ready. Connect USB to host, then SSH to ${USB_IP}"
