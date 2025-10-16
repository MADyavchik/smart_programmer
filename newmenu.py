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
font = pygame.font.Font(None, 22)

serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=16, bus_speed_hz=40000000)
device = st7789(serial, width=WIDTH, height=HEIGHT, rotate=0)

# --- Лог менеджер ---
log_manager = LogManager(font, max_width=300, max_height=170, line_spacing=4)

# --- Базовые классы GUI ---
class Screen:
    def handle_input(self):
        pass

    def draw(self, surface):
        pass

# --- Sprite для пункта меню ---
class MenuItem(pygame.sprite.Sprite):
    def __init__(self, text, font, x, y, selected=False):
        super().__init__()
        self.font = font
        self.text = text
        self.selected = selected
        self.x = x
        self.y = y
        self.update_image()

    def update_image(self):
        color = (255, 0, 0) if self.selected else (0, 0, 0)
        self.image = self.font.render(self.text, True, color)
        self.rect = self.image.get_rect(topleft=(self.x, self.y))

    def set_selected(self, selected):
        self.selected = selected
        self.update_image()

    def move_to(self, y):
        self.y = y
        self.rect.y = y

# --- Список через спрайты ---
class ListScreen(Screen):
    def __init__(self, items):
        self.items = items
        self.sprite_group = pygame.sprite.Group()
        self.selected_index = 0
        self.scroll_offset = 0
        self.line_height = font.get_height() + 4
        self.visible_lines = VISIBLE_HEIGHT // self.line_height
        self.update_sprites()

    def update_sprites(self):
        self.sprite_group.empty()
        start = self.scroll_offset
        end = min(len(self.items), start + self.visible_lines)
        y_start = (HEIGHT - VISIBLE_HEIGHT) // 2
        for i, item_text in enumerate(self.items[start:end]):
            selected = (start + i) == self.selected_index
            y = y_start + i * self.line_height
            sprite = MenuItem(item_text, font, 40, y, selected)
            self.sprite_group.add(sprite)

    def handle_list_input(self, on_select=None, on_back=None):
        if GPIO.input(buttons["up"]) == GPIO.LOW:
            self.selected_index = (self.selected_index - 1) % len(self.items)
            if self.selected_index < self.scroll_offset:
                self.scroll_offset = self.selected_index
            self.update_sprites()
            time.sleep(0.1)
        elif GPIO.input(buttons["down"]) == GPIO.LOW:
            self.selected_index = (self.selected_index + 1) % len(self.items)
            if self.selected_index >= self.scroll_offset + self.visible_lines:
                self.scroll_offset = self.selected_index - self.visible_lines + 1
            self.update_sprites()
            time.sleep(0.1)
        elif GPIO.input(buttons["left"]) == GPIO.LOW and on_back:
            on_back()
            time.sleep(0.1)
        elif GPIO.input(buttons["reset"]) == GPIO.LOW and on_select:
            on_select(self.items[self.selected_index])
            while GPIO.input(buttons["reset"]) == GPIO.LOW:
                time.sleep(0.05)

    def draw_list(self, surface):
        surface.fill((255, 255, 0))
        self.sprite_group.draw(surface)

# --- Главное меню ---
class MainMenu(Screen):
    def __init__(self):
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
        self.selected = 0

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
            x, y = self.positions[i]
            surface.blit(icon, (x, y))
            if i == self.selected:
                pygame.draw.rect(surface, (0,0,0), (x-2,y-2,28,28), 2)

# --- Подменю Burn ---
class BurnMenu(ListScreen):
    def __init__(self):
        base_path = "/root/smart_programmer/firmware"
        folders = [f for f in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, f))]
        folders.sort()
        super().__init__(["Download"] + folders)

    def handle_input(self):
        global current_screen
        def select(item):
            if item == "Download":
                local = download_latest_firmware()
                logging.info(f"Скачан: {local}" if local else "Ошибка скачивания")
            else:
                version_path = os.path.join(flasher.flash_dir, item)
                if os.path.exists(version_path):
                    current_screen = FlashVariant(version_path)

        def go_back():
            global current_screen
            current_screen = MainMenu()

        self.handle_list_input(on_select=select, on_back=go_back)

    def draw(self, surface):
        # Просто рисуем спрайты списка
        self.draw_list(surface)

# --- Подменю Flash ---
class FlashVariant(ListScreen):
    def __init__(self, version_path):
        self.version_path = version_path
        items = self.firmware_list(version_path)
        super().__init__(items)

    def firmware_list(self, path):
        suffix = "_0x9000.bin"
        return sorted([f[:-len(suffix)] for f in os.listdir(path) if f.endswith(suffix)])

    def handle_input(self):
        global current_screen
        def select(item):
            firmware_file = os.path.join(self.version_path, f"{item}_0x9000.bin")
            if os.path.exists(firmware_file):
                result = flasher.flash_firmware(firmware_file)
                logging.info("✅ Успех" if result else "❌ Ошибка")
            else:
                logging.error("❌ Нет файла")
        def go_back():
            global current_screen
            current_screen = BurnMenu()
        self.handle_list_input(on_select=select, on_back=go_back)

# --- Экран логов ---
class LogsScreen(Screen):
    def __init__(self, log_manager):
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
