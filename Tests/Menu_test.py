import RPi.GPIO as GPIO
import pygame
from PIL import Image
from luma.core.interface.serial import spi
from luma.lcd.device import st7789

# GPIO-кнопки
buttons = {
    "up": 5,
    "down": 19,
    "left": 6,
    "right": 26,
    "reset": 13,
}
GPIO.setmode(GPIO.BCM)
for pin in buttons.values():
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # кнопки на землю

# Дисплей
serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=16, bus_speed_hz=40000000)
device = st7789(serial, width=320, height=240, rotate=0)

# Pygame
pygame.init()
width, height = 320, 240
surface = pygame.Surface((width, height))
clock = pygame.time.Clock()

# Загружаем иконки (масштабируем в 24x24)
icon_files = [
    ("burn", "icons/burn.png"),
    ("download", "icons/download.png"),
    ("settings", "icons/settings.png"),
    ("info", "icons/info.png"),
]
icons = []
for name, path in icon_files:
    icon = pygame.image.load(path)
    icon = pygame.transform.smoothscale(icon, (24, 24))  # гарантируем 24x24
    icons.append((name, icon))

# Координаты для 2x2 сетки
positions = [
    (100, 70),   # burn (верхний левый)
    (180, 70),   # download (верхний правый)
    (100, 150),  # settings (нижний левый)
    (180, 150),  # info (нижний правый)
]

selected = 0  # индекс выбранной иконки

running = True
try:
    while running:
        surface.fill((255, 255, 255))  # белый фон

        # Рисуем иконки
        for i, (name, icon) in enumerate(icons):
            x, y = positions[i]
            surface.blit(icon, (x, y))

            # Подсветка рамкой выбранной иконки
            if i == selected:
                pygame.draw.rect(surface, (0, 0, 0), (x - 2, y - 2, 28, 28), 2)

        # Вывод на дисплей
        raw_str = pygame.image.tostring(surface, "RGB")
        img = Image.frombytes("RGB", (width, height), raw_str)
        device.display(img)

        # Обработка кнопок
        if GPIO.input(buttons["up"]) == GPIO.LOW:
            if selected in [2, 3]:  # нижний ряд -> верхний
                selected -= 2
        elif GPIO.input(buttons["down"]) == GPIO.LOW:
            if selected in [0, 1]:  # верхний ряд -> нижний
                selected += 2
        elif GPIO.input(buttons["left"]) == GPIO.LOW:
            if selected in [1, 3]:  # правый -> левый
                selected -= 1
        elif GPIO.input(buttons["right"]) == GPIO.LOW:
            if selected in [0, 2]:  # левый -> правый
                selected += 1
        elif GPIO.input(buttons["reset"]) == GPIO.LOW:
            choice = icons[selected][0]
            print(f"Выбрана иконка: {choice}")
            if choice == "info":  # например, выход
                running = False

        clock.tick(10)
finally:
    GPIO.cleanup()
