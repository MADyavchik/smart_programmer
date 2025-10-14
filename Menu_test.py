# --- main_menu.py ---
import os
import time
import logging
import RPi.GPIO as GPIO
import pygame
from PIL import Image
from luma.core.interface.serial import spi
from luma.lcd.device import st7789
from log_reader import LogManager
from esp_flasher_class import ESPFlasher

flasher = ESPFlasher(port="/dev/ttyS0", flash_dir="/root/smart_programmer/Прошивки")

# --- GPIO и кнопки ---
buttons = {"up":5,"down":19,"left":6,"right":26,"reset":13}
GPIO.setmode(GPIO.BCM)
for pin in buttons.values():
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)



# --- Pygame и дисплей ---
pygame.init()
width, height = 320, 240
surface = pygame.Surface((width, height))
clock = pygame.time.Clock()
font = pygame.font.Font(None, 22)

serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=16, bus_speed_hz=40000000)
device = st7789(serial, width=width, height=height, rotate=0)

# --- Лог менеджер ---
log_manager = LogManager(font, max_width=300, max_height=170, line_spacing=4)

# --- Главное меню ---
STATE_MAIN = "main"
STATE_BURN = "burn_menu"
STATE_INFO = "info"
STATE_LOGS = "logs"
state = STATE_MAIN

selected = 0
folders = []

# --- Иконки ---
icon_files = [
    ("burn","icons/burn.png"),
    ("download","icons/download.png"),
    ("settings","icons/settings.png"),
    ("info","icons/info.png"),
]
icons = []
for name, path in icon_files:
    icon = pygame.image.load(path)
    icon = pygame.transform.smoothscale(icon,(24,24))
    icons.append((name, icon))
positions = [(100,70),(180,70),(100,150),(180,150)]

# --- Основной цикл ---
try:
    running = True
    while running:
        surface.fill((255,255,0))  # фон желтый

        # --- Главное меню ---
        if state == STATE_MAIN:
            for i, (name, icon) in enumerate(icons):
                x,y = positions[i]
                surface.blit(icon,(x,y))
                if i==selected:
                    pygame.draw.rect(surface,(0,0,0),(x-2,y-2,28,28),2)

            # --- Кнопки ---
            if GPIO.input(buttons["up"])==GPIO.LOW and selected>=2: selected-=2
            elif GPIO.input(buttons["down"])==GPIO.LOW and selected<=1: selected+=2
            elif GPIO.input(buttons["left"])==GPIO.LOW and selected in [1,3]: selected-=1
            elif GPIO.input(buttons["right"])==GPIO.LOW and selected in [0,2]: selected+=1
            elif GPIO.input(buttons["reset"])==GPIO.LOW:
                choice = icons[selected][0]
                if choice=="burn":
                    state=STATE_BURN
                    selected=0
                    base_path="/root/smart_programmer/Прошивки"
                    folders=[f for f in os.listdir(base_path) if os.path.isdir(os.path.join(base_path,f))]
                    folders.sort()
                    menu_items = ["Download"] + folders
                    time.sleep(0.2)
                elif choice=="info":
                    state=STATE_INFO
                    time.sleep(0.2)
                elif choice=="download":
                    state=STATE_LOGS
                    log_manager.start(port="/dev/ttyS0",baud=115200)
                    time.sleep(0.2)

        # --- Подменю Burn ---
        elif state == STATE_BURN:
            y_start = 50
            for i, item in enumerate(menu_items):
                color = (255, 0, 0) if i == selected else (0, 0, 0)
                surface.blit(font.render(item, True, color), (40, y_start + i*40))

            # --- Навигация ---
            if GPIO.input(buttons["up"]) == GPIO.LOW and menu_items:
                selected = (selected - 1) % len(menu_items)
                time.sleep(0.2)
            elif GPIO.input(buttons["down"]) == GPIO.LOW and menu_items:
                selected = (selected + 1) % len(menu_items)
                time.sleep(0.2)
            elif GPIO.input(buttons["left"]) == GPIO.LOW:
                state = STATE_MAIN
                selected = 0
                time.sleep(0.2)
            elif GPIO.input(buttons["reset"]) == GPIO.LOW and menu_items:
                chosen_item = menu_items[selected]
                logging.info(f"Выбран пункт: {chosen_item}")

                if chosen_item == "Download":
                    # Запускаем процесс скачивания с сервера
                    logging.info("🔽 Запуск скачивания прошивки с сервера...")
                    # Тут будет функция, которая загружает прошивку
                    #download_latest_firmware()  # <-- твоя функция для скачивания
                else:
                    # Запуск прошивки через класс
                    firmware_path = os.path.join(flasher.flash_dir, chosen_item)
                    if os.path.exists(firmware_path):
                        result = flasher.flash_firmware(chosen_item)
                        if result:
                            logging.info("Прошивка успешно завершена!")
                        else:
                            logging.error("Прошивка завершилась с ошибкой.")
                    else:
                        logging.error(f"Папка прошивки не найдена: {firmware_path}")

                while GPIO.input(buttons["reset"]) == GPIO.LOW:
                    time.sleep(0.05)

            time.sleep(0.2)

        # --- Экран логов ---
        elif state == STATE_LOGS:
            try:
                line = next(log_manager.generator)
                if line is not None:
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


        # --- Обновление дисплея ---
        raw_str=pygame.image.tostring(surface,"RGB")
        img=Image.frombytes("RGB",(width,height),raw_str)
        device.display(img)

        clock.tick(10)

finally:
    GPIO.cleanup()
