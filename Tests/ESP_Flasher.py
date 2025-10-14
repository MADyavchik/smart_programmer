# --- ESP_Flasher.py ---
import RPi.GPIO as GPIO
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BOOT_PIN = 24
EN_PIN = 23

# ⚠️ Не вызываем GPIO.setmode и setup здесь, это делается в основном меню
def enter_bootloader():
    logging.info("Перевод ESP32 в режим загрузчика...")
    GPIO.output(BOOT_PIN, GPIO.LOW)
    time.sleep(0.15)
    GPIO.output(EN_PIN, GPIO.LOW)
    time.sleep(0.1)
    GPIO.output(EN_PIN, GPIO.HIGH)
    logging.info("ESP32 теперь в режиме загрузчика.")

def exit_bootloader():
    logging.info("Выход из режима загрузчика...")
    GPIO.output(BOOT_PIN, GPIO.HIGH)
    time.sleep(0.1)
    GPIO.output(EN_PIN, GPIO.LOW)
    time.sleep(0.12)
    GPIO.output(EN_PIN, GPIO.HIGH)
    time.sleep(0.8)
    logging.info("ESP32 перезагружена в нормальный режим.")
