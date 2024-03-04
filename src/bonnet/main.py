#!/usr/bin/python3

import time
import threading
import board
import busio
from digitalio import DigitalInOut, Direction, Pull
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306


from menue import Menu
from os_stats import *

class Base:
    def __init__(self):
        # Init Display
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.display = adafruit_ssd1306.SSD1306_I2C(128, 64, self.i2c)

        # Init Buttons
        self.button_pins = [board.D5, board.D6, board.D27, board.D23, board.D17, board.D22, board.D4]
        self.button_names = ["return", "select", "left", "right", "up", "down", "middle"]

        button_return = DigitalInOut(board.D5)
        button_select = DigitalInOut(board.D6)
        button_left = DigitalInOut(board.D27)
        button_right = DigitalInOut(board.D23)
        button_up = DigitalInOut(board.D17)
        button_down = DigitalInOut(board.D22)
        button_middle = DigitalInOut(board.D4)

        self.buttons = [button_return, button_select, button_left, button_right, button_up, button_down, button_middle]

        for button in self.buttons:
            button.direction = Direction.INPUT
            button.pull = Pull.UP

        self.selected_item = [0]

        self.sys_stats = None

    def home(self):
        # Create an image with the stats
        image = Image.new("1", (128, 64))
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()

        self.sys_stats = update_sys_stats()

        if self.sys_stats is not None:
            cpu_usage = self.sys_stats["cpu_usage"]
            ram_usage = self.sys_stats["ram_usage"]
            cpu_temp = self.sys_stats["cpu_temp"]
        else:
            cpu_usage = "N/A"
            ram_usage = "N/A"
            cpu_temp = "N/A"

        draw.text((0, 0), f"CPU Temp: {cpu_temp} °C", font=font, fill=255)
        draw.text((0, 10), f"CPU Usage: {cpu_usage} %", font=font, fill=255)
        draw.text((0, 20), f"RAM Usage: {ram_usage} %", font=font, fill=255)

        # Clock
        current_time = time.strftime("%H:%M:%S")
        draw.text((0, 30), f"Time: {current_time}", font=font, fill=255)

        return image

    def empty(self):
        image = Image.new("1", (128, 64))
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()
        return image

    def nav(self, button_name):
        # Check button presses
        if button_name == "return":
            # Return
            self.selected_item.pop()
        elif button_name == "select":
            # Select
            return self.selected_item
        elif button_name == "left":
            # Left
            self.selected_item.pop()
        elif button_name == "right":
            # Right
            self.selected_item.append(1)
        elif button_name == "up":
            # Up
            current = self.selected_item.pop()
            self.selected_item.append(current + 1)
        elif button_name == "down":
            # Down
            current = self.selected_item.pop()
            self.selected_item.append(current - 1)
        elif button_name == "middle":
            self.selected_item.clear()
        else:
            return

def main():
    base = Base()

    # Main Loop
    while True:
        # Menue Navigation
        for button_name, button in zip(base.button_names, base.buttons):
            if (button.value == False):
                base.nav(button_name)

        print(base.selected_item)

        if base.selected_item == [0]:
            # Display home screen
            image = base.home()
        elif base.selected_item == [0, 1]:
            # Display empty screen
            image = base.empty()

        base.display.image(image)
        base.display.show()
        print("Updated Display")
        time.sleep(1)

if __name__ == "__main__":
    main()