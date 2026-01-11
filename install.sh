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

# Check which packages need to be installed
PACKAGES_TO_INSTALL=()
for pkg in python3-pip python3-venv python3-dev build-essential libdbus-1-dev libglib2.0-dev bluez bluez-tools hostapd dnsmasq i2c-tools libopenjp2-7 libtiff6; do
    if ! dpkg -l | grep -q "^ii  $pkg"; then
        PACKAGES_TO_INSTALL+=("$pkg")
    fi
done

if [ ${#PACKAGES_TO_INSTALL[@]} -gt 0 ]; then
    echo "Installing missing packages: ${PACKAGES_TO_INSTALL[*]}"
    echo "Running apt-get update..."
    apt-get update
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

# 4. Install helper scripts (all .sh files from scripts/ directory)
echo "Installing helper scripts..."
mkdir -p /usr/local/bin/zero2
for script in scripts/*.sh; do
    if [ -f "$script" ]; then
        install -m 755 "$script" /usr/local/bin/zero2/
        echo "  Installed: $(basename $script)"
    fi
done

# 5. Setup Python Environment
echo "Setting up Python Environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

./venv/bin/pip install -r requirements.txt

# 6. Enable I2C for Display
if [ "$ENABLE_DISPLAY" = true ]; then
    echo "Enabling I2C for display support..."

    # Check if I2C is already enabled (handle with/without leading whitespace)
    I2C_ENABLED=false
    if grep -qE "^[[:space:]]*dtparam=i2c_arm=on" /boot/config.txt; then
        I2C_ENABLED=true
        echo "  I2C already enabled in /boot/config.txt"
    elif grep -qE "^[[:space:]]*dtparam=i2c_arm=off" /boot/config.txt; then
        # I2C is explicitly disabled, change it to on
        sed -i 's/^[[:space:]]*dtparam=i2c_arm=off/dtparam=i2c_arm=on/' /boot/config.txt
        I2C_ENABLED=true
        echo "  Changed dtparam=i2c_arm=off to dtparam=i2c_arm=on"
    elif grep -qE "^[[:space:]]*#.*dtparam=i2c_arm=" /boot/config.txt; then
        # I2C line is commented out (with optional whitespace before #), uncomment and enable
        # Handle both "#dtparam=i2c_arm=off" and "# dtparam=i2c_arm=off" patterns
        sed -i -E 's/^([[:space:]]*)#([[:space:]]*)dtparam=i2c_arm=.*/\1dtparam=i2c_arm=on/' /boot/config.txt
        I2C_ENABLED=true
        echo "  Uncommented and enabled I2C in /boot/config.txt"
    fi

    # If I2C is not enabled yet, add it
    if [ "$I2C_ENABLED" = false ]; then
        echo "dtparam=i2c_arm=on" >> /boot/config.txt
        echo "  Added dtparam=i2c_arm=on to /boot/config.txt"
    fi

    # Load I2C kernel module (works immediately, reboot needed for permanent)
    modprobe i2c-dev 2>/dev/null || echo "  Warning: Could not load i2c-dev module (may need reboot)"

    # Verify I2C is accessible
    if [ -e /dev/i2c-1 ] || [ -e /dev/i2c-0 ]; then
        echo "  I2C device files found - I2C should be working"
    else
        echo "  Warning: I2C device files not found. A reboot may be required."
    fi

    echo "  Note: If I2C was just enabled, a reboot is required for changes to take effect"
fi

# Optimize GPU Memory for Headless (Maximize RAM)
if ! grep -q "gpu_mem=" /boot/config.txt; then
    echo "Setting gpu_mem=16 for headless performance"
    echo "gpu_mem=16" >> /boot/config.txt
fi

# 6.5. Create Centralized Config File
echo "Creating centralized configuration file..."
mkdir -p "$INSTALL_DIR/config"

# Use default config file from repo if it exists, otherwise try example, otherwise create inline
if [ -f "config/zero2.conf" ]; then
    echo "Copying default config file from repository..."
    cp config/zero2.conf "$INSTALL_DIR/config/zero2.conf"

    # Update feature flags from installation variables
    sed -i "s/^ENABLE_LOW_BAT=.*/ENABLE_LOW_BAT=$ENABLE_LOW_BAT/" "$INSTALL_DIR/config/zero2.conf"
    sed -i "s/^ENABLE_DISPLAY=.*/ENABLE_DISPLAY=$ENABLE_DISPLAY/" "$INSTALL_DIR/config/zero2.conf"
    sed -i "s/^ENABLE_SSH_BT=.*/ENABLE_SSH_BT=$ENABLE_SSH_BT/" "$INSTALL_DIR/config/zero2.conf"
    sed -i "s/^ENABLE_USB_OTG=.*/ENABLE_USB_OTG=$ENABLE_USB_OTG/" "$INSTALL_DIR/config/zero2.conf"
    sed -i "s/^ENABLE_WIFI_HOTSPOT=.*/ENABLE_WIFI_HOTSPOT=$ENABLE_WIFI_HOTSPOT/" "$INSTALL_DIR/config/zero2.conf"
elif [ -f "config/zero2.conf.example" ]; then
    echo "Copying config example from repository..."
    cp config/zero2.conf.example "$INSTALL_DIR/config/zero2.conf"

    # Update feature flags from installation variables
    sed -i "s/^ENABLE_LOW_BAT=.*/ENABLE_LOW_BAT=$ENABLE_LOW_BAT/" "$INSTALL_DIR/config/zero2.conf"
    sed -i "s/^ENABLE_DISPLAY=.*/ENABLE_DISPLAY=$ENABLE_DISPLAY/" "$INSTALL_DIR/config/zero2.conf"
    sed -i "s/^ENABLE_SSH_BT=.*/ENABLE_SSH_BT=$ENABLE_SSH_BT/" "$INSTALL_DIR/config/zero2.conf"
    sed -i "s/^ENABLE_USB_OTG=.*/ENABLE_USB_OTG=$ENABLE_USB_OTG/" "$INSTALL_DIR/config/zero2.conf"
    sed -i "s/^ENABLE_WIFI_HOTSPOT=.*/ENABLE_WIFI_HOTSPOT=$ENABLE_WIFI_HOTSPOT/" "$INSTALL_DIR/config/zero2.conf"
else
    # Fallback: create config file inline if neither exists
    echo "Creating config file inline (no template found)..."
    cat > "$INSTALL_DIR/config/zero2.conf" <<EOF
# Zero2 Controller Configuration File
# This file contains all configuration options for the Zero2 Controller system
# Edit this file and restart the service to apply changes

# ==============================================================================
# Feature Flags
# ==============================================================================
ENABLE_LOW_BAT=$ENABLE_LOW_BAT
ENABLE_DISPLAY=$ENABLE_DISPLAY
ENABLE_SSH_BT=$ENABLE_SSH_BT
ENABLE_USB_OTG=$ENABLE_USB_OTG
ENABLE_WIFI_HOTSPOT=$ENABLE_WIFI_HOTSPOT

# ==============================================================================
# Power Management Settings
# ==============================================================================
POWER_GPIO_PIN=25
POWER_THRESHOLD=30
POWER_WARNING_TIME=30
POWER_NOTIFY_TERMINALS=true

# ==============================================================================
# Display Settings
# ==============================================================================
DISPLAY_UPDATE_INTERVAL=2

# ==============================================================================
# Network Settings
# ==============================================================================
BT_IP=10.10.10.1
USB_IP=10.10.20.1

# ==============================================================================
# Logging Settings
# ==============================================================================
LOG_LEVEL=INFO
LOG_FILE=/var/log/zero2-controller.log
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=5
EOF
fi

chmod 644 "$INSTALL_DIR/config/zero2.conf"

# Keep old config file for backward compatibility (if it exists)
if [ -f "$INSTALL_DIR/config/enabled_features.conf" ]; then
    echo "Note: Old config file enabled_features.conf exists but zero2.conf takes precedence"
fi

# 6.6. Setup Log Directory
echo "Setting up log directory..."
mkdir -p /var/log
touch /var/log/zero2-controller.log
chmod 644 /var/log/zero2-controller.log

# 7. Install Systemd Services
echo "Installing Systemd Services..."
cp systemd/zero2-controller.service /etc/systemd/system/
if [ "$ENABLE_SSH_BT" = true ]; then
    cp systemd/bt-nap.service /etc/systemd/system/
    #systemctl enable bt-nap.service
fi

systemctl daemon-reload
#systemctl enable zero2-controller.service

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
