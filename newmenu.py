# tile_menu.py
import os
import time
import pygame
import RPi.GPIO as GPIO
from PIL import Image
from luma.core.interface.serial import spi
from luma.lcd.device import st7789

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
VISIBLE_H = 170
COLS, ROWS = 4, 2
PADDING = 4
TILE_SIZE = (SCREEN_W - (COLS + 1) * PADDING) // COLS

BG_COLOR = (30, 30, 30)
TILE_COLOR = (60, 60, 60)
SELECTED_COLOR = (255, 200, 0)
TEXT_COLOR = (255, 255, 255)
FOOTER_COLOR = (20, 20, 20)

pygame.init()
surface = pygame.Surface((SCREEN_W, SCREEN_H))
clock = pygame.time.Clock()
font = pygame.font.Font(None, 20)
footer_font = pygame.font.Font(None, 14)

# ---------- Плитка ----------
class Tile:
    def __init__(self, label, callback=None):
        self.label = label
        self.callback = callback

    def draw(self, surf, rect, selected=False):
        color = SELECTED_COLOR if selected else TILE_COLOR
        pygame.draw.rect(surf, color, rect, border_radius=10)
        lines = self.label.split("\n")
        for i, line in enumerate(lines):
            txt = font.render(line, True, TEXT_COLOR)
            total_h = len(lines) * txt.get_height()
            y_offset = rect.y + (rect.h - total_h) // 2 + i * txt.get_height()
            x_offset = rect.x + rect.w // 2 - txt.get_width() // 2
            surf.blit(txt, (x_offset, y_offset))

# ---------- Экран плиток ----------
class TileScreen:
    def __init__(self, tiles):
        self.tiles = tiles
        self.selected = 0

    def draw(self, surf_full):
        temp = pygame.Surface((SCREEN_W, VISIBLE_H))
        temp.fill(BG_COLOR)

        for i, tile in enumerate(self.tiles):
            col = i % COLS
            row = i // COLS
            x = PADDING + col * (TILE_SIZE + PADDING)
            y = PADDING + row * (TILE_SIZE + PADDING)
            rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
            tile.draw(temp, rect, selected=(i == self.selected))

        footer_h = 18
        footer_rect = pygame.Rect(0, VISIBLE_H - footer_h, SCREEN_W, footer_h)
        pygame.draw.rect(temp, FOOTER_COLOR, footer_rect)
        hint = "↑↓←→ выбор   OK открыть"
        hint_surf = footer_font.render(hint, True, (180, 180, 180))
        hint_rect = hint_surf.get_rect(center=footer_rect.center)
        temp.blit(hint_surf, hint_rect)

        offset_top = (SCREEN_H - VISIBLE_H) // 2
        surf_full.blit(temp, (0, offset_top))

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

# ---------- создаём главное меню ----------
labels = ["OFF", "FLASH", "LOG", "WIFI",
          "REBOOT", "READ\nMAC", "SET", "BATT"]
tiles = [Tile(lbl, callback=stub_action(lbl)) for lbl in labels]
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
