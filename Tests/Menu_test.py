import threading
import queue
import sys
import termios
import tty
import pygame
from PIL import Image
from luma.core.interface.serial import spi
from luma.lcd.device import st7789

# Настройка дисплея
serial = spi(port=0, device=0, gpio_DC=23, gpio_RST=24, bus_speed_hz=40000000)
device = st7789(serial, width=320, height=240, rotate=2)

# Pygame
pygame.init()
width, height = 320, 240
surface = pygame.Surface((width, height))
font = pygame.font.Font(None, 36)
clock = pygame.time.Clock()

menu_items = ["Прошить", "Проверка", "Настройки", "Выход"]
selected = 0

# Очередь для клавиш
key_queue = queue.Queue()

# Поток чтения клавиш из терминала SSH
def read_keys(q):
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        while True:
            ch = sys.stdin.read(1)
            q.put(ch)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

# Запуск потока
threading.Thread(target=read_keys, args=(key_queue,), daemon=True).start()

running = True
while running:
    surface.fill((0, 0, 0))

    # Рисуем меню
    for i, item in enumerate(menu_items):
        color = (255, 255, 0) if i == selected else (255, 255, 255)
        text_surface = font.render(item, True, color)
        surface.blit(text_surface, (50, 50 + i * 40))

    # Отображение на дисплее
    raw_str = pygame.image.tostring(surface, "RGB")
    img = Image.frombytes("RGB", (width, height), raw_str)
    device.display(img)

    # Обработка нажатий с SSH
    while not key_queue.empty():
        key = key_queue.get()
        if key in ['w', 'A', '\x1b[A']:  # 'w' или стрелка вверх
            selected = (selected - 1) % len(menu_items)
        elif key in ['s', 'B', '\x1b[B']:  # 's' или стрелка вниз
            selected = (selected + 1) % len(menu_items)
        elif key == '\n':  # Enter
            choice = menu_items[selected]
            print(f"Выбран пункт: {choice}")
            if choice == "Выход":
                running = False

    clock.tick(10)
