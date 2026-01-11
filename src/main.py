import time
import signal
import sys
from modules.display import DisplayManager
from modules.power import PowerManager
from modules.buttons import ButtonHandler
from modules.menu import MenuSystem
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

    # 2. Initialize Buttons (if enabled)
    config = read_config()
    buttons = None
    if config.get('ENABLE_BUTTONS', True) and config.get('ENABLE_DISPLAY', True):
        try:
            buttons = ButtonHandler()
            logger.info("Button handler initialized successfully")

            # Menu navigation callbacks
            def button_up_pressed():
                if display:
                    display.menu.navigate_up()
                    display.update_info()  # Immediate update

            def button_down_pressed():
                if display:
                    display.menu.navigate_down()
                    display.update_info()  # Immediate update

            def button_left_pressed():
                if display:
                    display.menu.navigate_left()
                    display.update_info()  # Immediate update

            def button_right_pressed():
                if display:
                    display.menu.navigate_right()
                    display.update_info()  # Immediate update

            def button_select_pressed():
                if display:
                    display.menu.select()
                    display.update_info()  # Immediate update

            def button_a_pressed():
                # Button A: Toggle menu or custom action
                if display:
                    current_menu = display.menu.get_current_menu()
                    if current_menu != MenuSystem.MENU_MAIN:
                        display.menu.go_back()
                    display.update_info()

            def button_b_pressed():
                # Button B: Custom action or back
                if display:
                    current_menu = display.menu.get_current_menu()
                    if current_menu != MenuSystem.MENU_MAIN:
                        display.menu.go_back()
                    display.update_info()

            buttons.register_callback('UP', button_up_pressed)
            buttons.register_callback('DOWN', button_down_pressed)
            buttons.register_callback('LEFT', button_left_pressed)
            buttons.register_callback('RIGHT', button_right_pressed)
            buttons.register_callback('SELECT', button_select_pressed)
            buttons.register_callback('A', button_a_pressed)
            buttons.register_callback('B', button_b_pressed)

        except Exception as e:
            logger.error(f"Failed to initialize buttons: {e}", exc_info=True)
    else:
        logger.info("Button handling disabled (ENABLE_BUTTONS=false or ENABLE_DISPLAY=false)")

    # 3. Start Power Monitor (if enabled)
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

    # 4. Main Loop
    logger.info("Entering main loop")
    display_interval = config.get('DISPLAY_UPDATE_INTERVAL', 2)
    last_display_update = 0
    button_check_interval = 0.05  # Check buttons every 50ms
    last_button_check = 0

    while True:
        try:
            current_time = time.time()

            # Check buttons frequently but independently of display updates
            if buttons and (current_time - last_button_check) >= button_check_interval:
                buttons.check_buttons()
                last_button_check = current_time

            # Update display at configured interval (independent of button checks)
            # Note: Warnings trigger immediate updates via show_warning()
            if display and (current_time - last_display_update) >= display_interval:
                display.update_info()
                last_display_update = current_time

            # Small sleep to avoid busy-waiting
            time.sleep(0.01)  # Reduced sleep for more responsive button checking

        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
            time.sleep(5)

if __name__ == "__main__":
    main()
