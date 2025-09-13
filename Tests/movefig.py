import pygame
from PIL import Image
from luma.core.interface.serial import spi
from luma.lcd.device import st7789
import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import RPi.GPIO as GPIO

# -------------------- GPIO --------------------
buttons = {
    "up": 5,
    "down": 6,
    "left": 13,
    "right": 19,
    "reset": 26,
}

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Подсветка дисплея
GPIO.setup(12, GPIO.OUT)
GPIO.output(12, GPIO.HIGH)

# Кнопки с подтяжкой
for pin in buttons.values():
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# -------------------- ADS1115 --------------------
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
chan = AnalogIn(ads, ADS.P0)

# -------------------- Дисплей --------------------
serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=16, bus_speed_hz=40000000)
device = st7789(serial, width=320, height=240, rotate=2)

# -------------------- Pygame --------------------
pygame.init()
width, height = 320, 240
surface = pygame.Surface((width, height))
font = pygame.font.Font(None, 24)
clock = pygame.time.Clock()

# -------------------- Квадратик --------------------
square_size = 30
x, y = width // 2, height // 2
speed = 5

def read_buttons():
    """Вернёт словарь с состоянием кнопок"""
    return {name: GPIO.input(pin) == GPIO.LOW for name, pin in buttons.items()}

# -------------------- Главный цикл --------------------
while True:
    surface.fill((0, 0, 0))

    # Управление кнопками
    state = read_buttons()
    if state["up"] and y - speed > 0:
        y -= speed
    if state["down"] and y + speed + square_size < height:
        y += speed
    if state["left"] and x - speed > 0:
        x -= speed
    if state["right"] and x + speed + square_size < width:
        x += speed
    if state["reset"]:
        x, y = width // 2, height // 2

    # Рисуем квадрат
    pygame.draw.rect(surface, (0, 200, 255), (x, y, square_size, square_size))

    # Измерение напряжения
    voltage = chan.voltage * 2
    text = f"Battery: {voltage:.2f} V"
    text_surface = font.render(text, True, (255, 255, 255))
    surface.blit(text_surface, (10, 45))

    # Отобразить на дисплее
    raw_str = pygame.image.tostring(surface, "RGB")
    img = Image.frombytes("RGB", (width, height), raw_str)
    device.display(img)

    clock.tick(60)
