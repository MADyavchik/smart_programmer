# main.py
import time
from PIL import Image
import pygame
import RPi.GPIO as GPIO

# Импортируем из ui.py всё, что нужно
from ui import manager, device, surface, clock, SCREEN_W, SCREEN_H, BG_COLOR, poll_buttons, wait_release, KEY_OK


def main():
    try:
        while True:
            # --- Обработка кнопок ---
            key = poll_buttons()
            if key:
                manager.current.handle_input(key)
                if key == "OK":
                    wait_release(KEY_OK)
                time.sleep(0.05)

            # --- Отрисовка UI ---
            surface.fill(BG_COLOR)
            manager.draw(surface)

            # --- Вывод на дисплей ---
            raw_str = pygame.image.tobytes(surface, "RGB")
            img = Image.frombytes("RGB", (SCREEN_W, SCREEN_H), raw_str)
            device.display(img)

            clock.tick(30)

    finally:
        GPIO.cleanup()
        pygame.quit()
        # остановка потока апдейтера
        from ui import status_updater
        status_updater.stop()


if __name__ == "__main__":
    main()
