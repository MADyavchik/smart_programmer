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

# --- Настройка ---
flasher = ESPFlasher(port="/dev/ttyS0", flash_dir="/root/smart_programmer/firmware")
buttons = {"up":5,"down":19,"left":6,"right":26,"reset":13}
GPIO.setmode(GPIO.BCM)
for pin in buttons.values():
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

pygame.init()
WIDTH, HEIGHT = 320, 240
surface = pygame.Surface((WIDTH, HEIGHT))
clock = pygame.time.Clock()
font = pygame.font.Font(None, 22)
serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=16, bus_speed_hz=40000000)
device = st7789(serial, width=WIDTH, height=HEIGHT, rotate=0)
log_manager = LogManager(font, max_width=300, max_height=170, line_spacing=4)

# --- Базовый класс экрана ---
class Screen:
    LINE_HEIGHT = 25
    def handle_input(self):
        pass
    def draw(self, surface):
        pass

# --- Универсальный экран меню ---
class MenuScreen(Screen):
    def __init__(self, items_dict, title=None):
        self.items = list(items_dict.keys())
        self.actions = [items_dict[k] for k in self.items]
        self.selected_index = 0
        self.title = title

    def handle_input(self):
        global current_screen
        if GPIO.input(buttons["up"]) == GPIO.LOW:
            self.selected_index = (self.selected_index - 1) % len(self.items)
            time.sleep(0.1)
        elif GPIO.input(buttons["down"]) == GPIO.LOW:
            self.selected_index = (self.selected_index + 1) % len(self.items)
            time.sleep(0.1)
        elif GPIO.input(buttons["left"]) == GPIO.LOW:
            current_screen = main_menu if self.title != "Main" else self
            time.sleep(0.1)
        elif GPIO.input(buttons["reset"]) == GPIO.LOW:
            action = self.actions[self.selected_index]
            if action:
                action()
            while GPIO.input(buttons["reset"]) == GPIO.LOW:
                time.sleep(0.05)

    def draw(self, surface):
        surface.fill((0,0,0))
        y_start = 35
        if self.title:
            t_surf = font.render(self.title, True, (255,255,255))
            surface.blit(t_surf, (WIDTH//2 - t_surf.get_width()//2, 5))
        for i, item in enumerate(self.items):
            y = y_start + i * self.LINE_HEIGHT
            color = (255,0,0) if i == self.selected_index else (255,255,255)
            surface.blit(font.render(item, True, color), (10, y))
            if i == self.selected_index:
                pygame.draw.rect(surface, (255,0,0), (0, y, WIDTH, self.LINE_HEIGHT), 2)

# --- Логи ---
class LogScreen(Screen):
    def __init__(self):
        self.y_start = 35
    def handle_input(self):
        global current_screen
        if GPIO.input(buttons["up"]) == GPIO.LOW: log_manager.scroll_up(); time.sleep(0.05)
        elif GPIO.input(buttons["down"]) == GPIO.LOW: log_manager.scroll_down(); time.sleep(0.05)
        elif GPIO.input(buttons["right"]) == GPIO.LOW: log_manager.scroll_to_end(); time.sleep(0.05)
        elif GPIO.input(buttons["left"]) == GPIO.LOW: current_screen = main_menu; time.sleep(0.2)
        try:
            line = next(log_manager.generator)
            if line:
                log_manager.add_line(line)
        except StopIteration:
            pass
    def draw(self, surface):
        surface.fill((0,0,0))
        visible, lh = log_manager.get_visible()
        for i, (text, indent) in enumerate(visible):
            x = 10 + (20 if indent else 0)
            color = (255,0,0) if log_manager.is_alert_line(text) else (255,255,255)
            surface.blit(font.render(text, True, color), (x, self.y_start + i*lh))

# --- Действия меню ---
def download_firmware(_=None):
    local = download_latest_firmware()
    logging.info(f"Скачан: {local}" if local else "Ошибка скачивания")

def flash_file(path):
    if os.path.exists(path):
        result = flasher.flash_firmware(path)
        logging.info("✅ Успех" if result else "❌ Ошибка")
    else:
        logging.error("❌ Нет файла")

def build_flash_actions(version_path):
    files = sorted([f[:-len("_0x9000.bin")] for f in os.listdir(version_path) if f.endswith("_0x9000.bin")])
    return {f: lambda f=f: flash_file(os.path.join(version_path, f+"_0x9000.bin")) for f in files}

def open_burn_menu():
    global current_screen
    folders = sorted([f for f in os.listdir(flasher.flash_dir) if os.path.isdir(os.path.join(flasher.flash_dir,f))])
    items = {"Download": download_firmware}
    items.update({f: lambda f=f: open_flash_menu(f) for f in folders})
    current_screen = MenuScreen(items, "Burn Menu")

def open_flash_menu(folder):
    global current_screen
    version_path = os.path.join(flasher.flash_dir, folder)
    current_screen = MenuScreen(build_flash_actions(version_path), f"Flash {folder}")

def open_logs():
    global current_screen
    current_screen = LogScreen()

# --- Главное меню ---
MENU_STRUCTURE = {
    "Main": {
        "Burn": open_burn_menu,
        "Download Logs": open_logs,
        "Settings": None,
        "Info": None
    }
}
main_menu = MenuScreen(MENU_STRUCTURE["Main"], "Main")
current_screen = main_menu

# --- Основной цикл ---
try:
    running = True
    while running:
        current_screen.handle_input()
        current_screen.draw(surface)
        raw_str = pygame.image.tostring(surface,"RGB")
        device.display(Image.frombytes("RGB",(WIDTH,HEIGHT),raw_str))
        clock.tick(30)
finally:
    GPIO.cleanup()
