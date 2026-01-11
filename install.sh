#!/bin/bash
set -e

# ==============================================================================
# INSTALLATION CONFIGURATION (Defaults)
# ==============================================================================

# These can be overridden by exporting them before running this script
: "${ENABLE_SSH_BT:=true}"
: "${ENABLE_USB_OTG:=true}"
: "${ENABLE_WIFI_HOTSPOT:=true}"
: "${ENABLE_DISPLAY:=true}"
: "${ENABLE_LOW_BAT:=true}"
: "${OVERCLOCK_PROFILE:=none}"

# System Configuration
INSTALL_DIR="/opt/zero2_controller"
BT_IP="10.10.10.1"        # IP address for Bluetooth interface
USB_IP="10.10.20.1"       # IP address for USB Gadget interface

# ==============================================================================

echo "Starting Zero2 System Installer..."

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

# Ensure we are in the installation directory
if [ "$(pwd)" != "$INSTALL_DIR" ]; then
    echo "Warning: Script not running from $INSTALL_DIR. Attempting to change directory..."
    if [ -d "$INSTALL_DIR" ]; then
        cd "$INSTALL_DIR"
    else
        echo "Error: Installation directory $INSTALL_DIR does not exist."
        echo "Please run the bootstrap script (Automation_Custom_Script.sh) first."
        exit 1
    fi
fi

# 1. Update System & Install Dependencies
echo "Installing system dependencies..."
apt-get update

# Check which packages need to be installed
PACKAGES_TO_INSTALL=()
for pkg in python3-pip python3-venv python3-dev build-essential libdbus-1-dev libglib2.0-dev bluez bluez-tools hostapd dnsmasq i2c-tools libopenjp2-7 libtiff6; do
    if ! dpkg -l | grep -q "^ii  $pkg"; then
        PACKAGES_TO_INSTALL+=("$pkg")
    fi
done

if [ ${#PACKAGES_TO_INSTALL[@]} -gt 0 ]; then
    echo "Installing missing packages: ${PACKAGES_TO_INSTALL[*]}"
    apt-get install -y "${PACKAGES_TO_INSTALL[@]}"
else
    echo "All system dependencies are already installed."
fi

# 2. Setup USB OTG (Ethernet Gadget)
if [ "$ENABLE_USB_OTG" = true ]; then
    echo "Configuring USB OTG..."
    if ! grep -q "dtoverlay=dwc2" /boot/config.txt; then
        echo "dtoverlay=dwc2" >> /boot/config.txt
    fi
    if ! grep -q "modules-load=dwc2,g_ether" /boot/cmdline.txt; then
        sed -i 's/rootwait/rootwait modules-load=dwc2,g_ether/' /boot/cmdline.txt
    fi

    mkdir -p /etc/network/interfaces.d
    cat > /etc/network/interfaces.d/usb0 <<EOF
allow-hotplug usb0
iface usb0 inet static
    address $USB_IP
    netmask 255.255.255.0
EOF
fi

# 3. Setup Bluetooth PAN (Network Access Point)
if [ "$ENABLE_SSH_BT" = true ]; then
    echo "Configuring Bluetooth PAN..."
    cat > /usr/local/bin/simple-bt-nap <<EOF
#!/bin/bash
# Register NAP
bt-adapter --set Powered 1
bt-adapter --set Discoverable 1
bt-adapter --set Pairable 1
EOF
    chmod +x /usr/local/bin/simple-bt-nap

    mkdir -p /etc/network/interfaces.d
    cat > /etc/network/interfaces.d/bnep0 <<EOF
allow-hotplug bnep0
iface bnep0 inet static
    address $BT_IP
    netmask 255.255.255.0
EOF
fi

# 4. Setup WiFi Hotspot
if [ "$ENABLE_WIFI_HOTSPOT" = true ]; then
    echo "Configuring WiFi Hotspot..."

    # Stop services if running
    systemctl stop hostapd dnsmasq || true

    # Configure hostapd
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
    mv /etc/dnsmasq.conf /etc/dnsmasq.conf.bak || true
    cat > /etc/dnsmasq.conf <<EOF
interface=wlan0
dhcp-range=192.168.50.10,192.168.50.50,255.255.255.0,24h
domain=local
address=/gw.local/192.168.50.1
EOF

    # Configure wlan0 static IP
    mkdir -p /etc/network/interfaces.d
    cat > /etc/network/interfaces.d/wlan0 <<EOF
allow-hotplug wlan0
iface wlan0 inet static
    address 192.168.50.1
    netmask 255.255.255.0
    post-up systemctl start hostapd
    post-up systemctl start dnsmasq
EOF

    # Enable IP forwarding
    if ! grep -q "^net.ipv4.ip_forward=1" /etc/sysctl.conf; then
        echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
    fi
    sysctl -w net.ipv4.ip_forward=1

    # Unmask and enable services
    systemctl unmask hostapd
    systemctl enable hostapd
    systemctl enable dnsmasq
fi

# 5. Setup Python Environment
echo "Setting up Python Environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

./venv/bin/pip install -r requirements.txt

# 6. Enable I2C for Display
if [ "$ENABLE_DISPLAY" = true ]; then
    echo "Enabling I2C..."
    if ! grep -q "dtparam=i2c_arm=on" /boot/config.txt; then
        echo "dtparam=i2c_arm=on" >> /boot/config.txt
    fi
    modprobe i2c-dev || true
fi

# Optimize GPU Memory for Headless (Maximize RAM)
if ! grep -q "gpu_mem=" /boot/config.txt; then
    echo "Setting gpu_mem=16 for headless performance"
    echo "gpu_mem=16" >> /boot/config.txt
fi

# 7. Install Systemd Services
echo "Installing Systemd Services..."
cp systemd/zero2-controller.service /etc/systemd/system/
if [ "$ENABLE_SSH_BT" = true ]; then
    cp systemd/bt-nap.service /etc/systemd/system/
    systemctl enable bt-nap.service
fi

systemctl daemon-reload
systemctl enable zero2-controller.service

# 8. Apply Overclocking
if [ "$OVERCLOCK_PROFILE" != "none" ]; then
    echo "Applying Overclock Profile: $OVERCLOCK_PROFILE"

    # Check if already applied to avoid duplicates
    if grep -q "# Zero2 Controller Overclocking" /boot/config.txt; then
        echo "Overclock settings already present. Skipping..."
    else
        # Backup config
        cp /boot/config.txt /boot/config.txt.bak

        echo "" >> /boot/config.txt
        echo "# Zero2 Controller Overclocking ($OVERCLOCK_PROFILE)" >> /boot/config.txt

        case $OVERCLOCK_PROFILE in
            "modest")
                # Modest CPU but High RAM Performance
                echo "arm_freq=1200" >> /boot/config.txt
                echo "over_voltage=2" >> /boot/config.txt
                echo "core_freq=500" >> /boot/config.txt
                echo "sdram_freq=500" >> /boot/config.txt
                echo "over_voltage_sdram=2" >> /boot/config.txt
                ;;
            "high")
                echo "arm_freq=1300" >> /boot/config.txt
                echo "over_voltage=3" >> /boot/config.txt
                echo "core_freq=500" >> /boot/config.txt
                echo "sdram_freq=500" >> /boot/config.txt
                echo "over_voltage_sdram=2" >> /boot/config.txt
                ;;
            *)
                echo "Unknown profile: $OVERCLOCK_PROFILE. Skipping."
                ;;
        esac
    fi
fi

echo "Installation Complete. Please Reboot."
