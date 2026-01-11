#!/bin/bash
set -e

# Update the Zero2 controller repository, helper scripts, and systemd services.

if ! command -v git >/dev/null 2>&1; then
  echo "git is required to update the repository. Install git first."; exit 1
fi

INSTALL_DIR=${INSTALL_DIR:-/opt/zero2_controller}
BRANCH=${BRANCH:-main}

if [ ! -d "$INSTALL_DIR/.git" ]; then
  echo "Repository not found at $INSTALL_DIR. Run the bootstrap script first."; exit 1
fi

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (needed to update services and scripts)"; exit 1
fi

cd "$INSTALL_DIR"

# Prevent accidental overwrites when local changes exist
if [ -n "$(git status --porcelain)" ]; then
  echo "Working tree is dirty. Commit/stash changes before updating."; exit 1
fi

echo "Updating repository at $INSTALL_DIR (branch: $BRANCH)..."
git fetch --all --prune
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

# Update helper scripts (all .sh files from scripts/ directory)
echo "Updating helper scripts..."
mkdir -p /usr/local/bin/zero2
for script in scripts/*.sh; do
    if [ -f "$script" ]; then
        install -m 755 "$script" /usr/local/bin/zero2/
        echo "  Updated: $(basename $script)"
    fi
done

# Update systemd services
echo "Updating systemd services..."
cp systemd/zero2-controller.service /etc/systemd/system/
cp systemd/bt-nap.service /etc/systemd/system/
systemctl daemon-reload
echo "  Services reloaded"

# Track if I2C was changed (for reboot hint)
I2C_CHANGED=false

# Check and enable I2C if display is enabled
if [ -f "config/zero2.conf" ]; then
    ENABLE_DISPLAY=$(grep "^ENABLE_DISPLAY=" config/zero2.conf | cut -d'=' -f2 | tr -d ' ' | tr '[:upper:]' '[:lower:]')
    if [ "$ENABLE_DISPLAY" = "true" ] || [ "$ENABLE_DISPLAY" = "1" ] || [ "$ENABLE_DISPLAY" = "yes" ] || [ "$ENABLE_DISPLAY" = "on" ]; then
        echo "Checking I2C configuration..."

        # Read I2C_MODE from config file (default to hardware)
        I2C_MODE="hardware"
        I2C_MODE_CONFIG=$(grep "^I2C_MODE=" config/zero2.conf | cut -d'=' -f2 | tr -d ' ' | tr '[:upper:]' '[:lower:]')
        if [ -n "$I2C_MODE_CONFIG" ]; then
            I2C_MODE="$I2C_MODE_CONFIG"
        fi

        I2C_ALREADY_ENABLED=false
        I2C_JUST_ENABLED=false

        if [ "$I2C_MODE" = "gpio" ]; then
            # GPIO-based I2C mode (for Raspberry Pi Zero 2W where hardware I2C doesn't work)
            echo "  Configuring GPIO-based I2C (dtoverlay=i2c-gpio)..."

            # Disable hardware I2C if present (they cannot coexist)
            if grep -qE "^[[:space:]]*dtparam=i2c_arm=" /boot/config.txt; then
                sed -i 's/^[[:space:]]*dtparam=i2c_arm=.*/#dtparam=i2c_arm=off  # Disabled: using GPIO I2C instead/' /boot/config.txt
                echo "  Disabled hardware I2C (dtparam=i2c_arm) - GPIO I2C will be used instead"
                I2C_JUST_ENABLED=true
                I2C_CHANGED=true
            fi

            # Check if GPIO I2C overlay is already enabled
            if grep -qE "^[[:space:]]*dtoverlay=i2c-gpio" /boot/config.txt; then
                I2C_ALREADY_ENABLED=true
                echo "  GPIO I2C overlay already enabled in /boot/config.txt"
            else
                # Add GPIO I2C overlay: dtoverlay=i2c-gpio,i2c_gpio_sda=3,i2c_gpio_scl=5,bus=1
                echo "dtoverlay=i2c-gpio,i2c_gpio_sda=3,i2c_gpio_scl=5,bus=1" >> /boot/config.txt
                I2C_JUST_ENABLED=true
                I2C_CHANGED=true
                echo "  Added GPIO I2C overlay to /boot/config.txt"
            fi
        else
            # Hardware I2C mode (default)
            echo "  Configuring hardware I2C (dtparam=i2c_arm=on)..."

            # Disable GPIO I2C overlay if present (they cannot coexist)
            if grep -qE "^[[:space:]]*dtoverlay=i2c-gpio" /boot/config.txt; then
                sed -i 's/^[[:space:]]*dtoverlay=i2c-gpio.*/#dtoverlay=i2c-gpio  # Disabled: using hardware I2C instead/' /boot/config.txt
                echo "  Disabled GPIO I2C overlay - hardware I2C will be used instead"
                I2C_JUST_ENABLED=true
                I2C_CHANGED=true
            fi

            # Method 1: Use DietPi's internal hardware configuration tool (preferred for DietPi)
            if [ -f "/boot/dietpi/func/dietpi-set_hardware" ]; then
                echo "  Using DietPi's dietpi-set_hardware tool..."
                # Check if I2C is already enabled by checking config.txt
                if grep -qE "^[[:space:]]*dtparam=i2c_arm=on" /boot/config.txt; then
                    I2C_ALREADY_ENABLED=true
                    echo "  I2C already enabled in /boot/config.txt"
                else
                    # Use DietPi's tool to enable I2C
                    if /boot/dietpi/func/dietpi-set_hardware i2c enable >/dev/null 2>&1; then
                        I2C_JUST_ENABLED=true
                        I2C_CHANGED=true
                        echo "  Enabled I2C via dietpi-set_hardware"
                    else
                        echo "  dietpi-set_hardware failed, using direct config.txt method"
                    fi
                fi
            fi

            # Method 2: Direct /boot/config.txt modification (fallback or if DietPi tool not available)
            if [ "$I2C_ALREADY_ENABLED" = false ] && [ "$I2C_JUST_ENABLED" = false ]; then
                if grep -qE "^[[:space:]]*dtparam=i2c_arm=on" /boot/config.txt; then
                    I2C_ALREADY_ENABLED=true
                    echo "  I2C already enabled in /boot/config.txt"
                elif grep -qE "^[[:space:]]*dtparam=i2c_arm=off" /boot/config.txt; then
                    sed -i 's/^[[:space:]]*dtparam=i2c_arm=off/dtparam=i2c_arm=on/' /boot/config.txt
                    I2C_JUST_ENABLED=true
                    I2C_CHANGED=true
                    echo "  Changed dtparam=i2c_arm=off to dtparam=i2c_arm=on"
                elif grep -qE "^[[:space:]]*#.*dtparam=i2c_arm=" /boot/config.txt; then
                    # I2C line is commented out (with optional whitespace before #), uncomment and enable
                    # Handle both "#dtparam=i2c_arm=off" and "# dtparam=i2c_arm=off" patterns
                    sed -i -E 's/^([[:space:]]*)#([[:space:]]*)dtparam=i2c_arm=.*/\1dtparam=i2c_arm=on/' /boot/config.txt
                    I2C_JUST_ENABLED=true
                    I2C_CHANGED=true
                    echo "  Uncommented and enabled I2C in /boot/config.txt"
                else
                    # I2C is not enabled yet, add it
                    echo "dtparam=i2c_arm=on" >> /boot/config.txt
                    I2C_JUST_ENABLED=true
                    I2C_CHANGED=true
                    echo "  Added dtparam=i2c_arm=on to /boot/config.txt"
                fi
            fi
        fi

        # Install I2C tools and Python libraries only if:
        # 1. I2C was just enabled/changed, OR
        # 2. Packages are missing (even if I2C already enabled)
        if [ "$I2C_JUST_ENABLED" = true ]; then
            echo "  Installing I2C tools and Python libraries (I2C was just enabled)..."
            I2C_PACKAGES_TO_INSTALL=()

            # Check for i2c-tools using dpkg-query (more reliable)
            if ! dpkg-query -W -f='${Status}' i2c-tools 2>/dev/null | grep -q "install ok installed"; then
                I2C_PACKAGES_TO_INSTALL+=("i2c-tools")
            fi

            # Check for python3-smbus using dpkg-query (more reliable)
            if ! dpkg-query -W -f='${Status}' python3-smbus 2>/dev/null | grep -q "install ok installed"; then
                I2C_PACKAGES_TO_INSTALL+=("python3-smbus")
            fi

            if [ ${#I2C_PACKAGES_TO_INSTALL[@]} -gt 0 ]; then
                apt-get update -qq
                apt-get install -y "${I2C_PACKAGES_TO_INSTALL[@]}"
                echo "  Installed: ${I2C_PACKAGES_TO_INSTALL[*]}"
            else
                echo "  I2C tools already installed"
            fi
        elif [ "$I2C_ALREADY_ENABLED" = true ]; then
            # I2C already enabled - silently check if packages are missing
            # Only install if actually missing (no message if already installed)
            I2C_PACKAGES_TO_INSTALL=()

            # Check for i2c-tools using dpkg-query (more reliable)
            if ! dpkg-query -W -f='${Status}' i2c-tools 2>/dev/null | grep -q "install ok installed"; then
                I2C_PACKAGES_TO_INSTALL+=("i2c-tools")
            fi

            # Check for python3-smbus using dpkg-query (more reliable)
            if ! dpkg-query -W -f='${Status}' python3-smbus 2>/dev/null | grep -q "install ok installed"; then
                I2C_PACKAGES_TO_INSTALL+=("python3-smbus")
            fi

            # Only install and show message if packages are actually missing
            if [ ${#I2C_PACKAGES_TO_INSTALL[@]} -gt 0 ]; then
                echo "  Installing missing I2C tools and Python libraries..."
                apt-get update -qq
                apt-get install -y "${I2C_PACKAGES_TO_INSTALL[@]}"
                echo "  Installed: ${I2C_PACKAGES_TO_INSTALL[*]}"
            fi
            # No message if packages are already installed (silent success)
        fi

        # Ensure i2c-dev module is loaded at boot (required for I2C to work)
        if [ "$I2C_JUST_ENABLED" = true ] || [ "$I2C_ALREADY_ENABLED" = true ]; then
            if ! grep -q "^i2c-dev" /etc/modules 2>/dev/null; then
                echo "i2c-dev" >> /etc/modules
                echo "  Added i2c-dev to /etc/modules"
            fi

            # Try to load the module immediately (may require reboot to take full effect)
            modprobe i2c-dev 2>/dev/null || echo "  Note: i2c-dev module will be loaded on next reboot"
        fi

        # Only show warnings if I2C was just enabled
        if [ "$I2C_JUST_ENABLED" = true ]; then
            # Verify I2C is accessible
            if [ -e /dev/i2c-1 ] || [ -e /dev/i2c-0 ]; then
                echo "  I2C device files found - I2C should be working"
            else
                echo "  Warning: I2C device files not found. A reboot may be required."
            fi
        elif [ "$I2C_ALREADY_ENABLED" = true ]; then
            # I2C was already enabled, silently verify it's working (no warnings)
            if [ -e /dev/i2c-1 ] || [ -e /dev/i2c-0 ]; then
                echo "  I2C device files found - I2C is working"
            fi
        fi
    fi
fi

echo ""
echo "Update complete!"
echo "To enable newly updated services:"
echo "  sudo systemctl enable zero2-controller.service"
echo "  sudo systemctl enable bt-nap.service"
echo "  sudo systemctl restart zero2-controller.service"

# Only show reboot hint if I2C was actually changed
if [ "$I2C_CHANGED" = true ]; then
    echo ""
    echo "Note: I2C was just enabled ($I2C_MODE mode). A reboot may be required: sudo shutdown -r now  (or sudo reboot)"
fi