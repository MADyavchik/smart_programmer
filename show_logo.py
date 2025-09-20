from luma.core.interface.serial import spi
from luma.lcd.device import st7789
from PIL import Image

# Инициализация дисплея
serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=16, bus_speed_hz=40000000)
device = st7789(serial, width=320, height=240, rotate=0)

# Загрузка и вывод логотипа
logo = Image.open("logo.png").resize((320, 240)).convert("RGB")
device.display(logo)
