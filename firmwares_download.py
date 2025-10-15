# firmware_downloader.py
from packaging import version
import os
import requests

SERVER_URL = "https://tn.zitsky.com/flasher/eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE3NjA1MzY1ODQsIm5hbWUiOiJQYXZlbFBvcnRhdGl2ZSJ9.xaJabSB73QsJBhjHb4jQT2VHJXtQ8NXz3EQ3I0M2l7I/firmwares"
DOWNLOAD_DIR = "firmwares_downloaded"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def download_latest_firmware():
    """Скачивает последнюю версию прошивки с сервера"""
    try:
        response = requests.get(SERVER_URL)
        response.raise_for_status()
        data = response.json()

        # Проверяем наличие ключа 'firmwares'
        firmwares = data.get("firmwares", [])
        if not firmwares:
            print("❌ Нет доступных прошивок")
            return None

        # ✅ Логируем доступные прошивки
        print("\n📦 Доступные прошивки:")
        for fw in firmwares:
            print(f"  • Версия: {fw['version']}, Группа: {fw['group']}, Дата: {fw['created_at']}")

        # Сортируем по версии (если строки, можно по created_at)
        firmwares.sort(key=lambda x: version.parse(x["version"]))
        latest = firmwares[-1]

        zip_url = latest["zip"]
        latest_version = latest["version"]

        file_name = zip_url.split("/")[-1] + ".zip"
        local_path = os.path.join(DOWNLOAD_DIR, file_name)

        with requests.get(zip_url, stream=True) as r:
            r.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        print(f"✅ Прошивка {latest_version} скачана: {local_path}")
        return local_path

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None
