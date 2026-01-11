#!/bin/bash
set -e

# ==============================================================================
# ZERO2 WiFi HOTSPOT ENABLER
# ==============================================================================
# This script TEMPORARILY enables WiFi hotspot mode
# Use ONLY when normal WiFi is unavailable
# To disable: sudo systemctl stop hostapd dnsmasq

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

echo "Enabling WiFi Hotspot on wlan0..."

# Stop normal WiFi management temporarily
echo "Stopping normal WiFi..."
systemctl stop networking || true
killall wpa_supplicant || true

# Configure hostapd
echo "Configuring hostapd..."
mkdir -p /etc/hostapd
cat > /etc/hostapd/hostapd.conf <<EOF
interface=wlan0
driver=nl80211
ssid=Zero2_Hotspot
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=zero2pass
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF

# Set hostapd config path
sed -i 's|^#DAEMON_CONF=.*|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd || echo 'DAEMON_CONF="/etc/hostapd/hostapd.conf"' >> /etc/default/hostapd

# Configure dnsmasq
echo "Configuring dnsmasq..."
cp /etc/dnsmasq.conf /etc/dnsmasq.conf.bak || true
cat > /etc/dnsmasq.conf <<EOF
interface=wlan0
dhcp-range=192.168.50.10,192.168.50.50,255.255.255.0,24h
domain=local
address=/gw.local/192.168.50.1
EOF

# Configure wlan0 for hotspot
echo "Configuring wlan0 for hotspot..."
ip link set wlan0 down || true
ip addr flush dev wlan0 || true
ip link set wlan0 up
ip addr add 192.168.50.1/24 dev wlan0

# Enable IP forwarding
sysctl -w net.ipv4.ip_forward=1

# Start services
echo "Starting hotspot services..."
systemctl unmask hostapd
systemctl start hostapd
systemctl start dnsmasq

echo ""
echo "================== WiFi Hotspot ENABLED =================="
echo "SSID: Zero2_Hotspot"
echo "Password: zero2pass"
echo "IP: 192.168.50.1"
echo "DHCP: 192.168.50.10-50"
echo ""
echo "To DISABLE hotspot and return to normal WiFi:"
echo "  sudo systemctl stop hostapd dnsmasq"
echo "  sudo systemctl restart networking"
echo "========================================================"
