import time
import RPi.GPIO as GPIO
from luma.core.interface.serial import spi
from luma.lcd.device import st7789
from PIL import Image, ImageDraw

# --- Настройка GPIO для подсветки ---
GPIO.setmode(GPIO.BCM)
BLC = 12   # подсветка
GPIO.setup(BLC, GPIO.OUT)
GPIO.output(BLC, GPIO.HIGH)  # включаем подсветку

# --- Настройка дисплея ---
serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=16, bus_speed_hz=16000000)
device = st7789(serial, width=320, height=240, rotate=2)

# --- Функция: залить экран цветом ---
def fill(color):
    img = Image.new("RGB", (device.width, device.height), color)
    device.display(img)

# --- Тест: выводим разные цвета ---
for color in ["red", "green", "blue", "white", "black"]:
    fill(color)
    time.sleep(1)

print("Тест завершёнен!")
GPIO.cleanup()
