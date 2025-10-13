
import os
import time
import RPi.GPIO as GPIO
import pygame
from PIL import Image
from luma.core.interface.serial import spi
from luma.lcd.device import st7789
from battery_status import get_battery_status  # импортируем функцию
from log_reader import read_logs, add_log_line, clean_line


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

running = True
try:
    while running:
        surface.fill((255, 255, 255))  # белый фон

        # --- Главное меню ---
        if state == STATE_MAIN:
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
                    # создаём генератор логов из UART
                    log_generator = read_logs(port="/dev/ttyS0", baud=115200)
                    current_log_line = ""
                    time.sleep(0.2)

        # --- Подменю Burn ---
        elif state == STATE_BURN:
            y_start = 50
            for i, folder in enumerate(folders):
                color = (255, 0, 0) if i == selected else (0, 0, 0)
                text_surface = font.render(folder, True, color)
                surface.blit(text_surface, (40, y_start + i * 40))

            if GPIO.input(buttons["up"]) == GPIO.LOW and folders:
                selected = (selected - 1) % len(folders)
            elif GPIO.input(buttons["down"]) == GPIO.LOW and folders:
                selected = (selected + 1) % len(folders)
            elif GPIO.input(buttons["left"]) == GPIO.LOW:
                state = STATE_MAIN
                selected = 0
                time.sleep(0.2)
            elif GPIO.input(buttons["reset"]) == GPIO.LOW and folders:
                choice = folders[selected]
                print(f"Выбрана папка прошивки: {choice}")
                time.sleep(0.2)

        # --- Экран Info ---
        elif state == STATE_INFO:
            voltage, charging = get_battery_status()
            text1 = f"Battery: {voltage:.2f} V"
            text2 = "Charging: Yes" if charging else "Charging: No"

            txt1 = font.render(text1, True, (0, 0, 0))
            txt2 = font.render(text2, True, (0, 0, 0))
            surface.blit(txt1, (50, 80))
            surface.blit(txt2, (50, 120))

            if GPIO.input(buttons["left"]) == GPIO.LOW:
                state = STATE_MAIN
                selected = 0
                time.sleep(0.2)

       # --- Экран логов ---
        elif state == STATE_LOGS:
            surface.fill((255, 255, 255))  # белый фон

            try:
                line = next(log_generator)
                clean = clean_line(line)
                print(line)

                visible_lines = add_log_line(clean, font, max_width=300, max_height=170, line_spacing=4)

            except StopIteration:
                visible_lines = add_log_line("Лог завершён.", font, max_width=300, max_height=170, line_spacing=4)

            # ---- ПАРАМЕТРЫ ОТОБРАЖЕНИЯ ----
            line_height = font.get_linesize() + 4
            MAX_VISIBLE_LINES = 170 // line_height

            # ✅ АВТОПРОКРУТКА, если включена
            if auto_scroll:
                scroll_index = max(0, len(visible_lines) - MAX_VISIBLE_LINES)

            # ---- ОБРАБОТКА КНОПОК ----
            if GPIO.input(buttons["up"]) == GPIO.LOW:
                auto_scroll = False  # отключаем авто
                scroll_index = max(0, scroll_index - 1)
                time.sleep(0.15)

            if GPIO.input(buttons["down"]) == GPIO.LOW:
                auto_scroll = False  # отключаем авто
                max_scroll = max(0, len(visible_lines) - MAX_VISIBLE_LINES)
                scroll_index = min(max_scroll, scroll_index + 1)
                time.sleep(0.15)

            if GPIO.input(buttons["right"]) == GPIO.LOW:
                # включаем автопрокрутку и прыгаем в конец
                auto_scroll = True
                scroll_index = max(0, len(visible_lines) - MAX_VISIBLE_LINES)
                time.sleep(0.15)

            # ---- ОТРИСОВКА ----
            y_start = 35
            start = scroll_index
            end = scroll_index + MAX_VISIBLE_LINES

            for i, (line_text, is_indent) in enumerate(visible_lines[start:end]):
                x_offset = 10 + (20 if is_indent else 0)
                # Если в строке есть "ReportBuilder:", красим в красный
                if "ReportBuilder:" in line_text:
                    color = COLOR_ALERT
                else:
                    color = COLOR_NORMAL

                txt = font.render(line_text, True, color)
                surface.blit(txt, (x_offset, y_start + i * line_height))

            # ---- ВЫХОД ----
            if GPIO.input(buttons["left"]) == GPIO.LOW:
                state = STATE_MAIN
                selected = 0
                time.sleep(0.2)

        # Вывод на дисплей
        raw_str = pygame.image.tostring(surface, "RGB")
        img = Image.frombytes("RGB", (width, height), raw_str)
        device.display(img)

        clock.tick(10)

finally:
    GPIO.cleanup()
