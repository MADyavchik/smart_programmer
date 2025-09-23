import RPi.GPIO as GPIO
import pygame
from PIL import Image
from luma.core.interface.serial import spi
from luma.lcd.device import st7789

# Настройка GPIO
buttons = {
    "up": 5,
    "down": 19,
    "left": 6,
    "right": 26,
    "reset": 13,
}
GPIO.setmode(GPIO.BCM)
for pin in buttons.values():
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # кнопки на землю

# Настройка дисплея
serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=16, bus_speed_hz=40000000)
device = st7789(serial, width=320, height=240, rotate=0)

# Pygame
pygame.init()
width, height = 320, 240
surface = pygame.Surface((width, height))
font = pygame.font.Font(None, 36)
clock = pygame.time.Clock()

menu_items = ["Прошить", "Проверка", "Настройки", "Выход"]
selected = 0

running = True
try:
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

        # Проверка кнопок
        if GPIO.input(buttons["up"]) == GPIO.LOW:   # нажата
            selected = (selected - 1) % len(menu_items)
        elif GPIO.input(buttons["down"]) == GPIO.LOW:
            selected = (selected + 1) % len(menu_items)
        elif GPIO.input(buttons["reset"]) == GPIO.LOW:  # вместо Enter
            choice = menu_items[selected]
            print(f"Выбран пункт: {choice}")
            if choice == "Выход":
                running = False

        clock.tick(10)
finally:
    GPIO.cleanup()
