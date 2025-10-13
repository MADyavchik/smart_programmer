import serial
import re

# Регулярка для ANSI escape-последовательностей
ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')


log_lines = []  # буфер логов
MAX_LOG_HEIGHT = 170  # видимая область для текста

def read_logs(port="/dev/ttyS0", baud=115200):

    try:
        with serial.Serial(port, baud, timeout=0.1) as ser:
            while True:
                line = ser.readline().decode(errors="ignore").strip()
                if line:
                    yield line
    except Exception as e:
        yield f"Ошибка: {e}"

def clean_line(line):
    """
    Убирает все ANSI коды и неотображаемые символы из строки
    """
    # Убираем ANSI коды
    line = ansi_escape.sub('', line)
    # Убираем все неотображаемые символы (\x00, спецсимволы)
    line = "".join(ch for ch in line if 32 <= ord(ch) <= 126)
    return line

def wrap_text_to_screen(text, font, max_width, max_height, line_spacing=4, indent=20):
    """
    Делит текст на строки для экрана, добавляя отступ для переноса.
    indent: пиксели для сдвига всех строк кроме первой.
    """
    words = text.split(' ')
    lines = []
    current = ""
    line_height = font.get_linesize()

    first_line = True  # флаг первой строки

    for word in words:
        test_line = (current + " " + word).strip()
        # для вычисления ширины применяем отступ только к переносимым строкам
        test_width = font.size(test_line)[0] + (0 if first_line else indent)
        if test_width <= max_width:
            current = test_line
        else:
            # добавляем текущую строку в список
            lines.append(current)
            current = word
            first_line = False  # последующие строки будут с отступом

    if current:
        lines.append(current)

    # ограничиваем по высоте экрана
    max_lines = max_height // (line_height + line_spacing)
    return lines[:max_lines]

# Add line
def add_log_line(line, font, max_width, max_height, line_spacing=4):
    """
    Добавляет строку в буфер с автоматическим переносом.
    Возвращает список всех видимых строк на экране.
    """
    global log_lines

    # перенос длинной строки
    wrapped = wrap_text_to_screen(line, font, max_width, max_height, line_spacing)

    log_lines.extend(wrapped)

    # вычисляем высоту всех строк
    line_height = font.get_linesize() + line_spacing
    max_lines = max_height // line_height

    # если строк больше чем помещается — обрезаем сверху
    if len(log_lines) > max_lines:
        log_lines = log_lines[-max_lines:]

    return log_lines
