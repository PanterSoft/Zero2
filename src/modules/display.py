import time
import subprocess
import board
import busio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
from modules.logger import get_logger

logger = get_logger(__name__)

class DisplayManager:
    def __init__(self):
        # Create the I2C interface.
        # For Raspberry Pi with CircuitPython, we need to use the correct initialization
        # Error shows valid ports: ((1, 3, 2), (0, 1, 0)) - format: (port_id, scl_pin, sda_pin)
        self.i2c = None

        # Method 1: Try using board.I2C() if available (CircuitPython 7+)
        try:
            if hasattr(board, 'I2C'):
                self.i2c = board.I2C()
                logger.info("Initialized I2C using board.I2C()")
        except (ValueError, RuntimeError, AttributeError) as e:
            logger.debug(f"board.I2C() failed: {e}")

        # Method 2: Try explicit GPIO pins (port 1: GPIO3=SCL, GPIO2=SDA)
        # Don't switch to input - let I2C driver handle pin configuration
        if self.i2c is None:
            try:
                import digitalio
                # Standard Raspberry Pi I2C pins: GPIO 3 (SCL) and GPIO 2 (SDA)
                scl = digitalio.DigitalInOut(board.GP3)
                sda = digitalio.DigitalInOut(board.GP2)
                # Try with frequency parameter (100kHz default, 400kHz is common)
                self.i2c = busio.I2C(scl, sda, frequency=100000)
                logger.info("Initialized I2C using GPIO 3 (SCL) and GPIO 2 (SDA) with frequency")
            except (ValueError, RuntimeError, AttributeError) as e:
                logger.debug(f"I2C init with GP3/GP2 (with freq) failed: {e}")

        # Method 3: Try without frequency parameter
        if self.i2c is None:
            try:
                import digitalio
                scl = digitalio.DigitalInOut(board.GP3)
                sda = digitalio.DigitalInOut(board.GP2)
                self.i2c = busio.I2C(scl, sda)
                logger.info("Initialized I2C using GPIO 3 (SCL) and GPIO 2 (SDA)")
            except (ValueError, RuntimeError, AttributeError) as e:
                logger.debug(f"I2C init with GP3/GP2 (no freq) failed: {e}")

        # Method 4: Try I2C port 0 (GPIO1=SCL, GPIO0=SDA)
        if self.i2c is None:
            try:
                import digitalio
                scl = digitalio.DigitalInOut(board.GP1)
                sda = digitalio.DigitalInOut(board.GP0)
                self.i2c = busio.I2C(scl, sda, frequency=100000)
                logger.info("Initialized I2C using GPIO 1 (SCL) and GPIO 0 (SDA)")
            except (ValueError, RuntimeError, AttributeError) as e:
                logger.debug(f"I2C init with GP1/GP0 failed: {e}")

        # Method 5: Try using board.SCL/SDA as last resort
        if self.i2c is None:
            try:
                self.i2c = busio.I2C(board.SCL, board.SDA)
                logger.info("Initialized I2C using board.SCL/SDA")
            except (ValueError, RuntimeError, AttributeError) as e:
                logger.debug(f"I2C init with board.SCL/SDA failed: {e}")

        if self.i2c is None:
            error_msg = (
                "Failed to initialize I2C after trying multiple methods. "
                "Valid I2C ports reported: ((1, 3, 2), (0, 1, 0)).\n"
                "Troubleshooting steps:\n"
                "1. Verify I2C is enabled: sudo raspi-config -> Interface Options -> I2C -> Enable\n"
                "2. Check /boot/config.txt contains: dtparam=i2c_arm=on\n"
                "3. Verify display is connected: sudo i2cdetect -y 1\n"
                "4. Reboot after enabling I2C: sudo reboot\n"
                "5. If display is not needed, set ENABLE_DISPLAY=false in config"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Create the SSD1306 OLED class.
        # The 128x64 display.
        self.disp = adafruit_ssd1306.SSD1306_I2C(128, 64, self.i2c)

        # Clear display.
        self.disp.fill(0)
        self.disp.show()

        # Create blank image for drawing.
        # Make sure to create image with mode '1' for 1-bit color.
        self.width = self.disp.width
        self.height = self.disp.height
        self.image = Image.new("1", (self.width, self.height))
        self.draw = ImageDraw.Draw(self.image)
        self.font = ImageFont.load_default()

        self.warning_message = None
        self.warning_timeout = None

    def show_warning(self, message, timeout=None):
        """
        Display a warning message on the OLED.

        Args:
            message: Warning message to display
            timeout: Optional timeout in seconds (None = until cleared)
        """
        self.warning_message = message
        self.warning_timeout = timeout
        if timeout:
            self.warning_timeout = time.time() + timeout

    def clear_warning(self):
        """Clear the warning message."""
        self.warning_message = None
        self.warning_timeout = None

    def update_info(self):
        # Draw a black filled box to clear the image.
        self.draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)

        # Check if warning should be displayed
        if self.warning_message:
            if self.warning_timeout and time.time() > self.warning_timeout:
                self.clear_warning()
            else:
                # Display warning message (split across lines if needed)
                lines = self.warning_message.split('\n')
                for i, line in enumerate(lines[:4]):  # Max 4 lines
                    y_pos = i * 16
                    if y_pos < self.height:
                        self.draw.text((0, y_pos), line[:20], font=self.font, fill=255)

                # Display image and return early
                self.disp.image(self.image)
                self.disp.show()
                return

        # Shell scripts for system monitoring from here:
        # https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
        try:
            cmd = "hostname -I | cut -d' ' -f1"
            IP = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
            cmd = "top -bn1 | grep load | awk '{printf \"CPU Load: %.2f\", $(NF-2)}'"
            CPU = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
            cmd = "free -m | awk 'NR==2{printf \"Mem: %s/%s MB\", $3,$2}'"
            MemUsage = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
        except Exception as e:
            logger.warning(f"Failed to get system info: {e}")
            IP = "N/A"
            CPU = "N/A"
            MemUsage = "N/A"

        # Write operations
        self.draw.text((0, 0), "IP: " + IP, font=self.font, fill=255)
        self.draw.text((0, 16), CPU, font=self.font, fill=255)
        self.draw.text((0, 32), MemUsage, font=self.font, fill=255)
        self.draw.text((0, 48), "Zero2 Controller", font=self.font, fill=255)

        # Display image.
        self.disp.image(self.image)
        self.disp.show()
