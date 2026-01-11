#!/bin/bash
set -e

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"; exit 1
fi

echo "Disabling USB Ethernet gadget..."

ip link set usb0 down || true
rmmod g_ether || true

echo "USB gadget disabled."
