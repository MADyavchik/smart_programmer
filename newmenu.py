# tile_menu.py
import os
import time
import pygame
import RPi.GPIO as GPIO
from PIL import Image
from luma.core.interface.serial import spi
from luma.lcd.device import st7789

# ---------- Настройки железа / дисплея ----------
# SPI / Luma — параметры как у тебя раньше
serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=16, bus_speed_hz=40000000)
device = st7789(serial, width=320, height=240, rotate=0)

# ---------- GPIO настройки ----------
KEY_UP = 5
KEY_DOWN = 6
KEY_LEFT = 16
KEY_RIGHT = 20
KEY_OK = 21
KEY_BACK = 26

GPIO.setmode(GPIO.BCM)
for pin in [KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_OK, KEY_BACK]:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# ---------- базовые настройки экрана ----------
WIDTH, HEIGHT = 320, 240            # full surface size
VISIBLE_HEIGHT = 170                # как у тебя было
SCREEN_W, SCREEN_H = WIDTH, HEIGHT

# плиточная сетка: 4 колонки, 2 ряда (макс 8 плиток)
COLS = 4
ROWS = 2

# автоматически рассчитываем padding и TILE_SIZE, чтобы плитки помещались по ширине
PADDING = 8
TILE_SIZE = (SCREEN_W - (COLS + 1) * PADDING) // COLS

BG_COLOR = (255, 255, 0)            # фон центральной зоны (как у тебя раньше)
TILE_COLOR = (60, 60, 60)
SELECTED_COLOR = (255, 0, 0)
TEXT_COLOR = (0, 0, 0)
FOOTER_COLOR = (30, 30, 30)

# Показывать окно X11 для отладки (если у тебя нет X - оставь False)
SHOW_WINDOW = False

pygame.init()
# для отладки можно создать окно; основной рендер идёт в surface и отправляется на device
if SHOW_WINDOW:
    win = pygame.display.set_mode((SCREEN_W, SCREEN_H))
else:
    win = None

# поверхность, на которой рисуем всё (полный размер дисплея)
surface = pygame.Surface((SCREEN_W, SCREEN_H))
clock = pygame.time.Clock()

# используем встроенный шрифт — безопаснее на embedded
font = pygame.font.Font(None, 18)
footer_font = pygame.font.Font(None, 14)

# ---------- описание плитки ----------
class Tile:
    def __init__(self, label, callback=None):
        self.label = label
        self.callback = callback

    def draw(self, surf, rect, selected=False):
        color = SELECTED_COLOR if selected else TILE_COLOR
        pygame.draw.rect(surf, color, rect, border_radius=10)
        # подпись: многострочная поддержка
        lines = self.label.split("\n")
        for i, line in enumerate(lines):
            txt = font.render(line, True, TEXT_COLOR)
            # позиционируем по центру плитки, с учётом мн. строк
            total_h = len(lines) * txt.get_height()
            y_offset = rect.y + (rect.h - total_h) // 2 + i * txt.get_height()
            x_offset = rect.x + rect.w // 2 - txt.get_width() // 2
            surf.blit(txt, (x_offset, y_offset))

# ---------- экран плиток ----------
class TileScreen:
    def __init__(self, tiles):
        assert len(tiles) <= COLS * ROWS, "Максимум 8 плиток"
        self.tiles = tiles
        self.selected = 0  # индекс выбранной плитки

    def draw(self, surf_full):
        # рисуем всю central area (видимую часть) в temp surface, затем оно будет blit'нуто на main surface
        temp = pygame.Surface((SCREEN_W, VISIBLE_HEIGHT))
        temp.fill(BG_COLOR)

        # верхний отступ внутри видимой зоны — используем PADDING сверху
        y0 = PADDING
        x0 = PADDING

        for idx, tile in enumerate(self.tiles):
            col = idx % COLS
            row = idx // COLS
            x = x0 + col * (TILE_SIZE + PADDING)
            y = y0 + row * (TILE_SIZE + PADDING)
            rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
            selected = (idx == self.selected)
            tile.draw(temp, rect, selected=selected)

        # footer (пояснения) — рисуем в нижней части видимой зоны
        footer_h = 18
        footer_rect = pygame.Rect(0, VISIBLE_HEIGHT - footer_h, SCREEN_W, footer_h)
        pygame.draw.rect(temp, FOOTER_COLOR, footer_rect)
        hint = "↑↓←→ выбор   OK открыть   ← назад"
        hint_surf = footer_font.render(hint, True, (200, 200, 200))
        hint_rect = hint_surf.get_rect(center=footer_rect.center)
        temp.blit(hint_surf, hint_rect)

        # теперь blit temp (320x170) в центральную область surf_full (320x240) с vertical offset
        offset_top = (HEIGHT - VISIBLE_HEIGHT) // 2
        surf_full.blit(temp, (0, offset_top))

    def handle_input(self, direction):
        # движение по сетке 4×2
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

# ---------- создание главного меню ----------
labels = [
    "OFF", "FLASH", "LOG", "WIFI",
    "REBOOT", "READ\nMAC", "SET", "BATT"
]
tiles = [Tile(lbl, callback=stub_action(lbl)) for lbl in labels]
menu = TileScreen(tiles)

# ---------- чтение GPIO-кнопок ----------
PIN_TO_KEY = {
    KEY_UP: "UP",
    KEY_DOWN: "DOWN",
    KEY_LEFT: "LEFT",
    KEY_RIGHT: "RIGHT",
    KEY_OK: "OK",
    KEY_BACK: "BACK",
}

last_pin_state = {pin: True for pin in PIN_TO_KEY.keys()}  # True == not pressed
last_event_time = {pin: 0 for pin in PIN_TO_KEY.keys()}
DEBOUNCE_SEC = 0.12

def poll_buttons():
    now = time.time()
    for pin, name in PIN_TO_KEY.items():
        state = GPIO.input(pin)  # True == not pressed, False == pressed
        last = last_pin_state[pin]
        if last and not state:  # falling edge
            if now - last_event_time[pin] >= DEBOUNCE_SEC:
                last_event_time[pin] = now
                last_pin_state[pin] = state
                return name
        if not last and state:  # released
            last_pin_state[pin] = state
    return None

def wait_release(pin, timeout=1.5):
    start = time.time()
    while GPIO.input(pin) == GPIO.LOW and (time.time() - start) < timeout:
        time.sleep(0.01)

# ---------- главный цикл ----------
def main():
    try:
        running = True
        while running:
            # Обработка SDL-событий (нужно чтобы не подвисало)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False

            key = poll_buttons()
            if key:
                if key == "OK":
                    menu.handle_input("OK")
                    wait_release(KEY_OK)
                elif key == "BACK":
                    print("[BACK] pressed")
                    wait_release(KEY_BACK)
                else:
                    menu.handle_input(key)
                time.sleep(0.05)

            # Подготовка поверхности полного размера
            surface.fill((0,0,0))  # очищаем всю поверхность (можно оставить фон)
            menu.draw(surface)

            # Отправляем на реальный SPI-дисплей: surface -> raw -> PIL -> device.display
            raw_str = pygame.image.tostring(surface, "RGB")
            img = Image.frombytes("RGB", (WIDTH, HEIGHT), raw_str)
            device.display(img)

            # Опционально показываем в окне для отладки
            if win is not None:
                win.blit(surface, (0,0))
                pygame.display.flip()

            clock.tick(30)

    finally:
        GPIO.cleanup()
        pygame.quit()

if __name__ == "__main__":
    main()
