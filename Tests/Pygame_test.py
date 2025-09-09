import pygame
from PIL import Image
from luma.core.interface.serial import spi
from luma.lcd.device import st7789
import time
import random
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import RPi.GPIO as GPIO


# Включаем подсветку на GPIO12
GPIO.setmode(GPIO.BCM)
GPIO.setup(12, GPIO.OUT)
GPIO.output(12, GPIO.HIGH)  # включить подсветку


# I2C интерфейс
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
chan = AnalogIn(ads, ADS.P0)  # Канал A0

# Дисплей
serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=16, bus_speed_hz=40000000)
device = st7789(serial, width=320, height=240, rotate=2)

# Pygame
pygame.init()
width, height = 320, 240
surface = pygame.Surface((width, height))
font = pygame.font.Font(None, 24)
clock = pygame.time.Clock()

# Видимая область
VISIBLE_TOP = 5
VISIBLE_BOTTOM = height - 5

GRAVITY = 0.1
DAMPING = 1.0

import random
import pygame

class Ball:
    def __init__(self):
        self.radius = random.randint(10, 50)
        self.x = random.randint(self.radius, width - self.radius)
        self.y = random.randint(VISIBLE_TOP + self.radius, VISIBLE_BOTTOM - self.radius)
        self.dx = random.uniform(-3, 3)
        self.dy = random.uniform(-3, 0)
        self.color = self.random_color()
        self.alpha = random.randint(100, 150)  # Прозрачность от 100 до 255

    def random_color(self):
        return (
            random.randint(100, 255),
            random.randint(100, 255),
            random.randint(100, 255)
        )

    def move(self):
        self.dy += GRAVITY
        self.x += self.dx
        self.y += self.dy

        # Стенки по X
        if self.x - self.radius < 0 or self.x + self.radius > width:
            self.dx *= -1
            self.color = self.random_color()

        # Стенка снизу
        if self.y + self.radius > VISIBLE_BOTTOM:
            self.y = VISIBLE_BOTTOM - self.radius
            self.dy = -self.initial_bounce_speed()  # фиксированная скорость вверх
            self.color = self.random_color()

        # Стенка сверху
        if self.y - self.radius < VISIBLE_TOP:
            self.y = VISIBLE_TOP + self.radius
            self.dy = self.initial_bounce_speed()  # вниз
            self.color = self.random_color()

    def draw(self, surface):
        # Поверхность с альфа-каналом
        ball_surface = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        color_with_alpha = (*self.color, self.alpha)
        pygame.draw.circle(ball_surface, color_with_alpha, (self.radius, self.radius), self.radius)
        surface.blit(ball_surface, (int(self.x - self.radius), int(self.y - self.radius)))

    def initial_bounce_speed(self):
        return random.uniform(3.0, 5.0)  # можно сделать постоянным, если не хочешь случайность

# Создание шаров
balls = [Ball() for _ in range(30)]

while True:
    surface.fill((0, 0, 0))

    # Обновить и нарисовать шары
    for ball in balls:
        ball.move()
        ball.draw(surface)

    # Измерение напряжения (умножаем на 2, если делитель)
    voltage = chan.voltage * 2
    text = f"Battery: {voltage:.2f} V"
    text_surface = font.render(text, True, (255, 255, 255))
    surface.blit(text_surface, (10, 45))

    # Отобразить на дисплее
    raw_str = pygame.image.tostring(surface, "RGB")
    img = Image.frombytes("RGB", (width, height), raw_str)
    device.display(img)

    clock.tick(120)

