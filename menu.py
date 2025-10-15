import os
import time
import logging
import RPi.GPIO as GPIO
import pygame
from PIL import Image
from luma.core.interface.serial import spi
from luma.lcd.device import st7789
from esp_flasher_class import ESPFlasher
from firmwares_download import download_latest_firmware
from log_reader import LogManager

# --- Настройка flasher ---
flasher = ESPFlasher(port="/dev/ttyS0", flash_dir="/root/smart_programmer/firmware")

# --- GPIO ---
buttons = {"up":5,"down":19,"left":6,"right":26,"reset":13}
GPIO.setmode(GPIO.BCM)
for pin in buttons.values():
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# --- Pygame / дисплей ---
pygame.init()
WIDTH, HEIGHT = 320, 240
surface = pygame.Surface((WIDTH, HEIGHT))
clock = pygame.time.Clock()
font = pygame.font.Font(None, 22)

serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=16, bus_speed_hz=40000000)
device = st7789(serial, width=WIDTH, height=HEIGHT, rotate=0)

# --- Лог менеджер ---
log_manager = LogManager(font, max_width=300, max_height=170, line_spacing=4)

# --- Базовые классы GUI ---
class Screen:
    def __init__(self):
        self.selected = 0

    def handle_input(self):
        pass

    def draw(self, surface):
        pass

# --- Главное меню ---
class MainMenu(Screen):
    def __init__(self):
        super().__init__()
        self.items = [("burn","icons/burn.png"),
                      ("download","icons/download.png"),
                      ("settings","icons/settings.png"),
                      ("info","icons/info.png")]
        self.icons = []
        for name, path in self.items:
            icon = pygame.image.load(path)
            icon = pygame.transform.smoothscale(icon, (24,24))
            self.icons.append((name, icon))
        self.positions = [(100,70),(180,70),(100,150),(180,150)]

    def handle_input(self):
        global current_screen
        if GPIO.input(buttons["up"]) == GPIO.LOW and self.selected >= 2: self.selected -= 2
        elif GPIO.input(buttons["down"]) == GPIO.LOW and self.selected <= 1: self.selected += 2
        elif GPIO.input(buttons["left"]) == GPIO.LOW and self.selected in [1,3]: self.selected -=1
        elif GPIO.input(buttons["right"]) == GPIO.LOW and self.selected in [0,2]: self.selected +=1
        elif GPIO.input(buttons["reset"]) == GPIO.LOW:
            choice = self.icons[self.selected][0]
            if choice=="burn":
                current_screen = BurnMenu()
            elif choice=="download":
                log_manager.start(port="/dev/ttyS0", baud=115200)
                current_screen = LogsScreen(log_manager)
            elif choice=="info":
                pass
            time.sleep(0.2)

    def draw(self, surface):
        surface.fill((255,255,0))
        for i, (name, icon) in enumerate(self.icons):
            x,y = self.positions[i]
            surface.blit(icon,(x,y))
            if i==self.selected:
                pygame.draw.rect(surface,(0,0,0),(x-2,y-2,28,28),2)

# --- Подменю Burn ---
class BurnMenu(Screen):
    def __init__(self):
        super().__init__()
        base_path = "/root/smart_programmer/firmware"
        # список папок с версиями прошивок
        self.folders = [f for f in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, f))]
        self.folders.sort()
        self.menu_items = ["Download"] + self.folders
        self.scroll_offset = 0
        self.VISIBLE_LINES = 4
        self.y_start = 50

    def handle_input(self):
        global current_screen
        if GPIO.input(buttons["up"]) == GPIO.LOW:
            self.selected = (self.selected - 1) % len(self.menu_items)
            if self.selected < self.scroll_offset:
                self.scroll_offset = self.selected
            time.sleep(0.05)

        elif GPIO.input(buttons["down"]) == GPIO.LOW:
            self.selected = (self.selected + 1) % len(self.menu_items)
            if self.selected >= self.scroll_offset + self.VISIBLE_LINES:
                self.scroll_offset = self.selected - self.VISIBLE_LINES + 1
            time.sleep(0.05)

        elif GPIO.input(buttons["left"]) == GPIO.LOW:
            current_screen = MainMenu()
            time.sleep(0.05)

        elif GPIO.input(buttons["reset"]) == GPIO.LOW:
            chosen_item = self.menu_items[self.selected]
            logging.info(f"Выбран пункт: {chosen_item}")

            if chosen_item == "Download":
                local_file = download_latest_firmware()
                if local_file:
                    logging.info(f"Файл скачан: {local_file}")
                else:
                    logging.error("Скачивание не удалось")
            else:
                # Переход на экран выбора варианта прошивки
                firmware_version_path = os.path.join(flasher.flash_dir, chosen_item)
                if os.path.exists(firmware_version_path):
                    current_screen = FlashVariant(firmware_version_path)
                else:
                    logging.error(f"Папка с прошивкой не найдена: {firmware_version_path}")

            # Ждём отпускания кнопки
            while GPIO.input(buttons["reset"]) == GPIO.LOW:
                time.sleep(0.05)

    def draw(self, surface):
        surface.fill((255, 255, 0))
        visible_items = self.menu_items[self.scroll_offset:self.scroll_offset + self.VISIBLE_LINES]
        for i, item in enumerate(visible_items):
            color = (255, 0, 0) if (self.scroll_offset + i) == self.selected else (0, 0, 0)
            surface.blit(font.render(item, True, color), (40, self.y_start + i * 40))

