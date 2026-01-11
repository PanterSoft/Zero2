#!/bin/bash
set -e

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"; exit 1
fi

echo "Disabling WiFi hotspot..."

systemctl stop hostapd dnsmasq || true
rm -f /etc/dnsmasq.d/zero2-hotspot.conf

# Flush hotspot address and restart networking (ifupdown)
ip addr flush dev wlan0 || true
systemctl restart networking || true

echo "Hotspot disabled. wlan0 returned to normal client mode."