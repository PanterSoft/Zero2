import RPi.GPIO as GPIO
import os
import time
import subprocess
from threading import Thread
from modules.logger import get_logger
from modules.config import get_config

logger = get_logger(__name__)

class PowerManager:
    def __init__(self, pin=None, threshold=None, warning_time=None, display_manager=None):
        """
        Initialize Power Manager.

        Args:
            pin: GPIO pin number for low battery detection (defaults to config)
            threshold: Seconds low battery signal must persist before shutdown (defaults to config)
            warning_time: Seconds to warn user before shutdown (defaults to config)
            display_manager: Optional DisplayManager instance for warnings
        """
        # Load from config if not provided
        self.pin = pin if pin is not None else get_config('POWER_GPIO_PIN', 25)
        self.threshold = threshold if threshold is not None else get_config('POWER_THRESHOLD', 30)
        warning_time_config = warning_time if warning_time is not None else get_config('POWER_WARNING_TIME', 30)
        self.warning_time = min(warning_time_config, self.threshold)  # Ensure warning_time doesn't exceed threshold
        self.display_manager = display_manager
        self.notify_terminals = get_config('POWER_NOTIFY_TERMINALS', True)
        self.running = False
        self.shutdown_warning_sent = False

        GPIO.setmode(GPIO.BCM)
        # Use pull-up resistor so pin reads HIGH by default (LOW = low battery signal)
        # This prevents false shutdowns if pin is floating/unconnected
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def start_monitoring(self):
        self.running = True
        self.thread = Thread(target=self._monitor_loop)
        self.thread.daemon = True
        self.thread.start()

    def _send_wall_message(self, message):
        """
        Send message to all logged-in users via wall command.

        Args:
            message: Message to send
        """
        if not self.notify_terminals:
            return

        try:
            # Use wall command to send message to all terminals
            process = subprocess.Popen(
                ['wall'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            process.communicate(input=message.encode('utf-8'), timeout=2)
        except Exception as e:
            logger.debug(f"Failed to send wall message (may not be critical): {e}")

    def _send_warning(self, seconds_remaining, force_log=False):
        """
        Send warning message to display, terminals, and log.

        Args:
            seconds_remaining: Seconds until shutdown
            force_log: If True, always log (for first warning and final countdown)
        """
        warning_msg = f"LOW BATTERY!\nShutdown in {int(seconds_remaining)}s\nSave your work!"
        wall_msg = f"\n\n*** WARNING: LOW BATTERY ***\nSystem will shutdown in {int(seconds_remaining)} seconds!\nPlease save your work immediately!\n\n"

        # Send to OLED display
        if self.display_manager:
            try:
                self.display_manager.show_warning(warning_msg)
            except Exception as e:
                logger.error(f"Failed to display warning: {e}")

        # Send to all terminals via wall
        if force_log or int(seconds_remaining) % 10 == 0 or seconds_remaining <= 10:
            self._send_wall_message(wall_msg)

        # Log at key intervals: first warning, every 10 seconds, and final 10 seconds
        should_log = force_log or int(seconds_remaining) % 10 == 0 or seconds_remaining <= 10
        if should_log:
            logger.warning(f"Low battery detected. Shutting down in {int(seconds_remaining)} seconds. Save your work!")

    def _monitor_loop(self):
        logger.info(f"Starting power monitoring on GPIO {self.pin}")
        while self.running:
            # Wait for falling edge
            if GPIO.input(self.pin) == GPIO.LOW:
                start_time = time.time()
                logger.warning("Low battery signal detected on GPIO %d", self.pin)
                self.shutdown_warning_sent = False

                shutdown_triggered = True
                while time.time() - start_time < self.threshold:
                    if GPIO.input(self.pin) == GPIO.HIGH:
                        logger.info("Low battery signal cleared - shutdown cancelled")
                        shutdown_triggered = False
                        self.shutdown_warning_sent = False
                        if self.display_manager:
                            try:
                                self.display_manager.clear_warning()
                            except Exception:
                                pass
                        break

                    elapsed = time.time() - start_time
                    remaining = self.threshold - elapsed

                    # Send warning when we enter the warning period
                    if remaining <= self.warning_time and not self.shutdown_warning_sent:
                        self._send_warning(remaining, force_log=True)
                        self.shutdown_warning_sent = True

                    # Update warning countdown (display every second, log at intervals)
                    if self.shutdown_warning_sent and remaining > 0:
                        force_log = (int(remaining) % 10 == 0) or (remaining <= 10)
                        self._send_warning(remaining, force_log=force_log)

                    time.sleep(1)

                if shutdown_triggered:
                    logger.critical(f"Low battery persisted for {self.threshold}s. Initiating system shutdown.")

                    # Final warning to all terminals
                    final_wall_msg = "\n\n*** SYSTEM SHUTDOWN INITIATED ***\nLow battery detected. System shutting down NOW!\n\n"
                    self._send_wall_message(final_wall_msg)

                    if self.display_manager:
                        try:
                            self.display_manager.show_warning("SHUTTING DOWN\nNOW!")
                        except Exception:
                            pass
                    time.sleep(2)  # Give display time to update
                    os.system("shutdown -h now")
                    self.running = False

            time.sleep(0.5)

    def stop(self):
        self.running = False
        GPIO.cleanup()
