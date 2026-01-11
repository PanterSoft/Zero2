import time
import subprocess
import board
import busio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
from modules.logger import get_logger
from modules.config import get_config, read_config

logger = get_logger(__name__)

class DisplayManager:
    def __init__(self):
        # Create the I2C interface.
        # For Raspberry Pi with CircuitPython, we need to use the correct initialization
        # Error shows valid ports: ((1, 3, 2), (0, 1, 0)) - format: (port_id, scl_pin, sda_pin)
        self.i2c = None

        # Read I2C mode from config (hardware or gpio)
        i2c_mode = get_config('I2C_MODE', 'hardware').lower()

        if i2c_mode == 'gpio':
            # GPIO-based I2C mode: dtoverlay=i2c-gpio,i2c_gpio_sda=3,i2c_gpio_scl=5,bus=1
            # Try GPIO 5 (SCL) and GPIO 3 (SDA) first
            logger.info("Attempting GPIO-based I2C initialization (GPIO 5=SCL, GPIO 3=SDA)")

            # Method 1: Try GPIO-based I2C pins with frequency
            try:
                import digitalio
                scl = digitalio.DigitalInOut(board.GP5)
                sda = digitalio.DigitalInOut(board.GP3)
                self.i2c = busio.I2C(scl, sda, frequency=100000)
                logger.info("Initialized GPIO I2C using GPIO 5 (SCL) and GPIO 3 (SDA) with frequency")
            except (ValueError, RuntimeError, AttributeError) as e:
                logger.debug(f"GPIO I2C init with GP5/GP3 (with freq) failed: {e}")

            # Method 2: Try GPIO-based I2C pins without frequency
            if self.i2c is None:
                try:
                    import digitalio
                    scl = digitalio.DigitalInOut(board.GP5)
                    sda = digitalio.DigitalInOut(board.GP3)
                    self.i2c = busio.I2C(scl, sda)
                    logger.info("Initialized GPIO I2C using GPIO 5 (SCL) and GPIO 3 (SDA)")
                except (ValueError, RuntimeError, AttributeError) as e:
                    logger.debug(f"GPIO I2C init with GP5/GP3 (no freq) failed: {e}")
        else:
            # Hardware I2C mode (default)
            logger.info("Attempting hardware I2C initialization")

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
            if i2c_mode == 'gpio':
                error_msg = (
                    "Failed to initialize GPIO-based I2C after trying multiple methods.\n"
                    "Troubleshooting steps:\n"
                    "1. Check /boot/config.txt contains: dtoverlay=i2c-gpio,i2c_gpio_sda=3,i2c_gpio_scl=5,bus=1\n"
                    "2. Verify display is connected: sudo i2cdetect -y 1\n"
                    "3. Reboot after enabling GPIO I2C: sudo shutdown -r now\n"
                    "4. If display is not needed, set ENABLE_DISPLAY=false in config\n"
                    "5. Try hardware I2C mode by setting I2C_MODE=hardware in config"
                )
            else:
                error_msg = (
                    "Failed to initialize hardware I2C after trying multiple methods. "
                    "Valid I2C ports reported: ((1, 3, 2), (0, 1, 0)).\n"
                    "Troubleshooting steps:\n"
                    "1. Verify I2C is enabled: sudo raspi-config -> Interface Options -> I2C -> Enable\n"
                    "2. Check /boot/config.txt contains: dtparam=i2c_arm=on\n"
                    "3. Verify display is connected: sudo i2cdetect -y 1\n"
                    "4. Reboot after enabling I2C: sudo shutdown -r now\n"
                    "5. If hardware I2C doesn't work, try GPIO mode: set I2C_MODE=gpio in config\n"
                    "6. If display is not needed, set ENABLE_DISPLAY=false in config"
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

        # Menu bar height (top status bar)
        self.menu_bar_height = 12
        self.content_start_y = self.menu_bar_height + 1

        # Cache for status info (update less frequently)
        self.status_cache = {}
        self.status_cache_time = 0
        self.status_cache_interval = 5  # Update status every 5 seconds

    def _get_battery_status(self):
        """Get battery percentage if available."""
        try:
            # Try reading from sysfs (common for power management ICs)
            # This is a placeholder - adjust based on your hardware
            with open('/sys/class/power_supply/battery/capacity', 'r') as f:
                return int(f.read().strip())
        except (FileNotFoundError, ValueError, IOError):
            # Try alternative paths or methods
            try:
                # Some systems use different paths
                with open('/sys/class/power_supply/BAT0/capacity', 'r') as f:
                    return int(f.read().strip())
            except (FileNotFoundError, ValueError, IOError):
                # Battery info not available
                return None

    def _get_wifi_status(self):
        """Check if WiFi is enabled/connected."""
        try:
            # Check if WiFi interface exists and is up
            result = subprocess.run(
                ['ip', 'link', 'show', 'wlan0'],
                capture_output=True,
                text=True,
                timeout=1
            )
            if result.returncode == 0 and 'state UP' in result.stdout:
                # Check if connected to network
                result = subprocess.run(
                    ['iwgetid', '-r'],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                if result.returncode == 0 and result.stdout.strip():
                    return 'connected'
                # Also check using iwconfig as fallback
                result = subprocess.run(
                    ['iwconfig', 'wlan0'],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                if result.returncode == 0 and 'ESSID:' in result.stdout and 'off/any' not in result.stdout:
                    # Extract ESSID to check if connected
                    import re
                    essid_match = re.search(r'ESSID:"([^"]+)"', result.stdout)
                    if essid_match and essid_match.group(1):
                        return 'connected'
                return 'enabled'
            return 'disabled'
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            # If WiFi interface check fails, try to see if wlan0 exists at all
            try:
                result = subprocess.run(
                    ['ip', 'link', 'show', 'wlan0'],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                if result.returncode == 0:
                    return 'enabled'
            except:
                pass
            return None

    def _get_bluetooth_status(self):
        """Check if Bluetooth is enabled."""
        config = read_config()
        if not config.get('ENABLE_SSH_BT', False):
            return None

        try:
            result = subprocess.run(
                ['systemctl', 'is-active', 'bluetooth'],
                capture_output=True,
                text=True,
                timeout=1
            )
            if result.returncode == 0 and 'active' in result.stdout:
                return 'enabled'
            return 'disabled'
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

    def _draw_battery_icon(self, x, y, percentage=None):
        """Draw a simple battery icon."""
        # Battery outline: 14x6 pixels (fits in 12px menu bar)
        # Outer rectangle (y+2 to y+8 = 6px height, fits in menu bar)
        self.draw.rectangle([x, y+2, x+13, y+8], outline=255, fill=0)
        # Positive terminal (small bump on right)
        self.draw.rectangle([x+13, y+4, x+15, y+6], outline=255, fill=255)

        if percentage is not None:
            # Fill level (11 pixels wide for the fill area)
            fill_width = int(11 * percentage / 100)
            if fill_width > 0:
                self.draw.rectangle([x+1, y+3, x+1+fill_width, y+7], outline=255, fill=255)

            # Percentage text (small, next to icon) - ensure it fits
            text_x = x + 17
            if text_x + 20 < self.width:  # Check if text fits
                self.draw.text((text_x, y+1), f"{percentage}%", font=self.font, fill=255)
        else:
            # Show "?" if battery status unavailable
            text_x = x + 17
            if text_x + 5 < self.width:  # Check if text fits
                self.draw.text((text_x, y+1), "?", font=self.font, fill=255)

    def _draw_wifi_icon(self, x, y, status=None):
        """Draw a simple WiFi icon."""
        # Ensure icon fits within menu bar bounds (12px height)
        icon_size = 7
        icon_y_start = y + 2  # Start at y+2
        icon_y_mid = y + 5    # Middle
        icon_y_end = y + 9    # End at y+9 (fits in 12px menu bar)

        if status == 'connected':
            # Connected: show filled signal bars (more visible)
            # Outer arc (largest)
            self.draw.arc([x, icon_y_start, x+icon_size, icon_y_end], start=180, end=0, fill=255)
            # Middle arc
            self.draw.arc([x+1, icon_y_start+2, x+icon_size-1, icon_y_end-2], start=180, end=0, fill=255)
            # Inner arc
            self.draw.arc([x+2, icon_y_start+4, x+icon_size-2, icon_y_end-4], start=180, end=0, fill=255)
            # Center dot
            self.draw.rectangle([x+3, icon_y_mid, x+4, icon_y_mid+1], fill=255)
        elif status == 'enabled':
            # Enabled but not connected: show outline only
            self.draw.arc([x, icon_y_start, x+icon_size, icon_y_end], start=180, end=0, outline=255)
            self.draw.arc([x+2, icon_y_start+2, x+icon_size-2, icon_y_end-2], start=180, end=0, outline=255)
        else:
            # Disabled: show X
            self.draw.line([x, icon_y_start, x+icon_size, icon_y_end], fill=255)
            self.draw.line([x+icon_size, icon_y_start, x, icon_y_end], fill=255)

    def _draw_bluetooth_icon(self, x, y, status=None):
        """Draw a simple Bluetooth icon - scaled down to fit menu bar."""
        # Smaller icon to fit in 12px menu bar
        icon_width = 5
        icon_y_start = y + 3  # Start at y+3
        icon_y_mid = y + 6    # Middle
        icon_y_end = y + 9    # End at y+9 (fits in 12px menu bar)
        center_x = x + 2      # Center of icon

        if status == 'enabled':
            # Bluetooth symbol (smaller, simplified)
            # Top triangle (smaller)
            self.draw.polygon([(center_x, icon_y_start), (x+icon_width, icon_y_mid-1), (center_x, icon_y_mid)], outline=255, fill=0)
            # Bottom triangle (smaller)
            self.draw.polygon([(center_x, icon_y_mid), (x+icon_width, icon_y_end-1), (center_x, icon_y_end)], outline=255, fill=0)
            # Center vertical line (shorter)
            self.draw.line([center_x, icon_y_start, center_x, icon_y_end], fill=255)
        else:
            # Disabled: show X (smaller)
            self.draw.line([x, icon_y_start+1, x+icon_width, icon_y_end-1], fill=255)
            self.draw.line([x+icon_width, icon_y_start+1, x, icon_y_end-1], fill=255)

    def _draw_menu_bar(self):
        """Draw the top menu bar with status icons."""
        # Draw menu bar background
        self.draw.rectangle([0, 0, self.width-1, self.menu_bar_height], outline=255, fill=0)

        # Draw separator line below menu bar
        self.draw.line([0, self.menu_bar_height, self.width, self.menu_bar_height], fill=255)

        # Update status cache if needed
        current_time = time.time()
        if current_time - self.status_cache_time > self.status_cache_interval:
            # Only get battery status if low battery monitoring is enabled
            enable_low_bat = get_config('ENABLE_LOW_BAT', False)
            if enable_low_bat:
                self.status_cache['battery'] = self._get_battery_status()
            else:
                self.status_cache['battery'] = None
            self.status_cache['wifi'] = self._get_wifi_status()
            self.status_cache['bluetooth'] = self._get_bluetooth_status()
            self.status_cache_time = current_time

        # Calculate total width needed for all icons (right-aligned)
        icon_widths = []

        # Bluetooth icon width
        bt_status = self.status_cache.get('bluetooth')
        if bt_status is not None:
            icon_widths.append(('bluetooth', 7))

        # WiFi icon width
        wifi_status = self.status_cache.get('wifi')
        if wifi_status is not None:
            icon_widths.append(('wifi', 9))

        # Battery icon width (if enabled)
        enable_low_bat = get_config('ENABLE_LOW_BAT', False)
        if enable_low_bat:
            battery_status = self.status_cache.get('battery')
            # Battery icon + text = ~40px
            icon_widths.append(('battery', 40))

        # Start from right side, work backwards
        x = self.width - 2  # Start at right edge with 2px margin

        # Draw icons from right to left
        for icon_name, icon_width in icon_widths:
            x -= icon_width
            if icon_name == 'bluetooth':
                self._draw_bluetooth_icon(x, 0, bt_status)
            elif icon_name == 'wifi':
                self._draw_wifi_icon(x, 0, wifi_status)
            elif icon_name == 'battery':
                self._draw_battery_icon(x, 0, battery_status)

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

        # Draw menu bar with status icons
        self._draw_menu_bar()

        # Check if warning should be displayed
        if self.warning_message:
            if self.warning_timeout and time.time() > self.warning_timeout:
                self.clear_warning()
            else:
                # Display warning message (split across lines if needed)
                # Start below menu bar
                lines = self.warning_message.split('\n')
                for i, line in enumerate(lines[:4]):  # Max 4 lines
                    y_pos = self.content_start_y + (i * 14)
                    if y_pos < self.height:
                        self.draw.text((2, y_pos), line[:20], font=self.font, fill=255)

                # Display image and return early
                self.disp.image(self.image)
                self.disp.show()
                return

        # Shell scripts for system monitoring from here:
        # https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
        try:
            cmd = "hostname -I | cut -d' ' -f1"
            IP = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
            cmd = "top -bn1 | grep load | awk '{printf \"CPU: %.2f\", $(NF-2)}'"
            CPU = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
            cmd = "free -m | awk 'NR==2{printf \"Mem: %s/%sMB\", $3,$2}'"
            MemUsage = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
        except Exception as e:
            logger.warning(f"Failed to get system info: {e}")
            IP = "N/A"
            CPU = "N/A"
            MemUsage = "N/A"

        # Write operations (starting below menu bar)
        y_offset = self.content_start_y
        line_height = 13

        self.draw.text((2, y_offset), f"IP: {IP}", font=self.font, fill=255)
        self.draw.text((2, y_offset + line_height), CPU, font=self.font, fill=255)
        self.draw.text((2, y_offset + (line_height * 2)), MemUsage, font=self.font, fill=255)
        self.draw.text((2, y_offset + (line_height * 3)), "Zero2 Controller", font=self.font, fill=255)

        # Display image.
        self.disp.image(self.image)
        self.disp.show()
