#!/usr/bin/python3

from PIL import Image, ImageDraw, ImageFont

class Menu:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.image = Image.new('1', (width, height))
        self.draw = ImageDraw.Draw(self.image)
        self.font = ImageFont.load_default()

    def draw_menu(self, options, selected_option):
        self.draw.rectangle((0, 0, self.width, self.height), outline=255, fill=0)
        y = 0
        for i, option in enumerate(options):
            if i == selected_option:
                self.draw.text((0, y), option, font=self.font, fill=255)
            else:
                self.draw.text((0, y), option, font=self.font, fill=128)
            y += 10