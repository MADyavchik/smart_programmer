import RPi.GPIO as GPIO
from luma.core.interface.serial import spi
from luma.lcd.device import st7789
from PIL import Image
import time
import subprocess

# Включаем подсветку на GPIO12
GPIO.setmode(GPIO.BCM)
GPIO.setup(12, GPIO.OUT)
GPIO.output(12, GPIO.HIGH)  # включить подсветку

# Инициализация дисплея
serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=16, bus_speed_hz=40000000)
device = st7789(serial, width=320, height=240, rotate=0)

# Загрузка и вывод логотипа
logo = Image.open("/root/smart_programmer/logo.png").resize((320, 240)).convert("RGB")
device.display(logo)
# Подождём пару секунд
time.sleep(3)

# Запускаем основную программу
subprocess.run(["python3", "/root/smart_programmer/Tests/Pygame_test.py"])
