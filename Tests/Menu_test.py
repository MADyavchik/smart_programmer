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

# Меню
menu_items = ["Прошить", "Проверка", "Настройки", "Выход"]
selected = 0

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

    # Обработка событий клавиатуры
    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            if event.key in [pygame.K_UP, pygame.K_w]:
                selected = (selected - 1) % len(menu_items)
            elif event.key in [pygame.K_DOWN, pygame.K_s]:
                selected = (selected + 1) % len(menu_items)
            elif event.key == pygame.K_RETURN:
                choice = menu_items[selected]
                print(f"Выбран пункт: {choice}")
                if choice == "Выход":
                    running = False
                # Здесь добавляй действия по выбору

    clock.tick(10)
