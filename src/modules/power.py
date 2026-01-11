import RPi.GPIO as GPIO
import os
import time
from threading import Thread

class PowerManager:
    def __init__(self, pin=25, threshold=30):
        self.pin = pin
        self.threshold = threshold
        self.running = False

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_OFF)

    def start_monitoring(self):
        self.running = True
        self.thread = Thread(target=self._monitor_loop)
        self.thread.daemon = True
        self.thread.start()

    def _monitor_loop(self):
        print(f"Starting power monitoring on GPIO {self.pin}")
        while self.running:
            # Wait for falling edge
            if GPIO.input(self.pin) == GPIO.LOW:
                start_time = time.time()
                print("Low battery signal detected...")

                shutdown_triggered = True
                while time.time() - start_time < self.threshold:
                    if GPIO.input(self.pin) == GPIO.HIGH:
                        print("Low battery signal cleared.")
                        shutdown_triggered = False
                        break
                    time.sleep(1)

                if shutdown_triggered:
                    print(f"Low battery persisted for {self.threshold}s. Shutting down.")
                    os.system("shutdown -h now")
                    self.running = False

            time.sleep(0.5)

    def stop(self):
        self.running = False
        GPIO.cleanup()
