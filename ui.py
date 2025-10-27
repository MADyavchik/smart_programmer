# ui.py
import os
import time
import pygame
import RPi.GPIO as GPIO
#from PIL import Image
from luma.core.interface.serial import spi
from luma.lcd.device import st7789
#from system_status import BatteryMonitor, WifiMonitor
from firmwares_download import download_latest_firmware
from esp_flasher_class import ESPFlasher
from log_reader import LogManager
from system_status import BatteryMonitor, WifiMonitor
from system_updater import SystemStatusUpdater  # <-- новый файл/класс
import subprocess

# создаём объекты батареи и WiFi
batt = BatteryMonitor(multiplier=2.0, charge_pin=21)
wifi = WifiMonitor(interface="wlan0")

# создаём апдейтера, который будет обновлять данные в отдельном потоке
status_updater = SystemStatusUpdater(batt, wifi, interval=1.0)
status_updater.start()



# ---------- Объекты прошивки ESP ----------

flasher = ESPFlasher(
    port="/dev/ttyS0",
    flash_dir="/root/smart_programmer/firmware",
    boot_pin=24,
    en_pin=23
)

# ---------- Объекты системного статуса ----------
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
VISIBLE_H = 170
OFFSET_Y = (SCREEN_H - VISIBLE_H) // 2

COLS, ROWS = 4, 2
PADDING = 4
FOOTER_H = 25

AVAILABLE_H = VISIBLE_H - FOOTER_H - (ROWS + 1) * PADDING
TILE_W = (SCREEN_W - (COLS + 1) * PADDING) // COLS
TILE_H = AVAILABLE_H // ROWS

BG_COLOR = (0, 0, 0)
TILE_COLOR = (180, 140, 0)
SELECTED_COLOR = (255, 220, 0)
TEXT_COLOR = (0, 0, 0)
FOOTER_COLOR = (0, 0, 0)

pygame.init()
pygame.display.set_mode((1, 1))
surface = pygame.Surface((SCREEN_W, SCREEN_H))
clock = pygame.time.Clock()
font = pygame.font.Font(None, 25)
footer_font = pygame.font.Font(None, FOOTER_H)

