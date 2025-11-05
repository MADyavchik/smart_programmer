# utils.py
import os
import sys
import pygame
import RPi.GPIO as GPIO
import json
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

MAC_LOG_FILE = "/root/mac_log.json"  # или твой путь

# путь к директории, где лежит utils.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# путь к JSON-файлу ключа Google
GOOGLE_KEY_PATH = os.path.join(BASE_DIR, "parsfor-efc9e0058e29.json")

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

def init_google_sheet(sheet_name="read_MACs"):
    """Открывает таблицу ESP_MACs и возвращает лист по имени.
    Если листа нет — создаёт его и добавляет заголовки.
    """
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_KEY_PATH, scope)
    client = gspread.authorize(creds)
    workbook = client.open("ESP_MACs")

    # Проверяем, есть ли лист с нужным именем
    try:
        sheet = workbook.worksheet(sheet_name)
        print(f"📄 Используется существующий лист: {sheet_name}")
    except gspread.WorksheetNotFound:
        print(f"🆕 Лист '{sheet_name}' не найден — создаю новый...")
        sheet = workbook.add_worksheet(title=sheet_name, rows="1000", cols="10")
        headers = ["Date", "Time", "MAC", "Firmware Version", "Firmware Type"]
        sheet.update("A1:E1", [headers])
        print(f"✅ Создан новый лист '{sheet_name}' с заголовками.")

    return sheet

def sync_mac_log_with_google():
    """Синхронизирует несинхронизированные MAC-адреса в лист read_MACs Google Sheets."""
    if not os.path.exists(MAC_LOG_FILE):
        print("⚠️ Локальный файл MAC-логов не найден.")
        return

    try:
        with open(MAC_LOG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print("❌ Ошибка чтения mac_log.json — повреждён файл.")
        return

    unsynced = [entry for entry in data if not entry.get("synced", False)]

    if not unsynced:
        print("✅ Все записи уже синхронизированы.")
        return

    try:
        # Берём или создаём лист read_MACs
        sheet = init_google_sheet(sheet_name="read_MACs")
        all_records = sheet.get_all_records()

        for entry in unsynced:
            mac = entry.get("mac")
            if not mac:
                continue

            # Проверяем, есть ли уже запись с таким MAC
            existing_row = None
            for i, row in enumerate(all_records):
                if row.get("MAC") == mac:
                    existing_row = i + 2  # +2 из-за заголовка
                    break

            row_values = [
                entry.get("date"),
                entry.get("time"),
                mac,
                entry.get("firmware_version"),
                entry.get("firmware_type")
            ]

            if existing_row:
                sheet.update(f"A{existing_row}:E{existing_row}", [row_values])
                print(f"🔁 Обновлён MAC в '{sheet.title}': {mac}")
            else:
                sheet.append_row(row_values)
                print(f"☁️ Добавлен MAC в '{sheet.title}': {mac}")

            entry["synced"] = True

        # Обновляем локальный лог
        with open(MAC_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print("✅ Синхронизация завершена успешно.")

    except Exception as e:
        print(f"❌ Ошибка при синхронизации с Google Sheets: {e}")
