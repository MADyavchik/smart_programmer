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

def wrap_text_to_screen(text, font, max_width, max_height, line_spacing=4):
    """
    Делит текст на строки, чтобы полностью помещался на экране.
    text       : исходная строка
    font       : pygame.font.Font
    max_width  : ширина экрана в пикселях
    max_height : высота экрана в пикселях
    line_spacing: расстояние между строками
    """
    words = text.split(' ')
    lines = []
    current = ""
    line_height = font.get_linesize()

    for word in words:
        test_line = (current + " " + word).strip()
        if font.size(test_line)[0] <= max_width:
            current = test_line
        else:
            lines.append(current)
            current = word

    if current:
        lines.append(current)

    # Обрезаем строки, если превышают высоту экрана
    max_lines = max_height // (line_height + line_spacing)
    return lines[:max_lines]

    # Остаток слов — в последнюю строку
    remaining_words = words[words.index(word):] if len(lines) == max_lines - 1 else []
    last_line = current + " " + " ".join(remaining_words)
    last_line = last_line.strip()
    lines.append(last_line)

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
