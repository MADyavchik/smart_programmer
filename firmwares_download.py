# firmware_downloader.py

import os
import json
import requests

SERVER_URL = "http://192.168.1.193:8000/firmwares.json"
DOWNLOAD_DIR = "firmwares_downloaded"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def download_latest_firmware():
    """Скачивает последнюю версию прошивки с сервера"""
    response = requests.get(SERVER_URL)
    response.raise_for_status()
    firmwares = response.json()
    if not firmwares:
        print("Нет доступных прошивок")
        return None

    # Выбираем последнюю версию
    firmwares.sort(key=lambda x: x["version"])
    latest = firmwares[-1]
    file_name = latest["file"]

    # Скачиваем
    url = f"http://192.168.1.193:8000/{file_name}"
    local_path = os.path.join(DOWNLOAD_DIR, file_name)
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    print(f"✅ Файл {file_name} сохранён в {local_path}")
    return local_path
