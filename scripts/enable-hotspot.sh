#!/bin/bash
set -e

# Temporary WiFi hotspot for recovery or field use
# SSID: Zero2_Hotspot / Pass: zero2pass / IP: 192.168.50.1

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"; exit 1
fi

echo "Enabling WiFi hotspot on wlan0..."

# Stop client-side WiFi to free wlan0
systemctl stop networking || true
killall wpa_supplicant || true

# Hostapd config
mkdir -p /etc/hostapd
cat > /etc/hostapd/zero2-hotspot.conf <<'EOF'
interface=wlan0
driver=nl80211
ssid=Zero2_Hotspot
hw_mode=g
channel=7
wmm_enabled=0
auth_algs=1
wpa=2
wpa_passphrase=zero2pass
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF

# Point hostapd to our config
if grep -q '^DAEMON_CONF=' /etc/default/hostapd; then
  sed -i 's|^DAEMON_CONF=.*|DAEMON_CONF="/etc/hostapd/zero2-hotspot.conf"|' /etc/default/hostapd
else
  echo 'DAEMON_CONF="/etc/hostapd/zero2-hotspot.conf"' >> /etc/default/hostapd
fi

# dnsmasq config lives in its own file to avoid clobbering global config
mkdir -p /etc/dnsmasq.d
cat > /etc/dnsmasq.d/zero2-hotspot.conf <<'EOF'
interface=wlan0
dhcp-range=192.168.50.10,192.168.50.50,255.255.255.0,24h
domain=local
address=/gw.local/192.168.50.1
EOF

# Configure interface
ip link set wlan0 down || true
ip addr flush dev wlan0 || true
ip link set wlan0 up
ip addr add 192.168.50.1/24 dev wlan0 || true

# NAT/forwarding (local only)
sysctl -w net.ipv4.ip_forward=1 >/dev/null

systemctl unmask hostapd || true
systemctl restart dnsmasq
systemctl restart hostapd

echo "Hotspot enabled: SSID=Zero2_Hotspot, Pass=zero2pass, IP=192.168.50.1"
echo "To disable: /usr/local/bin/zero2/disable-hotspot.sh"
