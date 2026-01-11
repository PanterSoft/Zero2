#!/bin/bash
set -e

# Update the Zero2 controller repository to the latest version on the main branch.

if ! command -v git >/dev/null 2>&1; then
  echo "git is required to update the repository. Install git first."; exit 1
fi

INSTALL_DIR=${INSTALL_DIR:-/opt/zero2_controller}
BRANCH=${BRANCH:-main}

if [ ! -d "$INSTALL_DIR/.git" ]; then
  echo "Repository not found at $INSTALL_DIR. Run the bootstrap script first."; exit 1
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

echo "Update complete."
