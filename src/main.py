import time
import signal
import sys
from modules.display import DisplayManager
from modules.power import PowerManager
from modules.network import NetworkManagerController

def signal_handler(sig, frame):
    print("Exiting...")
    # cleanup if needed
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)

    print("Zero2 Controller Starting...")

    # 1. Initialize Display
    display = None
    try:
        display = DisplayManager()
        print("Display Initialized")
    except Exception as e:
        print(f"Failed to init display: {e}")

    # 2. Start Power Monitor
    power = PowerManager()
    power.start_monitoring()

    # 3. Network Management (Single pass check on boot)
    network = NetworkManagerController()
    try:
        network.manage()
    except Exception as e:
        print(f"Network management error: {e}")

    # 4. Main Loop
    while True:
        try:
            if display:
                display.update_info()
            time.sleep(2)
        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
