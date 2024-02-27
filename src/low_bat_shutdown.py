#!/usr/bin/env python3

import RPi.GPIO as GPIO
import os
import dbus
from time import sleep, time
from datetime import datetime

# GPIO pin to monitor
GPIO_PIN = 25

# Log file path
LOG_FILE = "/var/log/shutdown_warnings.log"

# Threshold in seconds
SHUTDOWN_THRESHOLD = 30  # Adjust as needed

# Initialize GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(GPIO_PIN, GPIO.IN, pull_up_down=GPIO.PUD_OFF)  # Set pull-up/pull-down resistor as floating

# Function to send message to desktop sessions
def send_message_to_session(message):
    bus = dbus.SessionBus()
    notifications = bus.get_object("org.freedesktop.Notifications", "/org/freedesktop/Notifications")
    notify_interface = dbus.Interface(notifications, "org.freedesktop.Notifications")
    notify_interface.Notify("Low Battery Shutdown", 0, "", "Zero Shutdown Warning", message, [], {}, -1)

try:
    while True:
        start_time = None

        # Wait for GPIO pin to go low
        GPIO.wait_for_edge(GPIO_PIN, GPIO.FALLING)
        start_time = time()

        # Wait for the threshold time
        while time() - start_time < SHUTDOWN_THRESHOLD:
            if GPIO.input(GPIO_PIN) == GPIO.HIGH:
                start_time = None
                break
            sleep(1)

        if start_time is not None:
            # Log shutdown warning
            with open(LOG_FILE, "a") as log:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log.write(f"{timestamp}: Zero is shutting down due to Low Battery Warning for {SHUTDOWN_THRESHOLD} seconds!\n")

            # Send warning message to all desktop sessions
            send_message_to_session(f"Raspberry Pi is shutting down due to Low Battery Warning for {SHUTDOWN_THRESHOLD} seconds!")

            # Add delay to ensure message is displayed
            sleep(52)

            # Shutdown Raspberry Pi
            os.system("sudo shutdown -h now")

except KeyboardInterrupt:
    print("Shutdown script terminated by user.")
finally:
    GPIO.cleanup()
