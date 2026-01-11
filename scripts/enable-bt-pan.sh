#!/bin/bash
set -e

# Enable Bluetooth PAN (NAP) for SSH over BT

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"; exit 1
fi

BT_IP=${BT_IP:-10.10.10.1}

echo "Enabling Bluetooth PAN (NAP)..."

bt-adapter --set Powered 1 || true
bt-adapter --set Discoverable 1 || true
bt-adapter --set Pairable 1 || true

# Start NAP on pan0 (will appear once a client connects)
bt-network -s nap pan0 || true

# Assign IP if interface exists already
if ip link show pan0 >/dev/null 2>&1; then
  ip addr add ${BT_IP}/24 dev pan0 || true
fi

echo "BT PAN ready. Pair from host, then SSH to ${BT_IP}"
