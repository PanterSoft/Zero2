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
        self.i2c = busio.I2C(board.SCL, board.SDA)

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
