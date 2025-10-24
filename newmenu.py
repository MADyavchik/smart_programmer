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
# ---- Заменить старую функцию read_gpio_input() и главный цикл main() на этот блок ----

# карта пинов -> имя события
PIN_TO_KEY = {
    KEY_UP: "UP",
    KEY_DOWN: "DOWN",
    KEY_LEFT: "LEFT",
    KEY_RIGHT: "RIGHT",
    KEY_OK: "OK",
    KEY_BACK: "BACK",
}

# для антидребезга и детекции фронтов
last_pin_state = {pin: True for pin in PIN_TO_KEY.keys()}  # True == PUD_UP (not pressed)
last_event_time = {pin: 0 for pin in PIN_TO_KEY.keys()}
DEBOUNCE_SEC = 0.15

def poll_buttons():
    """
    Возвращает название события при обнаружении перехода HIGH->LOW (нажатия).
    Возвращает None если нет нового события.
    Реализован debounce по времени и ожидание отпускания — функция сама не ждёт отпускания,
    но основная логика в main ниже ожидает отпускания для OK, если нужно.
    """
    now = time.time()
    for pin, name in PIN_TO_KEY.items():
        state = GPIO.input(pin)  # True == not pressed, False == pressed (pull-up)
        last = last_pin_state[pin]
        # detect falling edge
        if last and not state:
            # возможное нажатие
            if now - last_event_time[pin] >= DEBOUNCE_SEC:
                last_event_time[pin] = now
                last_pin_state[pin] = state
                return name
        # update state when released (rising edge) so next press can be detected
        if not last and state:
            last_pin_state[pin] = state
    return None

def wait_release(pin, timeout=1.5):
    """
    Блокирует до отпускания кнопки или timeout.
    Используется чтобы не генерировать авто-повтор при удержании.
    """
    start = time.time()
    while GPIO.input(pin) == GPIO.LOW and (time.time() - start) < timeout:
        time.sleep(0.01)

def main():
    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    GPIO.cleanup()
                    return

            ev = poll_buttons()
            if ev:
                # если OK — ждём отпускания кнопки, чтобы не было множества срабатываний
                if ev == "OK":
                    menu.handle_input("OK")
                    wait_release(KEY_OK)
                elif ev == "BACK":
                    # твоя логика для BACK
                    print("[BACK] pressed")
                    wait_release(KEY_BACK)
                else:
                    # стрелки — просто прокрутка, можно не ждать отпускания
                    if ev == "UP":
                        menu.handle_input("UP")
                    elif ev == "DOWN":
                        menu.handle_input("DOWN")
                    elif ev == "LEFT":
                        menu.handle_input("LEFT")
                    elif ev == "RIGHT":
                        menu.handle_input("RIGHT")
                # краткая пауза после обработки, дополнительный защитный механизм
                time.sleep(0.05)

            menu.draw(screen)
            clock.tick(30)

    finally:
        GPIO.cleanup()

# если файл запускается как main
if __name__ == "__main__":
    main()
