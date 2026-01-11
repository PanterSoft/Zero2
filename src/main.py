import time
import signal
import sys
from modules.display import DisplayManager
from modules.power import PowerManager
from modules.config import read_config, get_config
from modules.logger import setup_logger

logger = setup_logger()

def signal_handler(sig, frame):
    logger.info("Received shutdown signal. Exiting...")
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Zero2 Controller Starting...")

    # 1. Initialize Display
    display = None
    try:
        display = DisplayManager()
        logger.info("Display initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize display: {e}", exc_info=True)

    # 2. Start Power Monitor (if enabled)
    config = read_config()
    power = None
    if config.get('ENABLE_LOW_BAT', True):
        try:
            power = PowerManager(display_manager=display)
            power.start_monitoring()
            logger.info(f"Power monitoring enabled (GPIO {power.pin}, threshold: {power.threshold}s)")
        except Exception as e:
            logger.error(f"Failed to initialize power monitoring: {e}", exc_info=True)
    else:
        logger.info("Power monitoring disabled (ENABLE_LOW_BAT=false)")

    # 3. Main Loop
    logger.info("Entering main loop")
    while True:
        try:
            if display:
                display.update_info()
            time.sleep(2)
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
            time.sleep(5)

if __name__ == "__main__":
    main()
