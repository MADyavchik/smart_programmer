# tile_menu.py
import pygame
import RPi.GPIO as GPIO
import time
import sys

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
SCREEN_W, SCREEN_H = 320, 170
TILE_SIZE = 70
PADDING = 10
BG_COLOR = (20, 20, 20)
TILE_COLOR = (60, 60, 60)
SELECTED_COLOR = (255, 212, 59)
TEXT_COLOR = (255, 255, 255)
FOOTER_COLOR = (30, 30, 30)

pygame.init()
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Smart Programmer UI")
font = pygame.font.SysFont("DejaVuSans", 16)
clock = pygame.time.Clock()


# ---------- описание плитки ----------
class Tile:
    def __init__(self, label, x, y, callback=None):
        self.label = label
        self.x = x
        self.y = y
        self.callback = callback

    def draw(self, surface, selected=False):
        rect = pygame.Rect(self.x, self.y, TILE_SIZE, TILE_SIZE)
        color = SELECTED_COLOR if selected else TILE_COLOR
        pygame.draw.rect(surface, color, rect, border_radius=10)
        label_surf = font.render(self.label, True, TEXT_COLOR)
        label_rect = label_surf.get_rect(center=rect.center)
        surface.blit(label_surf, label_rect)


# ---------- экран плиток ----------
class TileScreen:
    def __init__(self, tiles):
        self.tiles = tiles
        self.selected = 0  # индекс выбранной плитки

    def draw(self, surface):
        surface.fill(BG_COLOR)
        for i, tile in enumerate(self.tiles):
            tile.draw(surface, selected=(i == self.selected))
        self.draw_footer(surface)
        pygame.display.flip()

    def draw_footer(self, surface):
        footer_rect = pygame.Rect(0, SCREEN_H - 18, SCREEN_W, 18)
        pygame.draw.rect(surface, FOOTER_COLOR, footer_rect)
        hint = "↑↓←→ выбор   OK открыть   ← назад"
        hint_surf = pygame.font.SysFont("DejaVuSans", 12).render(hint, True, (200, 200, 200))
        hint_rect = hint_surf.get_rect(center=footer_rect.center)
        surface.blit(hint_surf, hint_rect)

    def handle_input(self, direction):
        # движение по сетке 4×2
        row_len = 4
        if direction == "LEFT" and self.selected % row_len > 0:
            self.selected -= 1
        elif direction == "RIGHT" and self.selected % row_len < row_len - 1:
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
tiles = []
labels = [
    "OFF", "FLASH", "LOG", "WIFI",
    "REBOOT", "READ\nMAC", "SET", "BATT"
]
x0, y0 = PADDING, PADDING
for i, lbl in enumerate(labels):
    col = i % 4
    row = i // 4
    x = x0 + col * (TILE_SIZE + PADDING)
    y = y0 + row * (TILE_SIZE + PADDING)
    tiles.append(Tile(lbl, x, y, callback=stub_action(lbl)))

menu = TileScreen(tiles)


# ---------- чтение GPIO-кнопок ----------
def read_gpio_input():
    if not GPIO.input(KEY_UP):
        return "UP"
    if not GPIO.input(KEY_DOWN):
        return "DOWN"
    if not GPIO.input(KEY_LEFT):
        return "LEFT"
    if not GPIO.input(KEY_RIGHT):
        return "RIGHT"
    if not GPIO.input(KEY_OK):
        return "OK"
    if not GPIO.input(KEY_BACK):
        return "BACK"
    return None


# ---------- основной цикл ----------
def main():
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                GPIO.cleanup()
                sys.exit()

        key = read_gpio_input()
        if key:
            if key == "BACK":
                print("[BACK] pressed")
            else:
                menu.handle_input(key)
            time.sleep(0.2)  # антидребезг

        menu.draw(screen)
        clock.tick(30)


if __name__ == "__main__":
    main()
