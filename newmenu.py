# tile_menu.py
import os
import time
import pygame
import RPi.GPIO as GPIO
from PIL import Image
from luma.core.interface.serial import spi
from luma.lcd.device import st7789
from system_status import BatteryMonitor, WifiMonitor

# system_status
batt = BatteryMonitor(multiplier=2.0, charge_pin=21)
wifi = WifiMonitor(interface="wlan0")

# ---------- Настройки дисплея ----------
serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=16, bus_speed_hz=40000000)
device = st7789(serial, width=320, height=240, rotate=0)

# ---------- GPIO кнопки ----------
KEY_UP = 5
KEY_DOWN = 19
KEY_LEFT = 6
KEY_RIGHT = 26
KEY_OK = 13

GPIO.setmode(GPIO.BCM)
for pin in [KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_OK]:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

 # ---------- параметры интерфейса ----------
SCREEN_W, SCREEN_H = 320, 240
VISIBLE_H = 170   # активная высота матрицы
OFFSET_Y = (SCREEN_H - VISIBLE_H) // 2

COLS, ROWS = 4, 2
PADDING = 4
FOOTER_H = 25

# вычисляем размеры плиток внутри видимой зоны
AVAILABLE_H = VISIBLE_H - FOOTER_H - (ROWS + 1) * PADDING
TILE_W = (SCREEN_W - (COLS + 1) * PADDING) // COLS
TILE_H = AVAILABLE_H // ROWS

BG_COLOR = (30, 30, 30)
TILE_COLOR = (60, 60, 60)
SELECTED_COLOR = (255, 200, 0)
TEXT_COLOR = (255, 255, 255)
FOOTER_COLOR = (20, 20, 20)

pygame.init()
pygame.display.set_mode((1, 1))
surface = pygame.Surface((SCREEN_W, SCREEN_H))
clock = pygame.time.Clock()
font = pygame.font.Font(None, 20)
footer_font = pygame.font.Font(None, int(FOOTER_H-PADDING))