# --- Подменю Flash ---
class FlashVariant(Screen):
    def __init__(self, version_path):
        super().__init__()
        self.version_path = version_path  # путь к папке с выбранной версией прошивки

        # пока вручную список вариантов, позже можно динамически через os.listdir
        #self.menu_items = ["battery_sw", "battery_lr", "sw", "master_lr", "repeater_lr"]
        self.menu_items = self.firmware_list(version_path)

        self.scroll_offset = 0
        self.VISIBLE_LINES = 4
        self.y_start = 50

    def firmware_list(self, path):
        suffix = "_0x9000.bin"
        files = [
            f[:-len(suffix)]
            for f in os.listdir(path)
            if f.endswith(suffix) and os.path.isfile(os.path.join(path, f))
        ]
        return sorted(files)


    def handle_input(self):
        global current_screen
        if GPIO.input(buttons["up"]) == GPIO.LOW:
            self.selected = (self.selected - 1) % len(self.menu_items)
            if self.selected < self.scroll_offset:
                self.scroll_offset = self.selected
            time.sleep(0.05)

        elif GPIO.input(buttons["down"]) == GPIO.LOW:
            self.selected = (self.selected + 1) % len(self.menu_items)
            if self.selected >= self.scroll_offset + self.VISIBLE_LINES:
                self.scroll_offset = self.selected - self.VISIBLE_LINES + 1
            time.sleep(0.05)

        elif GPIO.input(buttons["left"]) == GPIO.LOW:
            # возвращаемся к меню версий
            current_screen = BurnMenu()
            time.sleep(0.05)

        elif GPIO.input(buttons["reset"]) == GPIO.LOW:
            chosen_item = self.menu_items[self.selected]
            logging.info(f"Выбран вариант прошивки: {chosen_item}")

            # формируем полный путь к бинарнику
            firmware_file = os.path.join(self.version_path, f"{chosen_item}_a_0x9000.bin")
            logging.info(f"Путь к файлу: {firmware_file}")

            if os.path.exists(firmware_file):
                result = flasher.flash_firmware(firmware_file)
                if result:
                    logging.info("✅ Прошивка завершена успешно!")
                else:
                    logging.error("❌ Прошивка завершилась с ошибкой")
            else:
                logging.error(f"❌ Файл прошивки не найден: {firmware_file}")

            # ждём отпускания кнопки
            while GPIO.input(buttons["reset"]) == GPIO.LOW:
                time.sleep(0.05)

    def draw(self, surface):
        surface.fill((255, 255, 0))
        visible_items = self.menu_items[self.scroll_offset:self.scroll_offset + self.VISIBLE_LINES]
        for i, item in enumerate(visible_items):
            color = (255, 0, 0) if (self.scroll_offset + i) == self.selected else (0, 0, 0)
            surface.blit(font.render(item, True, color), (40, self.y_start + i * 40))


# --- Экран логов ---
class LogsScreen(Screen):
    def __init__(self, log_manager):
        super().__init__()
        self.log_manager = log_manager
        self.y_start = 35

    def handle_input(self):
        global current_screen
        # Прокрутка
        if GPIO.input(buttons["up"]) == GPIO.LOW:
            self.log_manager.scroll_up()
            time.sleep(0.05)
        elif GPIO.input(buttons["down"]) == GPIO.LOW:
            self.log_manager.scroll_down()
            time.sleep(0.05)
        elif GPIO.input(buttons["right"]) == GPIO.LOW:
            self.log_manager.scroll_to_end()
            time.sleep(0.05)
        elif GPIO.input(buttons["left"]) == GPIO.LOW:
            current_screen = MainMenu()
            time.sleep(0.2)
        # Добавляем новые строки из генератора
        try:
            line = next(self.log_manager.generator)
            if line:
                self.log_manager.add_line(line)
        except StopIteration:
            pass

    def draw(self, surface):
        surface.fill((255,255,0))
        visible_lines, line_height = self.log_manager.get_visible()
        for i, (line_text, is_indent) in enumerate(visible_lines):
            x_offset = 10 + (20 if is_indent else 0)
            color = (255,0,0) if self.log_manager.is_alert_line(line_text) else (0,0,0)
            surface.blit(font.render(line_text, True, color), (x_offset, self.y_start + i*line_height))

# --- Основной цикл ---
current_screen = MainMenu()

try:
    running = True
    while running:
        current_screen.handle_input()
        current_screen.draw(surface)
        raw_str = pygame.image.tostring(surface,"RGB")
        img = Image.frombytes("RGB",(WIDTH,HEIGHT),raw_str)
        device.display(img)
        clock.tick(20)
finally:
    GPIO.cleanup()
