# --- ESP_Flasher.py ---
import RPi.GPIO as GPIO
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")



# ⚠️ Не вызываем GPIO.setmode и setup здесь, это делается в основном меню
def enter_bootloader(boot_pin, en_pin):
    logging.info("Перевод ESP32 в режим загрузчика...")
    GPIO.output(boot_pin, GPIO.LOW)
    time.sleep(0.15)
    GPIO.output(en_pin, GPIO.LOW)
    time.sleep(0.1)
    GPIO.output(en_pin, GPIO.HIGH)
    logging.info("ESP32 теперь в режиме загрузчика.")

def exit_bootloader(boot_pin, en_pin):
    logging.info("Выход из режима загрузчика...")
    GPIO.output(boot_pin, GPIO.HIGH)
    time.sleep(0.1)
    GPIO.output(en_pin, GPIO.LOW)
    time.sleep(0.12)
    GPIO.output(en_pin, GPIO.HIGH)
    time.sleep(0.8)
    logging.info("ESP32 перезагружена в нормальный режим.")
