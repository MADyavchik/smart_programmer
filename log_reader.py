# log_reader.py
import re


# Регулярка для удаления ANSI-последовательностей
ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')


class LogManager:
    def __init__(self, font, max_width, max_height, line_spacing=4, alert_markers=None):
        self.font = font
        self.max_width = max_width
        self.max_height = max_height
        self.line_spacing = line_spacing
        self.alert_markers = alert_markers or ["ReportBuilder:"]

        self.log_lines = []      # [(строка, indent_flag)]
        self.scroll_index = 0
        self.auto_scroll = True
        self.generator = None

    # --- Запуск UART чтения ---
    def start(self, port="/dev/ttyS0", baud=115200):
        self.generator = self._read_logs(port, baud)

    def _read_logs(self, port, baud):
        try:
            import serial
            with serial.Serial(port, baud, timeout=0.1) as ser:  # короткий таймаут
                while True:
                    if ser.in_waiting:  # проверяем, есть ли данные
                        line = ser.readline().decode(errors="ignore").strip()
                        if line:
                            yield line
                    else:
                        yield None  # генератор не блокирует цикл
        except Exception as e:
            yield f"Ошибка: {e}"

    # --- Чистка от ANSI и мусора ---
    def _clean_line(self, line):
        line = ansi_escape.sub('', line)
        line = "".join(ch for ch in line if 32 <= ord(ch) <= 126)
        return line

    # --- Перенос строки на экран ---
    def _wrap_text(self, text):
        words = text.split(' ')
        lines = []
        current = ""
        first_line = True

        for word in words:
            test_line = (current + " " + word).strip()
            test_width = self.font.size(test_line)[0]
            if test_width <= self.max_width:
                current = test_line
            else:
                lines.append((current, not first_line))
                current = word
                first_line = False

        if current:
            lines.append((current, not first_line))

        return lines

    # --- Добавление строки в буфер ---
    def add_line(self, line):
        clean = self._clean_line(line)
        wrapped = self._wrap_text(clean)
        self.log_lines.extend(wrapped)

    # --- Получение визуальных строк (учёт скролла) ---
    def get_visible(self):
        line_height = self.font.get_linesize() + self.line_spacing
        max_visible_lines = self.max_height // line_height

        if self.auto_scroll:
            self.scroll_index = max(0, len(self.log_lines) - max_visible_lines)

        start = self.scroll_index
        end = start + max_visible_lines
        return self.log_lines[start:end], line_height

    # --- Скролл вверх ---
    def scroll_up(self):
        self.auto_scroll = False
        self.scroll_index = max(0, self.scroll_index - 1)

    # --- Скролл вниз ---
    def scroll_down(self):
        self.auto_scroll = False
        line_height = self.font.get_linesize() + self.line_spacing
        max_visible_lines = self.max_height // line_height
        max_scroll = max(0, len(self.log_lines) - max_visible_lines)
        self.scroll_index = min(max_scroll, self.scroll_index + 1)

    # --- Перейти в конец (включить автопрокрутку) ---
    def scroll_to_end(self):
        self.auto_scroll = True

    # --- Проверка на «красные» строки ---
    def is_alert_line(self, text):
        return any(marker in text for marker in self.alert_markers)
