
import os
import time
import RPi.GPIO as GPIO
import pygame
from PIL import Image
from luma.core.interface.serial import spi
from luma.lcd.device import st7789
from battery_status import get_battery_status  # импортируем функцию
from log_reader import LogManager



scroll_index = 0
auto_scroll = True
COLOR_NORMAL = (0, 0, 0)       # чёрный
COLOR_ALERT = (255, 0, 0)      # красный

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
font = pygame.font.Font(None, 20)

log_manager = LogManager(font, max_width=300, max_height=170, line_spacing=4)


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
STATE_INFO = "info"
STATE_LOGS = "logs"
state = STATE_MAIN

selected = 0
folders = []  # список папок для подменю

# --- Основной цикл меню + экран логов ---
try:
    running = True
    while running:
        surface.fill((255, 255, 255))  # каждый кадр чистим экран

        # --- Главное меню ---
        if state == STATE_MAIN:
            for i, (name, icon) in enumerate(icons):
                x, y = positions[i]
                surface.blit(icon, (x, y))
                if i == selected:
                    pygame.draw.rect(surface, (0, 0, 0), (x-2, y-2, 28, 28), 2)

            # Обработка кнопок
            if GPIO.input(buttons["up"]) == GPIO.LOW:
                if selected in [2, 3]: selected -= 2
            elif GPIO.input(buttons["down"]) == GPIO.LOW:
                if selected in [0, 1]: selected += 2
            elif GPIO.input(buttons["left"]) == GPIO.LOW:
                if selected in [1, 3]: selected -= 1
            elif GPIO.input(buttons["right"]) == GPIO.LOW:
                if selected in [0, 2]: selected += 1
            elif GPIO.input(buttons["reset"]) == GPIO.LOW:
                choice = icons[selected][0]
                if choice == "burn":
                    state = STATE_BURN
                    selected = 0
                    base_path = "/root/smart_programmer/Прошивки"
                    folders = [f for f in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, f))]
                    folders.sort()
                    time.sleep(0.2)
                elif choice == "info":
                    state = STATE_INFO
                    time.sleep(0.2)
                elif choice == "download":
                    state = STATE_LOGS
                    log_manager.start(port="/dev/ttyS0", baud=115200)
                    time.sleep(0.2)

        # --- Подменю Burn ---
        elif state == STATE_BURN:
            y_start = 50
            for i, folder in enumerate(folders):
                color = (255, 0, 0) if i == selected else (0, 0, 0)
                surface.blit(font.render(folder, True, color), (40, y_start + i*40))

            if GPIO.input(buttons["up"]) == GPIO.LOW and folders:
                selected = (selected-1) % len(folders)
            elif GPIO.input(buttons["down"]) == GPIO.LOW and folders:
                selected = (selected+1) % len(folders)
            elif GPIO.input(buttons["left"]) == GPIO.LOW:
                state = STATE_MAIN
                selected = 0
                time.sleep(0.2)

        # --- Экран Info ---
        elif state == STATE_INFO:
            voltage, charging = get_battery_status()
            txt1 = font.render(f"Battery: {voltage:.2f} V", True, (0,0,0))
            txt2 = font.render(f"Charging: {'Yes' if charging else 'No'}", True, (0,0,0))
            surface.blit(txt1, (50, 80))
            surface.blit(txt2, (50, 120))

            if GPIO.input(buttons["left"]) == GPIO.LOW:
                state = STATE_MAIN
                selected = 0
                time.sleep(0.2)

        # --- Экран логов ---
        elif state == STATE_LOGS:
            try:
                line = next(log_manager.generator)
                if line is not None:
                    log_manager.add_line(line)
                log_manager.add_line(line)
            except StopIteration:
                pass

            visible_lines, line_height = log_manager.get_visible()


            # --- Кнопки прокрутки ---
            if GPIO.input(buttons["up"]) == GPIO.LOW:
                log_manager.scroll_up()
                time.sleep(0.05)
            if GPIO.input(buttons["down"]) == GPIO.LOW:
                log_manager.scroll_down()
                time.sleep(0.05)
            if GPIO.input(buttons["right"]) == GPIO.LOW:
                log_manager.scroll_to_end()
                time.sleep(0.05)
            if GPIO.input(buttons["left"]) == GPIO.LOW:
                state = STATE_MAIN
                selected = 0
                time.sleep(0.2)

            # --- Отрисовка видимых строк ---
            y_start = 35
            for i, (line_text, is_indent) in enumerate(visible_lines):
                x_offset = 10 + (20 if is_indent else 0)
                color = (255,0,0) if log_manager.is_alert_line(line_text) else (0,0,0)
                surface.blit(font.render(line_text, True, color), (x_offset, y_start + i*line_height))

        # --- Обновляем дисплей один раз за цикл ---
        raw_str = pygame.image.tostring(surface, "RGB")
        img = Image.frombytes("RGB", (width, height), raw_str)
        device.display(img)

        clock.tick(10)

finally:
    GPIO.cleanup()
