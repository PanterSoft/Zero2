import time
import board
import digitalio
from modules.logger import get_logger
from modules.config import get_config

logger = get_logger(__name__)

class ButtonHandler:
    """
    Handle button inputs from Adafruit 128x64 OLED Bonnet.

    Buttons:
    - Button A: GPIO 5
    - Button B: GPIO 6
    - D-pad Up: GPIO 23
    - D-pad Down: GPIO 17
    - D-pad Left: GPIO 22
    - D-pad Right: GPIO 27
    - D-pad Select/Center: GPIO 4
    """

    # GPIO pin mappings for Adafruit 128x64 OLED Bonnet
    BUTTON_A_PIN = 5
    BUTTON_B_PIN = 6
    DPAD_UP_PIN = 23
    DPAD_DOWN_PIN = 17
    DPAD_LEFT_PIN = 22
    DPAD_RIGHT_PIN = 27
    DPAD_SELECT_PIN = 4

    def __init__(self):
        self.buttons = {}
        self.button_callbacks = {}
        self.last_press_time = {}
        self.debounce_time = 0.1  # 100ms debounce

        # Initialize all buttons
        try:
            self._init_button('A', self.BUTTON_A_PIN)
            self._init_button('B', self.BUTTON_B_PIN)
            self._init_button('UP', self.DPAD_UP_PIN)
            self._init_button('DOWN', self.DPAD_DOWN_PIN)
            self._init_button('LEFT', self.DPAD_LEFT_PIN)
            self._init_button('RIGHT', self.DPAD_RIGHT_PIN)
            self._init_button('SELECT', self.DPAD_SELECT_PIN)
            logger.info("Button handler initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize buttons: {e}", exc_info=True)
            raise

    def _init_button(self, name, pin_number):
        """Initialize a button GPIO pin."""
        try:
            # Get GPIO pin from board module
            pin = getattr(board, f'GP{pin_number}')
            button = digitalio.DigitalInOut(pin)
            button.direction = digitalio.Direction.INPUT
            button.pull = digitalio.Pull.UP  # Buttons are active LOW (pulled up)
            self.buttons[name] = button
            self.last_press_time[name] = 0
        except AttributeError:
            # Fallback: try direct pin number if board.GP* doesn't exist
            try:
                import RPi.GPIO as GPIO
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(pin_number, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                self.buttons[name] = {'pin': pin_number, 'type': 'RPi'}
                self.last_press_time[name] = 0
            except Exception as e:
                logger.warning(f"Could not initialize button {name} on GPIO {pin_number}: {e}")
                self.buttons[name] = None

    def register_callback(self, button_name, callback):
        """
        Register a callback function for a button press.

        Args:
            button_name: Name of button ('A', 'B', 'UP', 'DOWN', 'LEFT', 'RIGHT', 'SELECT')
            callback: Function to call when button is pressed (no arguments)
        """
        if button_name in self.buttons:
            self.button_callbacks[button_name] = callback
            logger.debug(f"Registered callback for button {button_name}")
        else:
            logger.warning(f"Unknown button name: {button_name}")

    def is_pressed(self, button_name):
        """
        Check if a button is currently pressed.

        Args:
            button_name: Name of button ('A', 'B', 'UP', 'DOWN', 'LEFT', 'RIGHT', 'SELECT')

        Returns:
            bool: True if button is pressed, False otherwise
        """
        if button_name not in self.buttons or self.buttons[button_name] is None:
            return False

        button = self.buttons[button_name]

        try:
            if isinstance(button, dict) and button.get('type') == 'RPi':
                # RPi.GPIO method
                import RPi.GPIO as GPIO
                return not GPIO.input(button['pin'])  # Active LOW
            else:
                # CircuitPython digitalio method
                return not button.value  # Active LOW (pulled up, so False when pressed)
        except Exception as e:
            logger.debug(f"Error reading button {button_name}: {e}")
            return False

    def check_buttons(self):
        """
        Check all buttons and trigger callbacks if pressed.
        This should be called periodically in the main loop.
        """
        current_time = time.time()

        for button_name, button in self.buttons.items():
            if button is None:
                continue

            if self.is_pressed(button_name):
                # Debounce: only trigger if enough time has passed since last press
                if current_time - self.last_press_time[button_name] > self.debounce_time:
                    self.last_press_time[button_name] = current_time

                    # Trigger callback if registered
                    if button_name in self.button_callbacks:
                        try:
                            self.button_callbacks[button_name]()
                            logger.debug(f"Button {button_name} pressed - callback triggered")
                        except Exception as e:
                            logger.error(f"Error in button {button_name} callback: {e}", exc_info=True)
                    else:
                        logger.debug(f"Button {button_name} pressed - no callback registered")

    def cleanup(self):
        """Clean up GPIO resources."""
        try:
            for button_name, button in self.buttons.items():
                if button is not None and not isinstance(button, dict):
                    button.deinit()
            logger.info("Button handler cleaned up")
        except Exception as e:
            logger.warning(f"Error cleaning up buttons: {e}")
