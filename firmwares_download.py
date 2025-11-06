# firmware_downloader.py
from packaging import version
import os
import requests
import zipfile

SERVER_URL = "https://tn.zitsky.com/flasher/eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpYXQiOjE3NjA1MzY1ODQsIm5hbWUiOiJQYXZlbFBvcnRhdGl2ZSJ9.xaJabSB73QsJBhjHb4jQT2VHJXtQ8NXz3EQ3I0M2l7I/firmwares"
DOWNLOAD_DIR = "firmware"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def download_latest_firmware(on_msg=None):
    try:

        response = requests.get(SERVER_URL)
        response.raise_for_status()
        data = response.json()

        firmwares = data.get("firmwares", [])
        if not firmwares:
            msg = "Нет доступных прошивок"
            if on_msg: on_msg(msg)
            print(msg)
            return []
        msg = "поиск новых прошивок"
        if on_msg: on_msg(msg)
        print("\nДоступные прошивки:")
        for fw in firmwares:
            print(f"  • Версия: {fw['version']}, Группа: {fw['group']}, Дата: {fw['created_at']}")

        # сортируем по номеру
        firmwares.sort(key=lambda x: version.parse(x["version"]))

        # берём последние три
        last_three = firmwares[-6:]
        saved_paths = []

        for fw in last_three:
            version_str = fw["version"]
            zip_url = fw["zip"]
            file_name = f"{version_str}.zip"
            local_path = os.path.join(DOWNLOAD_DIR, file_name)
            extract_dir = os.path.join(DOWNLOAD_DIR, version_str)

            # если распакованная версия уже есть — пропускаем
            if os.path.exists(extract_dir):
                msg = f"Папка {extract_dir}-Ок"
                if on_msg: on_msg(msg)
                print(msg)
                saved_paths.append(extract_dir)
                continue

            # скачиваем ZIP
            with requests.get(zip_url, stream=True) as r:
                r.raise_for_status()
                with open(local_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            msg = f"Скачано: {local_path}"
            if on_msg: on_msg(msg)
            print(msg)

            # распаковываем
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(local_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            msg = f"Распаковано в: {extract_dir}"
            if on_msg: on_msg(msg)
            print(msg)

            # удаляем архив
            os.remove(local_path)
            msg = f"Удалено: {local_path}"
            if on_msg: on_msg(msg)
            print(msg)

            saved_paths.append(extract_dir)

            cleanup_old_firmwares(DOWNLOAD_DIR, keep=6)

            msg = "Готово!"
            if on_msg: on_msg(msg)
            print(msg)

        return saved_paths

    except Exception as e:
        msg = f"Ошибка: {e}"
        if on_msg: on_msg(msg)
        print(msg)
        return []

def cleanup_old_firmwares(base_dir, keep):
    """Удаляет старые прошивки, оставляя только последние 'keep' версии."""
    folders = [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]
    if not folders:
        return

    # сортируем как версии
    folders.sort(key=version.parse, reverse=True)

    # старые — всё, кроме первых 'keep'
    for old in folders[keep:]:
        path = os.path.join(base_dir, old)
        print(f"Удаляем старую прошивку: {old}")
        os.system(f"rm -rf '{path}'")
