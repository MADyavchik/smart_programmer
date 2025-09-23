import os
import RPi.GPIO as GPIO
import pygame
from PIL import Image
from luma.core.interface.serial import spi
from luma.lcd.device import st7789

# GPIO-кнопки
buttons = {
    "up": 5,
    "down": 19,
    "left": 6,     # используем как "назад"
    "right": 26,
    "reset": 13,   # выбор
}
GPIO.setmode(GPIO.BCM)
for pin in buttons.values():
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Дисплей
serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=16, bus_speed_hz=40000000)
device = st7789(serial, width=320, height=240, rotate=0)

# Pygame
pygame.init()
width, height = 320, 240
surface = pygame.Surface((width, height))
clock = pygame.time.Clock()
font = pygame.font.Font(None, 32)

# Загружаем иконки
icon_files = [
    ("burn", "icons/burn.png"),
    ("download", "icons/download.png"),
    ("settings", "icons/settings.png"),
    ("info", "icons/info.png"),
]
icons = []
for name, path in icon_files:
    icon = pygame.image.load(path)
    icon = pygame.transform.smoothscale(icon, (24, 24))
    icons.append((name, icon))

# Позиции для главного меню (2x2 сетка)
positions = [
    (100, 70),   # burn
    (180, 70),   # download
    (100, 150),  # settings
    (180, 150),  # info
]

# Состояния
STATE_MAIN = "main"
STATE_BURN = "burn_menu"
state = STATE_MAIN

selected = 0
folders = []  # список папок для подменю

running = True
try:
    while running:
        surface.fill((255, 255, 255))  # белый фон

        if state == STATE_MAIN:
            # Главное меню (иконки)
            for i, (name, icon) in enumerate(icons):
                x, y = positions[i]
                surface.blit(icon, (x, y))
                if i == selected:
                    pygame.draw.rect(surface, (0, 0, 0), (x - 2, y - 2, 28, 28), 2)

            # Обработка кнопок
            if GPIO.input(buttons["up"]) == GPIO.LOW:
                if selected in [2, 3]:
                    selected -= 2
            elif GPIO.input(buttons["down"]) == GPIO.LOW:
                if selected in [0, 1]:
                    selected += 2
            elif GPIO.input(buttons["left"]) == GPIO.LOW:
                if selected in [1, 3]:
                    selected -= 1
            elif GPIO.input(buttons["right"]) == GPIO.LOW:
                if selected in [0, 2]:
                    selected += 1
            elif GPIO.input(buttons["reset"]) == GPIO.LOW:
                choice = icons[selected][0]
                print(f"Выбрана иконка: {choice}")
                if choice == "burn":
                    # Переход в подменю
                    state = STATE_BURN
                    selected = 0
                    # Загружаем список папок из "Прошивки"
                    base_path = "/root/smart_programmer/Прошивки"
                    folders = [f for f in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, f))]
                    folders.sort()
                elif choice == "info":
                    running = False

        elif state == STATE_BURN:
            # Подменю (список папок)
            y_start = 50
            for i, folder in enumerate(folders):
                color = (255, 0, 0) if i == selected else (0, 0, 0)
                text_surface = font.render(folder, True, color)
                surface.blit(text_surface, (40, y_start + i * 40))

            # Обработка кнопок
            if GPIO.input(buttons["up"]) == GPIO.LOW and folders:
                selected = (selected - 1) % len(folders)
            elif GPIO.input(buttons["down"]) == GPIO.LOW and folders:
                selected = (selected + 1) % len(folders)
            elif GPIO.input(buttons["left"]) == GPIO.LOW:
                # Назад в главное меню
                state = STATE_MAIN
                selected = 0
            elif GPIO.input(buttons["reset"]) == GPIO.LOW and folders:
                choice = folders[selected]
                print(f"Выбрана папка прошивки: {choice}")
                # Здесь можно запускать логику прошивки

        # Вывод на дисплей
        raw_str = pygame.image.tostring(surface, "RGB")
        img = Image.frombytes("RGB", (width, height), raw_str)
        device.display(img)

        clock.tick(10)

finally:
    GPIO.cleanup()
