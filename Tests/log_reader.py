import serial

def read_logs(port="/dev/ttyS0", baud=115200):
    """
    Читает построчно UART и возвращает генератор строк.
    Аналог monitor PlatformIO, но без PIO.
    """
    try:
        with serial.Serial(port, baud, timeout=0.1) as ser:
            while True:
                line = ser.readline().decode(errors="ignore").strip()
                if line:
                    yield line
    except Exception as e:
        yield f"Ошибка: {e}"
