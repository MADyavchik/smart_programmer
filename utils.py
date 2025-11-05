# utils.py
import os
import sys
import pygame
import RPi.GPIO as GPIO
import json
from datetime import datetime

def clean_exit(manager=None, status_updater=None, poweroff=False, reboot=False, restart_app=False):
    """
    Корректное завершение приложения с остановкой потоков и очисткой ресурсов.

    Параметры:
        manager: объект ScreenManager (опционально)
        status_updater: объект SystemStatusUpdater (опционально)
        poweroff: если True — выключить систему
        reboot: если True — перезагрузить систему
        restart_app: если True — мягко перезапустить демон через systemd
    """
    print("[INFO] Stopping all threads and cleaning up...")

    # остановка апдейтера
    if status_updater:
        status_updater.stop()

    # остановка логов в менеджере экранов
    if manager:
        try:
            for screen in getattr(manager, "screens", []):
                if hasattr(screen, "log_manager"):
                    screen.log_manager.stop()
        except Exception:
            pass

    # очистка ресурсов
    GPIO.cleanup()
    pygame.quit()

    # системные действия
    if poweroff:
        print("[INFO] Powering off system...")
        os.system("sudo poweroff -i")
    elif reboot:
        print("[INFO] Rebooting system...")
        os.system("sudo reboot -i")
    elif restart_app:
        print("[INFO] Restarting smart_programmer.service...")
        os.system("sudo systemctl restart smart_programmer.service")

    # завершение процесса
    sys.exit(0)



MAC_LOG_FILE = "/root/smart_programmer/mac_log.json"

import os
import json
from datetime import datetime



MAC_LOG_FILE = "/root/mac_log.json"  # или твой путь

def log_mac_locally(mac_address: str, firmware_version: str = None, firmware_type: str = None):
    """
    Логирует или обновляет запись о MAC-адресе в локальном JSON-файле.

    Формат записи:
    {
        "date": "2025-11-05",
        "time": "15:47:20",
        "mac": "AA:BB:CC:DD:EE:FF",
        "firmware_version": "v1.2.3",
        "firmware_type": "esp32-lr",
        "synced": false
    }
    """
    entry = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M:%S"),
        "mac": mac_address,
        "firmware_version": firmware_version or "unknown",
        "firmware_type": firmware_type or "unknown",
        "synced": False
    }

    try:
        # Загружаем текущие записи
        if os.path.exists(MAC_LOG_FILE):
            with open(MAC_LOG_FILE, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    print("⚠️ Повреждён mac_log.json — пересоздаём файл.")
                    data = []
        else:
            data = []

        # Проверяем, есть ли этот MAC
        updated = False
        for record in data:
            if record.get("mac") == mac_address:
                # Обновляем запись (только поля, которые реально могли измениться)
                record.update(entry)
                updated = True
                break

        # Если нет — добавляем новую
        if not updated:
            data.append(entry)

        # Сохраняем обратно
        with open(MAC_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        if updated:
            print(f"🔁 Обновлён MAC: {mac_address}")
        else:
            print(f"✅ Добавлен новый MAC: {mac_address}")

    except Exception as e:
        print(f"❌ Ошибка записи MAC в лог: {e}")
