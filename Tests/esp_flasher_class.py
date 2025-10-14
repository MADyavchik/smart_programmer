# esp_flasher_class.py
import os
import subprocess
import logging
import re
import time

logging.basicConfig(level=logging.INFO)

class ESPFlasher:
    def __init__(self, port="/dev/ttyS0", flash_dir="esp"):
        self.port = port
        self.flash_dir = flash_dir
        self.mac_address = None

    # ===== Bootloader =====
    def enter_bootloader(self, boot_pin, en_pin):
        import RPi.GPIO as GPIO
        logging.info("🔌 Перевод ESP32 в режим загрузчика...")
        GPIO.output(boot_pin, GPIO.LOW)
        time.sleep(0.15)
        GPIO.output(en_pin, GPIO.LOW)
        time.sleep(0.1)
        GPIO.output(en_pin, GPIO.HIGH)
        logging.info("ESP32 теперь в режиме загрузчика.")

    def exit_bootloader(self, boot_pin, en_pin):
        import RPi.GPIO as GPIO
        logging.info("🛑 Выход из режима загрузчика...")
        GPIO.output(boot_pin, GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(en_pin, GPIO.LOW)
        time.sleep(0.12)
        GPIO.output(en_pin, GPIO.HIGH)
        time.sleep(0.8)
        logging.info("ESP32 перезагружена в нормальный режим.")

    # ===== Чтение MAC-адреса =====
    def get_mac_address(self):
        try:
            self.enter_bootloader_func()
            result = subprocess.run(
                ["esptool.py", "--chip", "esp32", "-p", self.port, "read_mac"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                check=True
            )
            mac_line = next((line for line in result.stdout.splitlines() if "MAC:" in line), None)
            if mac_line:
                mac = mac_line.split("MAC:")[1].strip()
                self.mac_address = mac.lower()
                logging.info(f"✅ MAC-адрес: {self.mac_address}")
                self.exit_bootloader_func()
                return self.mac_address
            else:
                raise Exception("MAC-адрес не найден")
        except Exception as e:
            logging.error(f"❌ Ошибка получения MAC: {e}")
            self.exit_bootloader_func()
            return None

    # ===== Прошивка =====
    def flash_firmware(self, firmware_name):
        #firmware_name = firmware_name.lower()
        firmware_path = os.path.join(self.flash_dir, firmware_name)
        if not os.path.exists(firmware_path):
            logging.error(f"❌ Папка с прошивкой не найдена: {firmware_path}")
            return False

        bootloader = os.path.join(firmware_path, "bootloader_0x1000.bin")
        firmware = os.path.join(firmware_path, "firmware_0x10000.bin")
        partitions = os.path.join(firmware_path, "partitions_0x8000.bin")
        ota = os.path.join(firmware_path, "ota_data_initial_0xe000.bin")

        for file in [bootloader, firmware, partitions, ota]:
            if not os.path.exists(file):
                logging.error(f"❌ Файл не найден: {file}")
                return False

        try:
            logging.info("🔌 Входим в bootloader...")
            self.enter_bootloader_func()

            logging.info("🧹 Очистка флеша...")
            subprocess.run(
                ["esptool.py", "--chip", "esp32", "-b", "460800", "-p", self.port, "erase_flash"],
                check=True
            )

            logging.info("📦 Прошивка...")
            flash_args = [
                "esptool.py", "--chip", "esp32", "-b", "460800", "-p", self.port,
                "write_flash", "--flash_mode", "dio", "--flash_freq", "40m", "--flash_size", "4MB",
                "0x1000", bootloader,
                "0x10000", firmware,
                "0x8000", partitions,
                "0xe000", ota
            ]

            subprocess.run(flash_args, check=True)
            logging.info("✅ Прошивка завершена")

            self.exit_bootloader_func()
            return True

        except subprocess.CalledProcessError as e:
            logging.error(f"❌ Ошибка прошивки: {e}")
            self.exit_bootloader_func()
            return False

    # ===== Вспомогательные функции для работы с пинами =====
    def enter_bootloader_func(self):
        from Menu_test import BOOT_PIN, EN_PIN
        self.enter_bootloader(BOOT_PIN, EN_PIN)

    def exit_bootloader_func(self):
        from Menu_test import BOOT_PIN, EN_PIN
        self.exit_bootloader(BOOT_PIN, EN_PIN)
