import time
import signal
import sys
import atexit
from modules.display import DisplayManager
from modules.power import PowerManager
from modules.buttons import ButtonHandler
from modules.menu import MenuSystem
from modules.config import read_config, get_config
from modules.logger import setup_logger

logger = setup_logger()

# Global display reference for cleanup
_display_instance = None
_buttons_instance = None
_power_instance = None

def cleanup_resources():
    """Clean up all resources on exit."""
    global _display_instance, _buttons_instance, _power_instance

    logger.info("Cleaning up resources...")

    if _display_instance:
        try:
            _display_instance.cleanup()
        except Exception as e:
            logger.error(f"Error cleaning up display: {e}", exc_info=True)

    if _buttons_instance:
        try:
            _buttons_instance.cleanup()
        except Exception as e:
            logger.error(f"Error cleaning up buttons: {e}", exc_info=True)

    if _power_instance:
        try:
            _power_instance.stop_monitoring()
        except Exception as e:
            logger.error(f"Error stopping power monitoring: {e}", exc_info=True)

    logger.info("Cleanup complete")

def signal_handler(sig, frame):
    logger.info("Received shutdown signal. Exiting...")
    cleanup_resources()
    sys.exit(0)

# Register cleanup function to be called on normal exit
atexit.register(cleanup_resources)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Zero2 Controller Starting...")

    # 1. Initialize Display
    global _display_instance
    display = None
    try:
        display = DisplayManager()
        _display_instance = display  # Store for cleanup
        logger.info("Display initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize display: {e}", exc_info=True)

    # 2. Initialize Buttons (if enabled)
    global _buttons_instance
    config = read_config()
    buttons = None
    # Initialize buttons if enabled (buttons can work even if display failed)
    if config.get('ENABLE_BUTTONS', True):
        try:
            buttons = ButtonHandler()
            _buttons_instance = buttons  # Store for cleanup
            logger.info("Button handler initialized successfully")

            # Menu navigation callbacks
            def button_up_pressed():
                if display:
                    try:
                        display.menu.navigate_up()
                        display.update_info()  # Immediate update
                    except Exception as e:
                        logger.error(f"Error in UP button: {e}", exc_info=True)

            def button_down_pressed():
                if display:
                    try:
                        display.menu.navigate_down()
                        display.update_info()  # Immediate update
                    except Exception as e:
                        logger.error(f"Error in DOWN button: {e}", exc_info=True)

            def button_left_pressed():
                if display:
                    try:
                        display.menu.navigate_left()
                        display.update_info()  # Immediate update
                    except Exception as e:
                        logger.error(f"Error in LEFT button: {e}", exc_info=True)

            def button_right_pressed():
                if display:
                    try:
                        display.menu.navigate_right()
                        display.update_info()  # Immediate update
                    except Exception as e:
                        logger.error(f"Error in RIGHT button: {e}", exc_info=True)

            def button_select_pressed():
                if display:
                    try:
                        display.menu.select()
                        display.update_info()  # Immediate update
                    except Exception as e:
                        logger.error(f"Error in SELECT button: {e}", exc_info=True)

            def button_a_pressed():
                if display:
                    try:
                        current_menu = display.menu.get_current_menu()
                        if current_menu != MenuSystem.MENU_MAIN:
                            display.menu.go_back()
                        display.update_info()
                    except Exception as e:
                        logger.error(f"Error in A button: {e}", exc_info=True)

            def button_b_pressed():
                if display:
                    try:
                        current_menu = display.menu.get_current_menu()
                        if current_menu != MenuSystem.MENU_MAIN:
                            display.menu.go_back()
                        display.update_info()
                    except Exception as e:
                        logger.error(f"Error in B button: {e}", exc_info=True)

            buttons.register_callback('UP', button_up_pressed)
            buttons.register_callback('DOWN', button_down_pressed)
            buttons.register_callback('LEFT', button_left_pressed)
            buttons.register_callback('RIGHT', button_right_pressed)
            buttons.register_callback('SELECT', button_select_pressed)
            buttons.register_callback('A', button_a_pressed)
            buttons.register_callback('B', button_b_pressed)

            logger.info("All button callbacks registered successfully")
            if not display:
                logger.warning("Display not initialized - menu navigation will not work until display is available")

        except Exception as e:
            logger.error(f"Failed to initialize buttons: {e}", exc_info=True)
    else:
        logger.info("Button handling disabled (ENABLE_BUTTONS=false)")

    # 3. Start Power Monitor (if enabled)
    global _power_instance
    power = None
    if config.get('ENABLE_LOW_BAT', True):
        try:
            power = PowerManager(display_manager=display)
            _power_instance = power  # Store for cleanup
            power.start_monitoring()
            logger.info(f"Power monitoring enabled (GPIO {power.pin}, threshold: {power.threshold}s)")
        except Exception as e:
            logger.error(f"Failed to initialize power monitoring: {e}", exc_info=True)
    else:
        logger.info("Power monitoring disabled (ENABLE_LOW_BAT=false)")

    # 4. Main Loop
    logger.info("Entering main loop")
    display_interval = config.get('DISPLAY_UPDATE_INTERVAL', 2)
    last_display_update = 0
    button_check_interval = 0.01  # Check buttons every 10ms for faster response
    last_button_check = 0

    while True:
        try:
            current_time = time.time()

            # Check buttons very frequently for immediate response
            if buttons and (current_time - last_button_check) >= button_check_interval:
                buttons.check_buttons()
                last_button_check = current_time

            # Update display at configured interval (independent of button checks)
            # Note: Button callbacks trigger immediate updates via update_info()
            if display and (current_time - last_display_update) >= display_interval:
                display.update_info()
                last_display_update = current_time

            # Very small sleep to avoid busy-waiting while maintaining responsiveness
            time.sleep(0.005)  # 5ms sleep for very responsive button checking

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received. Exiting...")
            cleanup_resources()
            sys.exit(0)
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
            time.sleep(5)

if __name__ == "__main__":
    main()
