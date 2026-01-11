import time
import subprocess
import os

class NetworkManagerController:
    def __init__(self, check_interval=60):
        self.check_interval = check_interval
        self.ap_mode = False

    def check_connection(self):
        # Check if connected to any wifi
        try:
            output = subprocess.check_output("nmcli -t -f TYPE,STATE connection show --active", shell=True).decode()
            if "802-11-wireless:activated" in output:
                return True
        except:
            pass
        return False

    def create_hotspot_profile(self):
        # Check if Hotspot profile exists
        try:
            subprocess.check_output("nmcli connection show Hotspot", shell=True)
        except subprocess.CalledProcessError:
            print("Creating Hotspot profile...")
            # Create Hotspot
            cmd = "nmcli con add type wifi ifname wlan0 con-name Hotspot autoconnect no ssid Zero2-Setup"
            subprocess.run(cmd, shell=True)
            subprocess.run("nmcli con modify Hotspot 802-11-wireless.mode ap 802-11-wireless.band bg ipv4.method shared", shell=True)
            subprocess.run("nmcli con modify Hotspot wifi-sec.key-mgmt wpa-psk wifi-sec.psk zero2setup", shell=True)

    def start_hotspot(self):
        print("Starting Hotspot...")
        subprocess.run("nmcli connection up Hotspot", shell=True)
        self.ap_mode = True

    def manage(self):
        self.create_hotspot_profile()

        # Give system time to connect on boot
        print("Waiting for network connection...")
        time.sleep(20) # wait for NM to try auto-connect

        if not self.check_connection():
            print("No WiFi connection found. Switching to Hotspot mode.")
            self.start_hotspot()
        else:
            print("WiFi Connected.")

