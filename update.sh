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

echo ""
echo "Update complete!"
echo "To enable newly updated services:"
echo "  sudo systemctl enable zero2-controller.service"
echo "  sudo systemctl enable bt-nap.service"
echo "  sudo systemctl restart zero2-controller.service"
