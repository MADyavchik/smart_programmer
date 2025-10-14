import os
import json
import requests

# Адрес твоего локального сервера
SERVER_URL = "http://192.168.1.193:8000/firmwares.json"

# Папка, куда будем сохранять скачанные прошивки
DOWNLOAD_DIR = "firmwares_downloaded"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def get_firmware_list():
    """Запрос JSON со списком прошивок"""
    response = requests.get(SERVER_URL)
    response.raise_for_status()  # Если ошибка, выбросит исключение
    return response.json()

def download_firmware(file_name):
    """Скачиваем файл по имени"""
    url = f"http://192.168.1.193:8000/{file_name}"
    local_path = os.path.join(DOWNLOAD_DIR, file_name)
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    print(f"✅ Файл {file_name} сохранён в {local_path}")
    return local_path

def main():
    firmwares = get_firmware_list()
    if not firmwares:
        print("Нет доступных прошивок")
        return

    # Например, выбираем последнюю версию (по имени файла)
    firmwares.sort(key=lambda x: x["version"])
    latest = firmwares[-1]
    print(f"Выбрана последняя версия: {latest['version']} ({latest['file']})")

    # Скачиваем
    download_firmware(latest["file"])

if __name__ == "__main__":
    main()
