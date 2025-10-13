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

def wrap_text_to_screen(text, font, max_width, line_spacing=4, indent=20):
    """
    Делит текст на строки для экрана.
    Только переносимые части получают отступ.
    Возвращает список кортежей: (строка, indent_flag)
    """
    words = text.split(' ')
    lines = []
    current = ""
    first_line = True

    for word in words:
        test_line = (current + " " + word).strip()
        test_width = font.size(test_line)[0]
        if test_width <= max_width:
            current = test_line
        else:
            lines.append((current, not first_line))  # True = нужно сдвигать
            current = word
            first_line = False

    if current:
        lines.append((current, not first_line))

    return lines

# Add line
def add_log_line(line, font, max_width, max_height, line_spacing=4, indent=20):
    global log_lines
    wrapped = wrap_text_to_screen(line, font, max_width, line_spacing, indent)
    log_lines.extend(wrapped)

    # ограничиваем по высоте
    line_height = font.get_linesize() + line_spacing
    max_lines = max_height // line_height
    if len(log_lines) > max_lines:
        log_lines = log_lines[-max_lines:]

    return log_lines
