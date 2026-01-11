#!/bin/bash
set -e

# ==============================================================================
# ZERO2 BOOTSTRAP CONFIGURATION
# ==============================================================================

# Feature Flags (Exported to install.sh)
export ENABLE_SSH_BT=true        # Enable SSH via Bluetooth (PAN/NAP)
export ENABLE_USB_OTG=true       # Enable SSH/ethernet via USB OTG (g_ether)
export ENABLE_WIFI_HOTSPOT=true  # Enable Auto-Hotspot fallback
export ENABLE_DISPLAY=true       # Enable Adafruit Bonnet 128x64 Setup
export ENABLE_LOW_BAT=false       # Enable Low Battery Shutdown
export OVERCLOCK_PROFILE="modest"  # Overclocking Profile: "none", "modest", "high"


# Repository Configuration
INSTALL_DIR="/opt/zero2_controller"
REPO_URL="https://github.com/PanterSoft/Zero2.git"
BRANCH="main"

# ==============================================================================

echo "Starting Zero2 Bootstrap..."

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

if ! dpkg -l | grep -q "^ii  git[[:space:]]"; then
    echo "Installing git..."
    apt-get install -y git
else
    echo "Git is already installed."
fi

# 2. Clone or Update Repository
echo "Fetching Repository..."
if [ -d "$INSTALL_DIR" ]; then
    echo "Updating existing installation at $INSTALL_DIR..."
    cd "$INSTALL_DIR"
    git pull
else
    echo "Cloning repository to $INSTALL_DIR..."
    git clone -b "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# 3. Run Installer
echo "Running Installer..."
chmod +x install.sh
./install.sh

echo "Bootstrap Complete."
