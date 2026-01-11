import time
import subprocess
import board
import busio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306

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

    def update_info(self):
        # Draw a black filled box to clear the image.
        self.draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)

        # Shell scripts for system monitoring from here:
        # https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
        cmd = "hostname -I | cut -d' ' -f1"
        IP = subprocess.check_output(cmd, shell=True).decode("utf-8")
        cmd = "top -bn1 | grep load | awk '{printf \"CPU Load: %.2f\", $(NF-2)}'"
        CPU = subprocess.check_output(cmd, shell=True).decode("utf-8")
        cmd = "free -m | awk 'NR==2{printf \"Mem: %s/%s MB\", $3,$2}'"
        MemUsage = subprocess.check_output(cmd, shell=True).decode("utf-8")

        # Write operations
        self.draw.text((0, 0), "IP: " + IP, font=self.font, fill=255)
        self.draw.text((0, 16), CPU, font=self.font, fill=255)
        self.draw.text((0, 32), MemUsage, font=self.font, fill=255)
        self.draw.text((0, 48), "Zero2 Controller", font=self.font, fill=255)

        # Display image.
        self.disp.image(self.image)
        self.disp.show()
