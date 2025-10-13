import subprocess

def read_logs(command=["platformio", "device", "monitor"]):
    """
    Запускает монитор платформы и построчно читает вывод.
    Возвращает генератор строк.
    """
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        for line in process.stdout:
            yield line.rstrip()

    except Exception as e:
        yield f"Ошибка: {e}"
