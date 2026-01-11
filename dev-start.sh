#!/bin/bash
# Development start script for Zero2 Controller
# This script runs the controller directly without systemd for development/testing

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Zero2 Controller - Development Mode"
echo "===================================="
echo ""

# Check if running as root (needed for GPIO access)
if [ "$EUID" -ne 0 ]; then
    echo "Warning: Not running as root. GPIO access may fail."
    echo "For full functionality, run with: sudo ./dev-start.sh"
    echo ""
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating..."
    python3 -m venv venv
    echo "Installing dependencies..."
    ./venv/bin/pip install -r requirements.txt
    echo ""
fi

# Check if config directory exists
if [ ! -d "config" ]; then
    echo "Config directory not found. Creating from default..."
    mkdir -p config
    if [ -f "config/zero2.conf" ]; then
        echo "Using existing config/zero2.conf"
    else
        echo "Creating default config..."
        cat > config/zero2.conf <<EOF
# Zero2 Controller Configuration File (Development)
# This is a local development config file

ENABLE_LOW_BAT=false
ENABLE_DISPLAY=true
ENABLE_SSH_BT=true
ENABLE_USB_OTG=true
ENABLE_WIFI_HOTSPOT=false

POWER_GPIO_PIN=25
POWER_THRESHOLD=30
POWER_WARNING_TIME=30
POWER_NOTIFY_TERMINALS=true

DISPLAY_UPDATE_INTERVAL=2

BT_IP=10.10.10.1
USB_IP=10.10.20.1

LOG_LEVEL=DEBUG
LOG_FILE=/var/log/zero2-controller.log
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=5
EOF
        echo "Created config/zero2.conf"
    fi
    echo ""
fi

# Set working directory for Python
export ZERO2_WORKING_DIR="$SCRIPT_DIR"

# Check if local config exists
if [ -f "config/zero2.conf" ]; then
    echo "Using local development config: config/zero2.conf"
    echo "  (Set ZERO2_USE_SYSTEM_CONFIG=1 to use system config instead)"
else
    echo "No local config found. Using system config: /opt/zero2_controller/config/zero2.conf"
    echo "  (Create config/zero2.conf for local development)"
fi

echo ""
echo "Starting Zero2 Controller..."
echo "Press Ctrl+C to stop"
echo ""

# Change to src directory and run
cd src
exec "$SCRIPT_DIR/venv/bin/python3" main.py "$@"
