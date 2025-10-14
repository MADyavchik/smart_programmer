import RPi.GPIO as GPIO
from luma.core.interface.serial import spi
from luma.lcd.device import st7789
from PIL import Image
import time
import subprocess

# Включаем подсветку на GPIO12
GPIO.setmode(GPIO.BCM)
GPIO.setup(12, GPIO.OUT)
GPIO.output(12, GPIO.LOW)  # включить подсветку

# Инициализация дисплея
serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=16, bus_speed_hz=40000000)
device = st7789(serial, width=320, height=240, rotate=0)

# Загружаем логотип
logo = Image.open("/root/smart_programmer/logo.png").convert("RGB")

# Масштабируем по высоте = 50px, ширина пропорционально
target_height = 50
w, h = logo.size
new_width = int(w * (target_height / h))
logo_resized = logo.resize((new_width, target_height), Image.LANCZOS)

# Создаём чёрный фон под экран
background = Image.new("RGB", (320, 240), (0, 0, 0))

# Центруем картинку
x = (320 - logo_resized.width) // 2
y = (240 - logo_resized.height) // 2
background.paste(logo_resized, (x, y))

# Отображаем
device.display(background)
#time.sleep(0.1)
GPIO.output(12, GPIO.HIGH)

# Подождём пару секунд
time.sleep(1)

# Запускаем основную программу
GPIO.cleanup()
subprocess.run(["python3", "/root/smart_programmer/Tests/Menu_test.py"])
