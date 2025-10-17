# esp_flasher_class.py
import os
import subprocess
import logging
import re
import time
import RPi.GPIO as GPIO
import glob

logging.basicConfig(level=logging.INFO)

class ESPFlasher:
    def __init__(self, port="/dev/ttyS0", flash_dir="esp", boot_pin=24, en_pin=23):
        self.port = port
        self.flash_dir = flash_dir
        self.boot_pin = boot_pin
        self.en_pin = en_pin
        self.mac_address = None


        GPIO.setwarnings(False)   # Чтобы убрать предупреждения
        GPIO.setmode(GPIO.BCM)

        GPIO.setup(self.boot_pin, GPIO.OUT, initial=GPIO.HIGH)
        GPIO.setup(self.en_pin, GPIO.OUT, initial=GPIO.HIGH)

    # ===== Bootloader =====
    def enter_bootloader(self, boot_pin, en_pin):

        logging.info("🔌 Перевод ESP32 в режим загрузчика...")
        GPIO.output(boot_pin, GPIO.LOW)
        time.sleep(0.15)
        GPIO.output(en_pin, GPIO.LOW)
        time.sleep(0.1)
        GPIO.output(en_pin, GPIO.HIGH)
        logging.info("ESP32 теперь в режиме загрузчика.")

    def exit_bootloader(self, boot_pin, en_pin):

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
    def flash_firmware(self, variant_file_path, on_stage=None, on_progress=None):
        """
        variant_file_path: полный путь к выбранному варианту, например:
        /root/smart_programmer/firmware/2.0.47/battery_sw_a_0x9000.bin
        """
        version_folder = os.path.dirname(variant_file_path)  # /root/.../2.0.47
        variant_name = os.path.basename(variant_file_path)   # battery_sw_a_0x9000.bin
        base_name = variant_name.split("_0x9000")[0]        # battery_sw_a

        if not os.path.exists(version_folder):
            logging.error(f"❌ Папка с прошивкой не найдена: {version_folder}")
            return False

        # Ищем файлы по суффиксам
        bootloader = self.catch_name(version_folder, "_0x1000.bin")
        firmware = self.catch_name(version_folder, "_0x10000.bin")
        partitions = self.catch_name(version_folder, "_0x8000.bin")
        ota = self.catch_name(version_folder, "_0xe000.bin")
        nvs = self.catch_name(version_folder, f"{base_name}_0x9000.bin")  # <-- нужный файл NVS

        for file in [bootloader, firmware, partitions, ota, nvs]:
            if not file or not os.path.exists(file):
                logging.error(f"❌ Файл не найден: {file}")
                return False

        try:
            logging.info("🔌 Входим в bootloader...")

            self.enter_bootloader(self.boot_pin, self.en_pin)
            if on_stage: on_stage("Enter Bootloader")
            if on_progress: on_progress(0)

            logging.info("🔌 Прожигаем фьюзы...")
            subprocess.run([
                "espefuse.py", "--chip", "esp32", "-p", self.port, "--do-not-confirm", "set_flash_voltage", "3.3V"
            ], check=True)
            if on_stage: on_stage("Burn fuses")
            if on_progress: on_progress(5)

            logging.info("🧹 Очистка флеша...")
            if on_stage: on_stage("Erase Flash")
            if on_progress: on_progress(10)
            subprocess.run(
                ["esptool.py", "--chip", "esp32", "-b", "460800", "-p", self.port, "erase_flash"],
                check=True
            )


            logging.info("🔌 Повторно входим в bootloader...")
            self.enter_bootloader(self.boot_pin, self.en_pin)


            logging.info("📦 Прошивка...")
            if on_stage: on_stage("Flash...")
            if on_progress: on_progress(15)

            flash_args = [
                "python3", "-u", "esptool.py", "--chip", "esp32", "-b", "460800", "-p", self.port,
                "write_flash", "--flash_mode", "dio", "--flash_freq", "40m", "--flash_size", "4MB",
                "0x1000", bootloader,
                "0x10000", firmware,
                "0x8000", partitions,
                "0xe000", ota,
                "0x9000", nvs
            ]

            start_percent = 15    # начало этапа Flash Firmware на общей шкале
            stage_range = 85      # сколько процентов занимает этап

            #proc = subprocess.Popen(flash_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            proc = subprocess.Popen(
                flash_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,   # или universal_newlines=True, но text=True предпочтительнее
                bufsize=1    # line-buffered
            )

            for line in proc.stdout:
                line = line.strip()
                print(line)
                # ловим проценты из строки esptool
                m = re.search(r"\[\=+\s*\>\s*\]*\s+(\d+\.\d+)%", line)
                if m and on_progress:
                    firmware_percent = float(m.group(1))
                    total_percent = start_percent + firmware_percent / 100 * stage_range
                    on_progress(total_percent)

            proc.wait()

            logging.info("✅ Прошивка завершена")
            if on_stage: on_stage("Done")
            if on_progress: on_progress(100)

            self.exit_bootloader(self.boot_pin, self.en_pin)
            return True

        except subprocess.CalledProcessError as e:
            logging.error(f"❌ Ошибка прошивки: {e}")
            self.exit_bootloader(self.boot_pin, self.en_pin)
            return False

    # ===== Вспомогательные функции =====

    def catch_name(self, path, suffix):

        matches = glob.glob(os.path.join(path, f"*{suffix}"))
        if matches:
            file = matches[0]  # берем первый
            print(f"Найден NVS-файл: {file}")
            return file

        else:
            print(f"Файл с окончанием {suffix} не найден")
            return False



