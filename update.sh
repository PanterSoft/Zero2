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

# Check and enable I2C if display is enabled
if [ -f "config/zero2.conf" ]; then
    ENABLE_DISPLAY=$(grep "^ENABLE_DISPLAY=" config/zero2.conf | cut -d'=' -f2 | tr -d ' ' | tr '[:upper:]' '[:lower:]')
    if [ "$ENABLE_DISPLAY" = "true" ] || [ "$ENABLE_DISPLAY" = "1" ] || [ "$ENABLE_DISPLAY" = "yes" ] || [ "$ENABLE_DISPLAY" = "on" ]; then
        echo "Checking I2C configuration..."

        # Check if I2C is enabled (handle with/without leading whitespace)
        I2C_ALREADY_ENABLED=false
        I2C_JUST_ENABLED=false

        if grep -qE "^[[:space:]]*dtparam=i2c_arm=on" /boot/config.txt; then
            I2C_ALREADY_ENABLED=true
            echo "  I2C already enabled in /boot/config.txt"
        elif grep -qE "^[[:space:]]*dtparam=i2c_arm=off" /boot/config.txt; then
            sed -i 's/^[[:space:]]*dtparam=i2c_arm=off/dtparam=i2c_arm=on/' /boot/config.txt
            I2C_JUST_ENABLED=true
            echo "  Changed dtparam=i2c_arm=off to dtparam=i2c_arm=on"
        elif grep -qE "^[[:space:]]*#.*dtparam=i2c_arm=" /boot/config.txt; then
            # I2C line is commented out (with optional whitespace before #), uncomment and enable
            # Handle both "#dtparam=i2c_arm=off" and "# dtparam=i2c_arm=off" patterns
            sed -i -E 's/^([[:space:]]*)#([[:space:]]*)dtparam=i2c_arm=.*/\1dtparam=i2c_arm=on/' /boot/config.txt
            I2C_JUST_ENABLED=true
            echo "  Uncommented and enabled I2C in /boot/config.txt"
        else
            # I2C is not enabled yet, add it
            echo "dtparam=i2c_arm=on" >> /boot/config.txt
            I2C_JUST_ENABLED=true
            echo "  Added dtparam=i2c_arm=on to /boot/config.txt"
        fi

        # Only show warnings if I2C was just enabled
        if [ "$I2C_JUST_ENABLED" = true ]; then
            # I2C was just enabled, try to load module and check
            modprobe i2c-dev 2>/dev/null || echo "  Warning: Could not load i2c-dev module"

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
echo ""
echo "Note: If I2C was just enabled, a reboot may be required: sudo reboot"