#!/bin/bash
set -e

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"; exit 1
fi

echo "Disabling Bluetooth PAN (NAP)..."

bt-network -d nap pan0 || true
ip link set pan0 down || true

echo "Bluetooth PAN disabled."
