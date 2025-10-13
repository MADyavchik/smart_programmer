import os
import time
import RPi.GPIO as GPIO
import pygame
from PIL import Image
from luma.core.interface.serial import spi
from luma.lcd.device import st7789
from battery_status import get_battery_status  # импортируем функцию
from log_reader import read_logs

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

# Text wrap
def wrap_text_to_screen(text, font, max_width, max_height, line_spacing=4):
    """
    Делит текст на строки, чтобы полностью помещался на экране.
    text       : исходная строка
    font       : pygame.font.Font
    max_width  : ширина экрана в пикселях
    max_height : высота экрана в пикселях
    line_spacing: расстояние между строками
    """
    words = text.split(' ')
    lines = []
    current = ""
    line_height = font.get_linesize()

    for word in words:
        test_line = (current + " " + word).strip()
        if font.size(test_line)[0] <= max_width:
            current = test_line
        else:
            lines.append(current)
            current = word

    if current:
        lines.append(current)

    # Обрезаем строки, если превышают высоту экрана
    max_lines = max_height // (line_height + line_spacing)
    return lines[:max_lines]

    # Остаток слов — в последнюю строку
    remaining_words = words[words.index(word):] if len(lines) == max_lines - 1 else []
    last_line = current + " " + " ".join(remaining_words)
    last_line = last_line.strip()
    lines.append(last_line)

    return lines[:max_lines]

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

        # ---Экран log---

        elif state == STATE_LOGS:
            surface.fill((255, 255, 255))  # белый фон

            try:
                # читаем следующую строку из генератора логов
                line = next(log_generator)
                current_log_line = line

                # выводим в консоль для отладки
                print(line)

            except StopIteration:
                current_log_line = "Лог завершён."

            # отрисовка на дисплее
            # Удаляем нулевые и другие неотображаемые символы
            # чистим строку от \x00
            safe_line = current_log_line.replace("\x00", "")

            # автоматический перенос
            lines = wrap_text_to_screen(
                safe_line,
                font,
                max_width=300,    # оставляем отступы слева и справа
                max_height=240,   # высота экрана
                line_spacing=4
            )

            y_start = 10
            for i, line in enumerate(lines):
                txt = font.render(line, True, (0, 0, 0))
                surface.blit(txt, (10, y_start + i * (font.get_linesize() + 4)))


            # выйти назад по кнопке
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
