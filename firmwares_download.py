# firmware_downloader.py
from packaging import version
import os
import requests
import zipfile

SERVER_URL = "https://tn.zitsky.com/flasher/eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE3NjA1MzY1ODQsIm5hbWUiOiJQYXZlbFBvcnRhdGl2ZSJ9.xaJabSB73QsJBhjHb4jQT2VHJXtQ8NXz3EQ3I0M2l7I/firmwares"
DOWNLOAD_DIR = "firmware"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def download_latest_firmware():
    """Скачивает последнюю версию прошивки с сервера и распаковывает архив"""
    try:
        response = requests.get(SERVER_URL)
        response.raise_for_status()
        data = response.json()

        firmwares = data.get("firmwares", [])
        if not firmwares:
            print("❌ Нет доступных прошивок")
            return None

        print("\n📦 Доступные прошивки:")
        for fw in firmwares:
            print(f"  • Версия: {fw['version']}, Группа: {fw['group']}, Дата: {fw['created_at']}")

        firmwares.sort(key=lambda x: version.parse(x["version"]))
        latest = firmwares[-1]

        zip_url = latest["zip"]
        version_str = latest["version"]
        file_name = f"{version_str}.zip"
        local_path = os.path.join(DOWNLOAD_DIR, file_name)

        # --- Скачивание ---
        with requests.get(zip_url, stream=True) as r:
            r.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        print(f"✅ Прошивка {version_str} скачана: {local_path}")

        # --- Распаковка ---
        extract_dir = os.path.join(DOWNLOAD_DIR, version_str)
        os.makedirs(extract_dir, exist_ok=True)

        with zipfile.ZipFile(local_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        print(f"📂 Архив распакован в: {extract_dir}")

        os.remove(local_path)
        print(f"🗑 Архив удалён: {local_path}")

        return extract_dir

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None
