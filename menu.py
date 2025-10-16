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
VISIBLE_HEIGHT = 170
surface = pygame.Surface((WIDTH, HEIGHT))
clock = pygame.time.Clock()
font = pygame.font.Font(None, 24)

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

    def draw_limited(self, surface, draw_fn):
        """
        Рисуем только в центральной зоне:
        сверху и снизу по 35 пикселей остаётся пусто.
        """
        temp_surface = pygame.Surface(surface.get_size())
        draw_fn(temp_surface)

        offset_top = (HEIGHT - VISIBLE_HEIGHT) // 2

        surface.blit(
            temp_surface,
            (0, offset_top),
            area=pygame.Rect(0, offset_top, WIDTH, VISIBLE_HEIGHT)
        )

    def draw(self, surface):
        pass

class ListScreen(Screen):
    def __init__(self, items, y_start=30, line_spacing=8):
        super().__init__()
        self.menu_items = items
        self.y_start = y_start
        self.selected = 0
        self.scroll_offset = 0

        font_height = font.get_height()
        self.line_height = font_height + line_spacing
        self.VISIBLE_LINES = VISIBLE_HEIGHT // self.line_height

    def handle_list_input(self, on_select=None, on_back=None):
        if GPIO.input(buttons["up"]) == GPIO.LOW:
            old = self.selected
            self.selected = (self.selected - 1) % len(self.menu_items)
            if old == 0 and self.selected == len(self.menu_items) - 1:
                self.scroll_offset = max(0, len(self.menu_items) - self.VISIBLE_LINES)
            elif self.selected < self.scroll_offset:
                self.scroll_offset = self.selected
            time.sleep(0.1)

        elif GPIO.input(buttons["down"]) == GPIO.LOW:
            old = self.selected
            self.selected = (self.selected + 1) % len(self.menu_items)
            if old == len(self.menu_items) - 1 and self.selected == 0:
                self.scroll_offset = 0
            elif self.selected >= self.scroll_offset + self.VISIBLE_LINES:
                self.scroll_offset = self.selected - self.VISIBLE_LINES + 1
            time.sleep(0.1)

        elif GPIO.input(buttons["left"]) == GPIO.LOW and on_back:
            on_back()
            time.sleep(0.1)

        elif GPIO.input(buttons["reset"]) == GPIO.LOW and on_select:
            on_select(self.menu_items[self.selected])
            while GPIO.input(buttons["reset"]) == GPIO.LOW:
                time.sleep(0.05)

    def draw_list(self, surface):
        def _draw(surf):
            surf.fill((255, 255, 0))
            visible_items = self.menu_items[self.scroll_offset : self.scroll_offset + self.VISIBLE_LINES]
            for i, item in enumerate(visible_items):
                color = (255, 0, 0) if (self.scroll_offset + i) == self.selected else (0, 0, 0)
                y = self.y_start + i * self.line_height
                surf.blit(font.render(item, True, color), (40, y))

        self.draw_limited(surface, _draw)
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
        def _draw(surf):
            surf.fill((255,255,0))
            for i, (name, icon) in enumerate(self.icons):
                x, y = self.positions[i]
                surf.blit(icon, (x, y))
                if i == self.selected:
                    pygame.draw.rect(surf, (0,0,0), (x-2,y-2,28,28), 2)

        self.draw_limited(surface, _draw)

# --- Подменю Burn ---
class BurnMenu(ListScreen):
    def __init__(self):
        base_path = "/root/smart_programmer/firmware"
        folders = [f for f in os.listdir(base_path)
                   if os.path.isdir(os.path.join(base_path, f))]
        folders.sort()
        super().__init__(["Download"] + folders)

    def handle_input(self):


        def select(item):
            global current_screen
            if item == "Download":
                local = download_latest_firmware()
                if local:
                    logging.info(f"Скачан: {local}")
                else:
                    logging.error("Ошибка скачивания")
            else:
                version_path = os.path.join(flasher.flash_dir, item)
                if os.path.exists(version_path):
                    current_screen = FlashVariant(version_path)

        def go_back():
            global current_screen
            current_screen = MainMenu()

        self.handle_list_input(on_select=select, on_back=go_back)

    def draw(self, surface):
        self.draw_list(surface)

# --- Подменю Flash ---
class FlashVariant(ListScreen):
    def __init__(self, version_path):
        self.version_path = version_path
        items = self.firmware_list(version_path)
        super().__init__(items)

    def firmware_list(self, path):
        suffix = "_0x9000.bin"
        return sorted([
            f[:-len(suffix)]
            for f in os.listdir(path)
            if f.endswith(suffix)
        ])

    def handle_input(self):
        global current_screen

        def select(item):
            firmware_file = os.path.join(self.version_path, f"{item}_0x9000.bin")
            if os.path.exists(firmware_file):
                result = flasher.flash_firmware(firmware_file)
                if result:
                    logging.info("✅ Успех")
                else:
                    logging.error("❌ Ошибка")
            else:
                logging.error("❌ Нет файла")

        def go_back():
            global current_screen
            current_screen = BurnMenu()

        self.handle_list_input(on_select=select, on_back=go_back)

    def draw(self, surface):
        self.draw_list(surface)

# --- Экран логов ---
class LogsScreen(Screen):
    def __init__(self, log_manager):
        super().__init__()
        self.log_manager = log_manager
        self.y_start = 35

    def handle_input(self):
        global current_screen
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
        try:
            line = next(self.log_manager.generator)
            if line:
                self.log_manager.add_line(line)
        except StopIteration:
            pass

    def draw(self, surface):
        def _draw(surf):
            surf.fill((255,255,0))
            visible_lines, line_height = self.log_manager.get_visible()
            for i, (line_text, is_indent) in enumerate(visible_lines):
                x_offset = 10 + (20 if is_indent else 0)
                color = (255,0,0) if self.log_manager.is_alert_line(line_text) else (0,0,0)
                surf.blit(font.render(line_text, True, color), (x_offset, self.y_start + i*line_height))

        self.draw_limited(surface, _draw)

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