# ---------- Плитка ----------
class Tile:
    def __init__(self, label=None, icon=None, callback=None, name=None,
                 dynamic_label_func=None, dynamic_color_func=None):
        """
        label: текст плитки
        icon: pygame.Surface с иконкой
        callback: функция при нажатии
        name: отображаемое имя в футере
        dynamic_label_func: функция без аргументов, возвращающая текст
        dynamic_color_func: функция без аргументов, возвращающая цвет плитки (r,g,b)
        """
        self.label = label
        self.icon = icon
        self.callback = callback
        self.name = name
        self.dynamic_label_func = dynamic_label_func
        self.dynamic_color_func = dynamic_color_func

    def draw(self, surf, rect, selected=False):
        # --- вычисляем цвет ---
        if self.dynamic_color_func:
            try:
                color = self.dynamic_color_func(selected)
            except Exception:
                color = SELECTED_COLOR if selected else TILE_COLOR
        else:
            color = SELECTED_COLOR if selected else TILE_COLOR

        pygame.draw.rect(surf, color, rect, border_radius=5)

        # --- обновляем текст если надо ---
        if self.dynamic_label_func:
            try:
                self.label = str(self.dynamic_label_func())
            except Exception:
                self.label = "ERR"

        # --- контент ---
        if self.icon:
            icon_rect = self.icon.get_rect(center=rect.center)
            surf.blit(self.icon, icon_rect)
        elif self.label:
            txt = font.render(self.label, True, TEXT_COLOR)
            surf.blit(txt, (rect.centerx - txt.get_width() // 2,
                            rect.centery - txt.get_height() // 2))

# ---------- Экран плиток ----------
class TileScreen:
    def __init__(self, tiles):
        self.tiles = tiles
        self.selected = 0

    def draw(self, surf_full):
        surf_full.fill(BG_COLOR)

        # рисуем плитки в видимой области
        for i, tile in enumerate(self.tiles):
            col = i % COLS
            row = i // COLS
            x = PADDING + col * (TILE_W + PADDING)
            y = OFFSET_Y + PADDING + row * (TILE_H + PADDING)
            rect = pygame.Rect(x, y, TILE_W, TILE_H)
            tile.draw(surf_full, rect, selected=(i == self.selected))

        # футер внизу видимой зоны
        footer_rect = pygame.Rect(0, OFFSET_Y + VISIBLE_H - FOOTER_H, SCREEN_W, FOOTER_H)
        pygame.draw.rect(surf_full, FOOTER_COLOR, footer_rect)

        # выводим название выделенной плитки
        current_tile = self.tiles[self.selected]
        if current_tile.label:
            footer_text = current_tile.label
        elif current_tile.icon:  # если плитка с иконкой, можно задать отдельное имя
            # например, можно хранить name в Tile
            footer_text = getattr(current_tile, "name", "Icon")
        else:
            footer_text = ""

        hint_surf = footer_font.render(footer_text, True, (180, 180, 180))
        hint_rect = hint_surf.get_rect(center=footer_rect.center)
        surf_full.blit(hint_surf, hint_rect)



    def handle_input(self, direction):
        row_len = COLS
        if direction == "LEFT" and self.selected % row_len > 0:
            self.selected -= 1
        elif direction == "RIGHT" and self.selected % row_len < row_len - 1 and self.selected + 1 < len(self.tiles):
            self.selected += 1
        elif direction == "UP" and self.selected >= row_len:
            self.selected -= row_len
        elif direction == "DOWN" and self.selected < len(self.tiles) - row_len:
            self.selected += row_len
        elif direction == "OK":
            tile = self.tiles[self.selected]
            if tile.callback:
                tile.callback()

# ---------- заглушки действий ----------
def stub_action(name):
    def _():
        print(f"[ACTION] {name} clicked!")
    return _

def battery_text():
    """Возвращает строку для динамической плитки"""
    voltage = batt.get_voltage()
    return f"{voltage:.2f}V"

def battery_color(selected=False):
    """Меняет цвет плитки в зависимости от зарядки"""
    charging = batt.is_charging()
    if charging:
        # зелёный при зарядке
        return (0, 200, 0) if not selected else (0, 255, 0)
    else:
        # красный при разрядке
        return (180, 50, 50) if not selected else (255, 80, 80)

# загрузка иконок
def load_icon(filename, size=(32, 32)):
    """
    filename: имя файла иконки, например "wifi.png"
    size: tuple (width, height)
    """
    base_path = os.path.dirname(os.path.abspath(__file__))  # папка скрипта
    full_path = os.path.join(base_path, "icons", filename)  # папка icons

    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Icon not found: {full_path}")

    img = pygame.image.load(full_path).convert_alpha()
    img = pygame.transform.smoothscale(img, size)
    return img

# иконки
OFF_icon = load_icon("off_ico.png")
REB_icon = load_icon("reboot_ico.png")
LOG_icon = load_icon("log_ico.png")
SET_icon = load_icon("settings_ico.png")
FLASH_icon = load_icon("flash_ico.png")
READMAC_icon = load_icon("readmac_ico.png")

# ---------- Создание плиток главного меню ----------
tiles = [
    Tile(icon=OFF_icon, callback=stub_action("OFF"), name="Выключение"),
    Tile(icon=FLASH_icon, callback=stub_action("FLASH"), name="Меню прошивки"),
    Tile(icon= LOG_icon, callback=stub_action("LOG"), name="Чтение лога"),
    Tile(label="WIFI", callback=stub_action("WIFI"), name="Инф. о сети WiFi"),
    Tile(icon=REB_icon, callback=stub_action("REBOOT"), name="Перезагрузка"),
    Tile(icon=READMAC_icon, callback=stub_action("READ MAC"), name="Считать MAC"),
    Tile(icon=SET_icon, callback=stub_action("SET"), name="Настройки"),
    Tile(dynamic_label_func=battery_text, dynamic_color_func=battery_color, callback=stub_action("BATT"), name="Инф. о питании")
]

menu = TileScreen(tiles)



# ---------- GPIO логика ----------
PIN_TO_KEY = {
    KEY_UP: "UP",
    KEY_DOWN: "DOWN",
    KEY_LEFT: "LEFT",
    KEY_RIGHT: "RIGHT",
    KEY_OK: "OK"
}

last_pin_state = {pin: True for pin in PIN_TO_KEY.keys()}
last_event_time = {pin: 0 for pin in PIN_TO_KEY.keys()}
DEBOUNCE_SEC = 0.12

def poll_buttons():
    now = time.time()
    for pin, name in PIN_TO_KEY.items():
        state = GPIO.input(pin)
        last = last_pin_state[pin]
        if last and not state:
            if now - last_event_time[pin] >= DEBOUNCE_SEC:
                last_event_time[pin] = now
                last_pin_state[pin] = state
                return name
        if not last and state:
            last_pin_state[pin] = state
    return None

def wait_release(pin, timeout=1.0):
    start = time.time()
    while GPIO.input(pin) == GPIO.LOW and (time.time() - start) < timeout:
        time.sleep(0.01)

# ---------- Главный цикл ----------
def main():
    try:
        while True:
            key = poll_buttons()
            if key:
                if key == "OK":
                    menu.handle_input("OK")
                    wait_release(KEY_OK)
                else:
                    menu.handle_input(key)
                time.sleep(0.05)

            surface.fill((0, 0, 0))
            menu.draw(surface)

            raw_str = pygame.image.tostring(surface, "RGB")
            img = Image.frombytes("RGB", (SCREEN_W, SCREEN_H), raw_str)
            device.display(img)

            clock.tick(30)

    finally:
        GPIO.cleanup()
        pygame.quit()

if __name__ == "__main__":
    main()