# ---------- Классы плиток и экранов ----------
class Tile:
    def __init__(self, label=None, icon=None, callback=None, name=None,
                 dynamic_label_func=None, dynamic_color_func=None,
                 dynamic_icon_func=None):
        self.label = label
        self.icon = icon
        self.callback = callback
        self.name = name
        self.dynamic_label_func = dynamic_label_func
        self.dynamic_color_func = dynamic_color_func
        self.dynamic_icon_func = dynamic_icon_func

    def draw(self, surf, rect, selected=False):
        if self.dynamic_color_func:
            try:
                color = self.dynamic_color_func(selected)
            except:
                color = SELECTED_COLOR if selected else TILE_COLOR
        else:
            color = SELECTED_COLOR if selected else TILE_COLOR

        pygame.draw.rect(surf, color, rect, border_radius=5)

        if self.dynamic_label_func:
            try:
                self.label = str(self.dynamic_label_func())
            except:
                self.label = "ERR"

        icon_to_draw = self.icon
        if self.dynamic_icon_func:
            try:
                icon_to_draw = self.dynamic_icon_func()
            except:
                pass

        if icon_to_draw:
            icon_rect = icon_to_draw.get_rect(center=rect.center)
            surf.blit(icon_to_draw, icon_rect)
        elif self.label:
            txt = font.render(self.label, True, TEXT_COLOR)
            surf.blit(txt, (rect.centerx - txt.get_width() // 2,
                            rect.centery - txt.get_height() // 2))

class TileScreen:
    def __init__(self, tiles):
        self.tiles = tiles
        self.selected = 0

    def draw(self, surf_full):
        surf_full.fill(BG_COLOR)
        for i, tile in enumerate(self.tiles):
            col = i % COLS
            row = i // COLS
            x = PADDING + col * (TILE_W + PADDING)
            y = OFFSET_Y + PADDING + row * (TILE_H + PADDING)
            rect = pygame.Rect(x, y, TILE_W, TILE_H)
            tile.draw(surf_full, rect, selected=(i == self.selected))

        footer_rect = pygame.Rect(0, OFFSET_Y + VISIBLE_H - FOOTER_H, SCREEN_W, FOOTER_H)
        pygame.draw.rect(surf_full, FOOTER_COLOR, footer_rect)
        current_tile = self.tiles[self.selected]

        if getattr(current_tile, "dynamic_label_func", None):
            footer_text = current_tile.dynamic_label_func()
        elif getattr(current_tile, "name", None):
            footer_text = current_tile.name       # <- name теперь имеет приоритет
        elif current_tile.label:
            footer_text = current_tile.label
        else:
            footer_text = ""

        hint_surf = footer_font.render(footer_text, True, SELECTED_COLOR)
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

# ---------- ScreenManager ----------
class ScreenManager:
    def __init__(self, root_screen):
        self.screens = [root_screen]

    @property
    def current(self):
        return self.screens[-1]

    def open(self, new_screen):
        self.screens.append(new_screen)

    def back(self):
        if len(self.screens) > 1:
            self.screens.pop()

    def draw(self, surf):
        self.current.draw(surf)

    def handle_input(self, direction):
        self.current.handle_input(direction)

# ---------- Утилиты ----------
def stub_action(name):
    def _():
        print(f"[ACTION] {name} clicked!")
    return _

def load_icon(filename, size=(32, 32)):
    base_path = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base_path, "icons", filename)
    img = pygame.image.load(full_path).convert_alpha()
    img = pygame.transform.smoothscale(img, size)
    return img

def make_dynamic_footer_tile(icon, name, action_func):
    """
    Создаёт Tile с динамическим футером:
    - По умолчанию отображается name
    - При запуске action_func футер меняется на статус
    - Одновременные запуски блокируются
    """
    import threading
    import time

    footer_text = {"current": name}  # текущее значение футера
    lock = threading.Lock()          # блокировка для предотвращения параллельных запусков

    def dynamic_label_func():
        return footer_text["current"]

    def callback():
        # пытаемся захватить lock
        if not lock.acquire(blocking=False):
            # если уже выполняется другой поток, просто игнорируем нажатие
            return

        def thread_func():
            try:
                footer_text["current"] = "Обновление запущено..."
                action_func()  # выполняем основное действие
                time.sleep(2)
                footer_text["current"] = "Готово"
                time.sleep(2)  # показываем "Готово" пару секунд
            except Exception as e:
                footer_text["current"] = "Ошибка"
                time.sleep(2)
            finally:
                footer_text["current"] = name  # возвращаем исходный текст
                lock.release()  # снимаем блокировку

        threading.Thread(target=thread_func, daemon=True).start()

    return Tile(icon=icon, dynamic_label_func=dynamic_label_func, callback=callback)

# ---------- Системные функции плиток ----------
def battery_text():
    percent = status_updater.battery_percent
    return f"{percent}%"


def battery_color(selected=False):
    charging = status_updater.battery_charging
    percent = status_updater.battery_percent

    if charging:
        color = (0, 180, 255)
        highlight = (0, 220, 255)
    else:
        if percent <= 20:
            color = (180, 50, 50)
            highlight = (255, 80, 80)
        else:
            color = (0, 200, 0)
            highlight = (0, 255, 0)

    return highlight if selected else color

def wifi_icon_func():
    quality = status_updater.wifi_quality
    if quality == 0:
        return WIFI0_icon
    elif quality <= 30:
        return WIFI1_icon
    elif quality <= 70:
        return WIFI2_icon
    else:
        return WIFI3_icon

def wifi_text():
    ssid = status_updater.wifi_ssid or "нет сети"
    rssi = status_updater.wifi_rssi or 0
    return f"{ssid} ({rssi} dBm)"


def wifi_color(selected=False):
    quality = status_updater.wifi_quality
    if quality == 0:
        color = (180, 50, 50)
        highlight = (255, 80, 80)
    else:
        color = (200, 200, 200)
        highlight = (255, 255, 255)
    return highlight if selected else color

def shutdown_action():
    os.system("sudo poweroff")

def reboot_action():
    os.system("sudo reboot")


# ---------- Иконки ----------
OFF_icon = load_icon("off_ico.png")
REB_icon = load_icon("reboot_ico.png")
LOG_icon = load_icon("log_ico.png")
SET_icon = load_icon("settings_ico.png")
FLASH_icon = load_icon("flash_ico.png")
READMAC_icon = load_icon("readmac_ico.png")
BATT_icon = load_icon("batt_ico.png")
WIFI0_icon = load_icon("wifi0_ico.png")
WIFI1_icon = load_icon("wifi1_ico.png")
WIFI2_icon = load_icon("wifi2_ico.png")
WIFI3_icon = load_icon("wifi3_ico.png")
DLOAD_icon = load_icon("download_ico.png")
BACK_icon = load_icon("back_ico.png")

OFF_tile = make_dynamic_footer_tile(
    icon=OFF_icon,
    name="Выключение",
    action_func=shutdown_action
)

REB_tile = make_dynamic_footer_tile(
    icon=REB_icon,
    name="Перезагрузка",
    action_func=reboot_action
)

# ---------- Главное меню ----------
main_tiles = [
    Tile(icon=OFF_icon, callback=shutdown_action, name="Выключение"),
    #OFF_tile,
    Tile(icon=FLASH_icon, callback=lambda: open_flash_version_menu(manager), name="Меню прошивки"),
    Tile(icon=LOG_icon, callback=lambda: open_log_screen(manager), name="Чтение лога"),
    Tile(dynamic_icon_func=wifi_icon_func, dynamic_color_func=wifi_color, callback=stub_action("WIFI"), dynamic_label_func=wifi_text),
    Tile(icon=REB_icon, callback=reboot_action, name="Перезагрузка"),
    #REB_tile,
    Tile(icon=READMAC_icon, callback=stub_action("READ MAC"), name="Считать MAC"),
    Tile(icon=SET_icon, callback=lambda: open_settings_menu(manager), name="Настройки"),  # <- новая плитка,
    Tile(icon=BATT_icon, dynamic_color_func=battery_color, callback=stub_action("BATT"), dynamic_label_func=battery_text)
]

main_menu = TileScreen(main_tiles)
manager = ScreenManager(main_menu)

class ProgressScreen:
    def __init__(self, title="Прошивка...", footer_text=""):
        self.title = title
        self.footer_text = footer_text
        self.progress = 0
        self.stage = "Подготовка..."
        self.finished = False
        self.success = None  # True / False после завершения

    def draw(self, surf_full):
        # Фон
        surf_full.fill(BG_COLOR)

        # Заголовок
        title_surf = font.render(self.title, True, SELECTED_COLOR)
        surf_full.blit(title_surf, (SCREEN_W // 2 - title_surf.get_width() // 2, OFFSET_Y + 20))

        # Прогрессбар
        bar_x = 40
        bar_y = SCREEN_H // 2 - 15
        bar_w = SCREEN_W - 2 * bar_x
        bar_h = 30

        pygame.draw.rect(surf_full, (80, 80, 80), (bar_x, bar_y, bar_w, bar_h), border_radius=8)
        fill_w = int(bar_w * self.progress / 100)
        pygame.draw.rect(surf_full, (255, 220, 0), (bar_x, bar_y, fill_w, bar_h), border_radius=8)

        # Текст процентов
        pct = font.render(f"{int(self.progress)}%", True, (255, 255, 255))
        surf_full.blit(pct, (SCREEN_W // 2 - pct.get_width() // 2, bar_y + bar_h + 10))

        # --- Футер (используем существующую логику от TileScreen) ---
        footer_rect = pygame.Rect(0, OFFSET_Y + VISIBLE_H - FOOTER_H, SCREEN_W, FOOTER_H)
        pygame.draw.rect(surf_full, FOOTER_COLOR, footer_rect)

        footer_text = self.stage if self.stage else self.footer_text
        footer_surf = footer_font.render(footer_text, True, SELECTED_COLOR)
        footer_rect_text = footer_surf.get_rect(center=footer_rect.center)
        surf_full.blit(footer_surf, footer_rect_text)

    def handle_input(self, direction):
        # После завершения — выход по OK
        if self.finished and direction == "OK":
            manager.back()

# ---------- Подменю прошивки ----------
def make_flash_type_menu(manager, version_dir):
    from esp_flasher_class import ESPFlasher
    flasher = ESPFlasher(port="/dev/ttyS0")

    base_path = os.path.join("/root/smart_programmer/firmware", version_dir)
    print(f"[DEBUG] Поиск файлов в: {base_path}")

    markers = ["sw_nvs_a", "sw_a", "lr_a", "lr_nvs_a"]
    bin_files = [
        f for f in os.listdir(base_path)
        if (
            f.endswith("_0x9000.bin") and
            any(marker in f for marker in markers) and
            os.path.isfile(os.path.join(base_path, f))
        )
    ]
    bin_files.sort()

    tiles = []
    # Кнопка "Назад"
    tiles.append(Tile(icon=BACK_icon, callback=lambda: manager.back(), name="Назад"))

    # ⚙️ Функция для создания колбэка с прогрессом
    def make_callback(full_path):
        def _():
            # 1️⃣ Открываем экран прогресса
            relative_path = full_path.split("/firmware/")[-1]
            clean_name = relative_path.replace("_0x9000.bin", "")

            # создаём экран с понятным заголовком
            prog_screen = ProgressScreen(
                title=f"Прошивка: {clean_name}",
                footer_text=os.path.basename(full_path)
            )
            manager.open(prog_screen)

            # 2️⃣ Определяем функции для обновления экрана
            def on_stage(stage):
                prog_screen.stage = stage

            def on_progress(percent):
                prog_screen.progress = percent

            # 3️⃣ Запускаем прошивку в отдельном потоке
            import threading
            def flash_thread():
                success = flasher.flash_firmware(
                    full_path,
                    on_stage=on_stage,
                    on_progress=on_progress
                )
                prog_screen.finished = True
                prog_screen.success = success
                prog_screen.stage = "Готово" if success else "Ошибка"

            threading.Thread(target=flash_thread, daemon=True).start()

        return _

    # Плитки для всех прошивок
    for f in bin_files:
        full_path = os.path.join(base_path, f)
        tiles.append(
            Tile(label=f[:2], name=f, callback=make_callback(full_path))
        )

    # Создаём экран
    return TileScreen(tiles)


def open_flash_version_menu(manager):
    """Меню выбора версии прошивки (по папкам)."""
    base_path = "/root/smart_programmer/firmware"

    # Список папок-версий
    versions = [
        f for f in os.listdir(base_path)
        if os.path.isdir(os.path.join(base_path, f))
    ]
    versions.sort(reverse=True)

    tiles = []

    # Кнопка "Назад"
    tiles.append(Tile(icon=BACK_icon, callback=lambda: manager.back(), name="Назад"))

    # Кнопки для каждой версии (открывают make_flash_type_menu)
    for ver in versions:
        tiles.append(
            Tile(label=ver, callback=lambda v=ver: manager.open(make_flash_type_menu(manager, v)))
        )

    # Кнопка "Обновить прошивки"
    tiles.append(Tile(icon=DLOAD_icon, callback=lambda: download_latest_firmware(), name="Обновить вер.прошивки"))

    manager.open(TileScreen(tiles))

def open_settings_menu(manager):
    """Меню настроек."""
    tiles = []

    # Кнопка "Назад"
    tiles.append(Tile(icon=BACK_icon, callback=lambda: manager.back(), name="Назад"))

    # Кнопка "Обновить программу через Git"
    def update_program():
        import threading
        def git_thread():
            try:
                print("🔄 Обновление программы через Git...")
                os.system("cd /root/smart_programmer && git pull")
                print("✅ Обновление завершено!")
            except Exception as e:
                print(f"❌ Ошибка обновления: {e}")

        threading.Thread(target=git_thread, daemon=True).start()

    tiles.append(
        make_dynamic_footer_tile(icon=DLOAD_icon, name="Обновить версию по", action_func=update_program)
    )
    manager.open(TileScreen(tiles))

def open_log_screen(manager):

    log_manager = LogManager(font, max_width=SCREEN_W - 20, max_height=VISIBLE_H - FOOTER_H)
    screen = LogScreen(log_manager, footer_text="UART Log")
    manager.open(screen)

class LogScreen:
    def __init__(self, log_manager, footer_text="UART Log"):
        self.log_manager = log_manager
        self.footer_text = footer_text
        self.log_manager.start()  # запуск при входе на экран

    def draw(self, surf):
        surf.fill((0, 0, 0))
        visible, line_h = self.log_manager.get_visible()
        y = 10
        for line, indent in visible:
            color = (255, 255, 255)
            text = font.render(line, True, color)
            surf.blit(text, (10 if not indent else 25, y))
            y += line_h

        # футер — как везде
        footer_rect = pygame.Rect(0, OFFSET_Y + VISIBLE_H - FOOTER_H, SCREEN_W, FOOTER_H)
        pygame.draw.rect(surf, (0, 0, 0), footer_rect)
        hint_surf = footer_font.render(self.footer_text, True, (255, 255, 0))
        surf.blit(hint_surf, hint_surf.get_rect(center=footer_rect.center))

    def handle_input(self, direction):
        if direction == "UP":
            self.log_manager.scroll_up()
        elif direction == "DOWN":
            self.log_manager.scroll_down()
        elif direction == "RIGHT":
            self.log_manager.scroll_to_end()
        elif direction == "LEFT":
            manager.back()
            self.log_manager.stop()  # ⬅️ остановка логгера при выходе

# ---------- GPIO логика ----------
PIN_TO_KEY = {KEY_UP: "UP", KEY_DOWN: "DOWN", KEY_LEFT: "LEFT", KEY_RIGHT: "RIGHT", KEY_OK: "OK"}
last_pin_state = {pin: True for pin in PIN_TO_KEY}
last_event_time = {pin: 0 for pin in PIN_TO_KEY}
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


