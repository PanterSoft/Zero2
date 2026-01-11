import subprocess
import os
from pathlib import Path


class NetworkManagerController:
    """
    Thin wrapper to call the modular helper scripts deployed to /usr/local/bin/zero2.
    This replaces the old nmcli-based logic.
    """

    def __init__(self, scripts_dir: str = "/usr/local/bin/zero2"):
        self.scripts_dir = Path(scripts_dir)

    def _run(self, script_name: str):
        script_path = self.scripts_dir / script_name
        if not script_path.exists():
            raise FileNotFoundError(f"Helper script not found: {script_path}")
        subprocess.run([str(script_path)], check=True)

    # Hotspot controls
    def enable_hotspot(self):
        self._run("enable-hotspot.sh")

    def disable_hotspot(self):
        self._run("disable-hotspot.sh")

    # Bluetooth PAN controls
    def enable_bt_pan(self):
        self._run("enable-bt-pan.sh")

    def disable_bt_pan(self):
        self._run("disable-bt-pan.sh")

    # USB gadget controls
    def enable_usb_gadget(self):
        self._run("enable-usb-ether.sh")

    def disable_usb_gadget(self):
        self._run("disable-usb-ether.sh")

    # Repo update
    def update_repo(self):
        self._run("update-repo.sh")

