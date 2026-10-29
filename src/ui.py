"""Lightweight terminal UI for the plate combiner.

No third-party packages: ANSI styling, raw-key input and layout are stdlib only.
The palette follows a small three-layer token model: primitive colours →
semantic roles → components/screens.
"""

import io
import os
import re
import select
import shutil
import subprocess
import sys
import textwrap
import time
from contextlib import redirect_stderr
from pathlib import Path

import app_config
import extract_plates_from_excel as extract_plates
import pcr_tools
import plate_layout
import report_xlsx
import run_pipeline
import seq_structure
import tool_reports
import tools as genetics
from i18n import TEXT
from run_pipeline import __version__, application_dir, next_result_number


def copy_text_to_clipboard(text):
    """Best-effort clipboard write for the TUI (Windows ``clip``, else pbcopy/xclip)."""
    data = text.replace('\n', '\r\n') if os.name == 'nt' else text
    if os.name == 'nt':
        completed = subprocess.run(
            ['clip'],
            input=data.encode('utf-16le'),
            check=False,
            capture_output=True,
        )
        return completed.returncode == 0
    for command in (['pbcopy'], ['xclip', '-selection', 'clipboard']):
        try:
            completed = subprocess.run(
                command,
                input=data.encode('utf-8'),
                check=False,
                capture_output=True,
            )
        except FileNotFoundError:
            continue
        if completed.returncode == 0:
            return True
    return False

RESULT_PATTERN = run_pipeline.RESULT_DIR_PATTERN

# Primitive tokens
PRIMITIVE = {
    'slate950': (11, 16, 32),
    'slate900': (17, 24, 39),
    'slate800': (30, 41, 59),
    'slate700': (51, 65, 85),
    'slate500': (100, 116, 139),
    'slate400': (148, 163, 184),
    'slate200': (226, 232, 240),
    'cyan400': (34, 211, 238),
    'violet400': (167, 139, 250),
    'emerald400': (52, 211, 153),
    'amber400': (251, 191, 36),
    'red400': (248, 113, 113),
    'white': (255, 255, 255),
    # Four nations plate accents (web --plate-1…4)
    'earth': (79, 154, 40),
    'water': (30, 111, 179),
    'air': (22, 164, 135),
    'fire': (171, 22, 16),
}

PLATE_NATION = ('earth', 'water', 'air', 'fire')

# Semantic tokens
SEMANTIC = {
    'bg': 'slate950',
    'panel': 'slate900',
    'border': 'slate700',
    'text': 'slate200',
    'muted': 'slate400',
    'dim': 'slate500',
    'accent': 'cyan400',
    'accent2': 'violet400',
    'success': 'emerald400',
    'warning': 'amber400',
    'error': 'red400',
    'white': 'white',
    'earth': 'earth',
    'water': 'water',
    'air': 'air',
    'fire': 'fire',
}

FALLBACK_256 = {
    'bg': 234,
    'panel': 235,
    'border': 238,
    'text': 252,
    'muted': 245,
    'dim': 240,
    'accent': 45,
    'accent2': 141,
    'success': 42,
    'warning': 214,
    'error': 203,
    'white': 231,
    'earth': 70,
    'water': 33,
    'air': 43,
    'fire': 160,
}

RESET = '\x1b[0m'
RESET_FG = '\x1b[39m\x1b[22m'
ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')




HELP = {
    'en': [
        ('Run', 'Press R or Enter. A new «Результат N» folder is created and every output is written there.'),
        ('Outputs', 'plate1-4.csv, metadata.csv, combined_384_plate.csv, combined_384_plate_pivot.csv and combined_384_plate_ids.txt.'),
        ('Config', 'Press C. The workbook is found automatically; F chooses the file, S the four sheets, R the data range. No config file to edit.'),
        ('Tools', 'Press T. Inspect primers and DNA, analyse oligo structure and in-silico PCR, validate wellmap layouts, and export results to XLSX.'),
        ('Web', 'Run with --web to open a local web UI: file and sheet selection, live log, results and genetics tools. The server listens on 127.0.0.1 only.'),
        ('Quick keys', 'R run · T tools · D results · O open last · C config · H help · L language · Q quit. Arrow keys move, Enter confirms.'),
        ('CFX', 'Paste combined_384_plate_ids.txt into Bio-Rad CFX Manager 3.1.'),
        ('Size', 'Runtime: Bio.Seq, Pint, Primer3-py, seqfold, pydna, wellmap, pandas, openpyxl and NiceGUI for the local web UI; matplotlib is not bundled.'),
    ],
    'ru': [
        ('Запуск', 'Нажмите R или Enter. Будет создана папка «Результат N», в неё попадут все файлы.'),
        ('Результаты', 'plate1-4.csv, metadata.csv, combined_384_plate.csv, combined_384_plate_pivot.csv и combined_384_plate_ids.txt.'),
        ('Настройка', 'Нажмите C. Файл Excel находится автоматически; F — выбрать файл, S — четыре листа, R — диапазон. Править конфиг не нужно.'),
        ('Инструменты', 'Нажмите T. Проверка праймеров и ДНК, структура олиго и ПЦР in silico, проверка раскладки wellmap, экспорт результатов в XLSX.'),
        ('Веб', 'Запустите с --web: локальный веб-интерфейс с выбором файла и листов, живым логом, результатами и инструментами. Сервер слушает только 127.0.0.1.'),
        ('Быстрые клавиши', 'R запуск · T инструменты · D результаты · O открыть последний · C настройки · H помощь · L язык · Q выход. Стрелки — выбор, Enter — подтвердить.'),
        ('CFX', 'Вставьте combined_384_plate_ids.txt в Bio-Rad CFX Manager 3.1.'),
        ('Размер', 'Рантайм: Bio.Seq, Pint, Primer3-py, seqfold, pydna, wellmap, pandas, openpyxl и NiceGUI для веб-интерфейса; matplotlib в сборку не входит.'),
    ],
}


def detect_language():
    locale = (
        os.environ.get('LC_ALL')
        or os.environ.get('LC_MESSAGES')
        or os.environ.get('LANG')
        or ''
    ).lower()
    if 'ru' in locale:
        return 'ru'
    if 'en' in locale:
        return 'en'
    return 'ru'


def _supports_truecolor():
    if os.name == 'nt':
        return True
    colorterm = os.environ.get('COLORTERM', '').lower()
    term = os.environ.get('TERM', '').lower()
    return (
        colorterm in ('truecolor', '24bit')
        or 'truecolor' in term
        or '24bit' in term
        or any(name in term for name in ('kitty', 'alacritty', 'wezterm', 'ghostty'))
    )


class Theme:
    """ANSI token resolver with 24-bit and 256-colour fallbacks."""

    def __init__(self):
        self.enabled = not os.environ.get('NO_COLOR') and _supports_colour_output()
        self.truecolor = _supports_truecolor()

    def fg(self, role):
        name = SEMANTIC.get(role, role)
        if not self.enabled:
            return ''
        if self.truecolor and name in PRIMITIVE:
            red, green, blue = PRIMITIVE[name]
            return f'\x1b[38;2;{red};{green};{blue}m'
        return f'\x1b[38;5;{FALLBACK_256.get(role, 252)}m'

    def bg(self, role):
        name = SEMANTIC.get(role, role)
        if not self.enabled:
            return ''
        if self.truecolor and name in PRIMITIVE:
            red, green, blue = PRIMITIVE[name]
            return f'\x1b[48;2;{red};{green};{blue}m'
        return f'\x1b[48;5;{FALLBACK_256.get(role, 234)}m'

    def paint(self, text, role=None, bold=False, dim=False):
        if not self.enabled or not text:
            return text
        codes = self.fg(role) if role else ''
        if bold:
            codes += '\x1b[1m'
        if dim:
            codes += '\x1b[2m'
        if not codes:
            return text
        return f'{codes}{text}{RESET_FG}'

    def line(self, text, width):
        if not self.enabled:
            return pad(text, width)
        return f"{self.bg('bg')}{pad(text, width)}{RESET}"


def _supports_colour_output():
    try:
        return bool(sys.stdout and sys.stdout.isatty())
    except (AttributeError, OSError):
        return False


def visible_len(text):
    return len(ANSI_RE.sub('', text))


def pad(text, width):
    return text + ' ' * max(0, width - visible_len(text))


def truncate(text, width):
    if width <= 0:
        return ''
    if visible_len(text) <= width:
        return text
    plain = ANSI_RE.sub('', text)
    return plain[: max(0, width - 1)] + '…'


def shorten_path(text, width):
    text = str(text)
    if len(text) <= width:
        return text
    if width <= 1:
        return text[-width:]
    return '…' + text[-(width - 1):]


def wrap(text, width):
    if width <= 0:
        return ['']
    return textwrap.wrap(
        text,
        width=width,
        break_long_words=True,
        break_on_hyphens=False,
    ) or ['']


def pack_footer(text, width):
    """Wrap a shortcut footer without splitting or dangling an item.

    Footers are ``A ... · B ... · C ...``. Pack whole items per line and keep
    the separator between items, so a narrow terminal never shows ``Q`` on one
    line and ``выход`` on the next.
    """
    if width <= 0:
        return ['']

    parts = [part.strip() for part in re.split(r'\s+·\s+', text) if part.strip()]
    if not parts:
        return ['']

    lines = []
    current = ''
    for part in parts:
        candidate = f'{current} · {part}' if current else part
        if len(candidate) <= width:
            current = candidate
            continue

        if current:
            lines.append(current)
            current = ''

        if len(part) <= width:
            current = part
        else:
            wrapped = wrap(part, width)
            lines.extend(wrapped[:-1])
            current = wrapped[-1]

    if current:
        lines.append(current)
    return lines or ['']


def box(title, body, width, theme):
    width = max(24, width)
    inner = width - 4
    lines = []

    if title:
        label = truncate(f' {title} ', inner)
        top = '╭─' + label + '─' * max(0, width - 3 - visible_len(label)) + '╮'
    else:
        top = '╭' + '─' * (width - 2) + '╮'

    lines.append(theme.paint(top, 'border'))
    for line in body:
        line = truncate(line, inner)
        lines.append(
            theme.paint('│', 'border')
            + ' '
            + pad(line, inner)
            + ' '
            + theme.paint('│', 'border')
        )
    lines.append(theme.paint('╰' + '─' * (width - 2) + '╯', 'border'))
    return lines


def human_size(size):
    value = float(size)
    for unit in ('B', 'KB', 'MB', 'GB'):
        if value < 1024 or unit == 'GB':
            if unit == 'B':
                return f'{int(value)} {unit}'
            return f'{value:.1f} {unit}'
        value /= 1024
    return f'{value:.1f} GB'


def column_letter(number):
    letters = ''
    while number:
        number, remainder = divmod(number - 1, 26)
        letters = chr(ord('A') + remainder) + letters
    return letters


def terminal_geometry(fallback=(80, 24)):
    """Return the live console size for layout.

    Paint exactly this many columns: the TUI advances rows by filling each
    line to the terminal width (no embedded newlines). A hard min/max width
    previously forced wrapping on narrow consoles and left dead space on wide
    ones; resize must re-query this every frame.
    """
    cols, rows = shutil.get_terminal_size(fallback)
    return max(24, int(cols)), max(8, int(rows))


class Terminal:
    """Raw single-key reader for POSIX and Windows consoles."""

    def __enter__(self):
        self._fd = None
        self._old = None
        if os.name != 'nt':
            import termios
            import tty

            self._fd = sys.stdin.fileno()
            self._old = termios.tcgetattr(self._fd)
            tty.setraw(self._fd)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._old is not None:
            import termios

            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old)

    def read_key(self, timeout=None):
        """Read one key. If ``timeout`` (seconds) is set and nothing arrives, return ``None``."""
        if os.name == 'nt':
            return self._read_windows(timeout=timeout)
        return self._read_posix(timeout=timeout)

    def _read_posix(self, timeout=None):
        if timeout is not None:
            ready, _, _ = select.select([self._fd], [], [], timeout)
            if not ready:
                return None

        first = os.read(self._fd, 1)
        if not first:
            return 'QUIT'

        if first == b'\x1b':
            sequence = b''
            while select.select([self._fd], [], [], 0.02)[0]:
                sequence += os.read(self._fd, 1)
                if len(sequence) >= 2:
                    break
            return {
                b'[A': 'UP',
                b'OA': 'UP',
                b'[B': 'DOWN',
                b'OB': 'DOWN',
                b'[C': 'RIGHT',
                b'OC': 'RIGHT',
                b'[D': 'LEFT',
                b'OD': 'LEFT',
            }.get(sequence, 'ESC')

        if first in (b'\r', b'\n'):
            return 'ENTER'
        if first == b'\x03':
            return 'CTRL_C'
        if first == b'\x15':
            return 'CTRL_U'
        if first == b'\x17':
            return 'CTRL_W'
        if first in (b'\x7f', b'\x08'):
            return 'BACKSPACE'
        try:
            return first.decode('utf-8')
        except UnicodeDecodeError:
            return ''

    def _read_windows(self, timeout=None):
        import msvcrt

        if timeout is not None:
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if msvcrt.kbhit():
                    break
                time.sleep(0.02)
            else:
                return None

        char = msvcrt.getwch()
        if char in ('\x00', '\xe0'):
            second = msvcrt.getwch()
            return {
                'H': 'UP',
                'P': 'DOWN',
                'K': 'LEFT',
                'M': 'RIGHT',
            }.get(second, '')
        if char == '\r':
            return 'ENTER'
        if char == '\x1b':
            return 'ESC'
        if char == '\x03':
            return 'CTRL_C'
        if char == '\x15':
            return 'CTRL_U'
        if char == '\x17':
            return 'CTRL_W'
        if char == '\x08':
            return 'BACKSPACE'
        return char


def _enable_windows_ansi():
    if os.name != 'nt':
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


class App:
    def __init__(self, lang=None):
        self.base_dir = application_dir()
        self.lang = lang if lang in TEXT else detect_language()
        self.theme = Theme()
        self.screen = 'home'
        self.notice = None
        self.term = None
        self.result_entries = self._load_results()
        self.result_index = max(0, len(self.result_entries) - 1)
        self.result_offset = 0
        self.progress = []
        self.run_state = 'idle'
        self.run_result = None
        self.run_error = None
        self.run_elapsed = 0.0
        self.tool_output = []
        self.config = None
        self.config_error = None
        self.reload_config()

    @property
    def t(self):
        return TEXT[self.lang]

    def reload_config(self):
        """Load config.json when present, otherwise auto-detect the workbook."""
        self.config, self.config_error, _source = app_config.load_config(
            self.base_dir
        )

    def run(self):
        _enable_windows_ansi()
        if hasattr(sys.stdout, 'reconfigure'):
            try:
                sys.stdout.reconfigure(encoding='utf-8')
                sys.stdin.reconfigure(encoding='utf-8')
            except (AttributeError, OSError):
                pass

        try:
            with Terminal() as terminal:
                self.term = terminal
                sys.stdout.write('\x1b[?1049h\x1b[?25l\x1b[2J')
                dirty = True
                last_size = None
                while self.screen != 'quit':
                    size = terminal_geometry()
                    if size != last_size:
                        last_size = size
                        dirty = True
                    if dirty:
                        self.draw()
                        dirty = False
                    key = terminal.read_key(timeout=0.2)
                    if key is None:
                        continue
                    self.handle_key(key)
                    dirty = True
        finally:
            sys.stdout.write(f'{RESET}\x1b[?25h\x1b[?1049l')
            sys.stdout.flush()

    def draw(self):
        width, height = terminal_geometry()
        self.paint_lines(self.render_screen(width, height), width, height)

    def paint_lines(self, lines, width, height):
        if len(lines) > height:
            lines = lines[:height]
        while len(lines) < height:
            lines.append('')

        output = ['\x1b[2J\x1b[H']
        output.extend(self.theme.line(truncate(line, width), width) for line in lines)
        output.append(RESET)
        sys.stdout.write(''.join(output))
        sys.stdout.flush()

    def render_screen(self, width, height):
        if self.screen == 'help':
            return self.render_help(width, height)
        if self.screen == 'config':
            return self.render_config(width, height)
        if self.screen == 'results':
            return self.render_results(width, height)
        if self.screen == 'run':
            return self.render_run(width, height)
        if self.screen == 'tools':
            return self.render_tools(width, height)
        return self.render_home(width, height)

    def header(self, width):
        left = (
            self.theme.paint('◈', 'accent', bold=True)
            + '  '
            + self.theme.paint('AVATAR', 'white', bold=True)
            + '  '
            + self.theme.paint('COMBINER', 'muted')
        )
        version = self.theme.paint(f'v{__version__}', 'dim')
        inner = width - 4
        gap = max(1, inner - visible_len(left) - visible_len(version))
        return box(
            None,
            [
                left + ' ' * gap + version,
                self.theme.paint(self.t['subtitle'], 'muted'),
            ],
            width,
            self.theme,
        )

    def render_home(self, width, height):
        lines = self.header(width)
        lines.append('')
        lines.extend(self.status_box(width))
        lines.append('')
        lines.extend(self.menu_box(width))
        lines.append('')
        lines.extend(self.footer_lines(width, self.t['footer']))
        return lines

    def status_box(self, width):
        config, error = self.config, self.config_error
        inner = width - 4

        if error or not config:
            excel = self.theme.paint(self.t['config_missing'], 'error')
            sheets = '—'
        else:
            excel_name = config.get('excel_file', '—')
            excel_path = self.excel_path()
            if excel_path and excel_path.exists():
                excel = (
                    self.theme.paint('✓', 'success')
                    + ' '
                    + truncate(excel_name, inner - 10)
                )
            else:
                excel = (
                    self.theme.paint('✗', 'error')
                    + ' '
                    + truncate(excel_name, inner - 10)
                )
            parts = []
            for index, item in enumerate(config.get('sheets', {}).values()):
                nation = PLATE_NATION[index % 4]
                name = item.get('sheet_name', '—')
                parts.append(self.theme.paint(name, nation, bold=True))
            sheets = ' · '.join(parts) or '—'

        last = self.result_entries[-1] if self.result_entries else None
        last_text = (
            f"{last['name']} · {last['files']} {self.t['files']}"
            if last
            else self.t['none']
        )
        next_text = self.theme.paint(
            f"Результат {next_result_number(self.base_dir)}",
            'accent',
            bold=True,
        )

        body = [
            self.theme.paint('●', 'success') + ' ' + self.theme.paint(self.t['ready'], 'success', bold=True),
            '',
            self.label_value(self.t['excel'], excel, inner),
            self.label_value(self.t['sheets'], sheets, inner),
            self.label_value(self.t['next'], next_text, inner),
            self.label_value(self.t['last'], last_text, inner),
            '',
            self.theme.paint(self.t['run_hint'], 'dim'),
        ]
        return box(self.t['status'], body, width, self.theme)

    def menu_box(self, width):
        items = [
            ('R', '1', self.t['run'], 'accent'),
            ('D', '2', self.t['results'], 'accent2'),
            ('O', '3', self.t['open_last'], 'accent'),
            ('C', '4', self.t['config'], 'muted'),
            ('T', '7', self.t['tools'], 'accent2'),
            ('H', '5', self.t['help'], 'muted'),
            ('L', '6', f"{self.t['language']}: {self.lang.upper()}", 'warning'),
            ('Q', '0', self.t['quit'], 'error'),
        ]
        inner = width - 4
        column = max(18, (inner - 2) // 2)
        rows = []
        for index in range(0, len(items), 2):
            left = self.menu_item(items[index], column)
            right = (
                self.menu_item(items[index + 1], column)
                if index + 1 < len(items)
                else ''
            )
            rows.append(pad(left, column) + '  ' + right)
        return box(self.t['actions'], rows, width, self.theme)

    def menu_item(self, item, width):
        key, _alias, label, role = item
        return self.theme.paint(f'[{key}]', role, bold=True) + ' ' + truncate(label, width - 5)

    def label_value(self, label, value, width):
        label_width = 10
        value_width = max(8, width - label_width - 1)
        label_text = self.theme.paint(label.upper().ljust(label_width), 'dim')
        return label_text + ' ' + truncate(str(value), value_width)

    def footer_lines(self, width, text):
        lines = []
        if self.notice:
            message, role = self.notice
            for line in wrap(message, width - 4):
                lines.append(self.theme.paint('● ' + line, role, bold=True))
        for line in pack_footer(text, width - 4):
            lines.append(self.theme.paint(line, 'dim'))
        return lines

    def render_help(self, width, height):
        lines = self.header(width)
        lines.append('')
        inner = width - 4

        if width >= 96:
            column = (inner - 3) // 2
            english = self.help_column('en', column)
            russian = self.help_column('ru', column)
            for index in range(max(len(english), len(russian))):
                left = english[index] if index < len(english) else ''
                right = russian[index] if index < len(russian) else ''
                lines.append(pad(left, column) + '   ' + truncate(right, column))
        else:
            lines.extend(self.help_column(self.lang, inner))

        lines.append('')
        lines.extend(self.footer_lines(width, self.t['help_footer']))
        return lines

    def help_column(self, lang, width):
        lines = [self.theme.paint('ENGLISH' if lang == 'en' else 'РУССКИЙ', 'accent', bold=True), '']
        for title, body in HELP[lang]:
            lines.append(self.theme.paint(title, 'white', bold=True))
            for line in wrap(body, width):
                lines.append(self.theme.paint(line, 'muted'))
            lines.append('')
        return lines

    def render_config(self, width, height):
        lines = self.header(width)
        lines.append('')
        inner = width - 4
        config, error = self.config, self.config_error

        if error or not config:
            body = [
                self.theme.paint(self.t['config_missing'], 'error'),
                self.theme.paint(error or '', 'dim'),
            ]
        else:
            excel_name = config.get('excel_file', '—')
            excel_path = self.excel_path()
            excel_value = (
                self.theme.paint('✓ ', 'success')
                if excel_path and excel_path.exists()
                else self.theme.paint('✗ ', 'error')
            ) + excel_name
            parts = []
            for index, item in enumerate(config.get('sheets', {}).values()):
                nation = PLATE_NATION[index % 4]
                name = item.get('sheet_name', '—')
                parts.append(self.theme.paint(name, nation, bold=True))
            sheets = ' · '.join(parts) or '—'
            body = [
                self.label_value(self.t['folder'], self.base_dir, inner),
                self.label_value(self.t['excel'], excel_value, inner),
                self.label_value(self.t['sheets'], sheets, inner),
                self.label_value(self.t['range'], self.range_text(config), inner),
            ]

        lines.extend(box(self.t['config'], body, width, self.theme))
        lines.append('')

        actions = [
            self.theme.paint('[F]', 'accent', bold=True) + ' ' + self.t['choose_excel'],
            self.theme.paint('[S]', 'accent', bold=True) + ' ' + self.t['choose_sheets'],
            self.theme.paint('[R]', 'accent', bold=True) + ' ' + self.t['choose_range'],
            self.theme.paint('[O]', 'accent', bold=True) + ' ' + self.t['open_folder'],
            self.theme.paint('[B]', 'muted', bold=True) + ' ' + self.t['back'],
        ]
        lines.extend(box(self.t['actions'], actions, width, self.theme))
        lines.append('')
        lines.extend(self.footer_lines(width, self.t['config_footer']))
        return lines

    def render_tools(self, width, height):
        lines = self.header(width)
        lines.append('')
        inner = width - 4
        if self.tool_output and height < 30:
            lines.append(self.theme.paint(self.t['tools'], 'dim', bold=True))
            tools = [
                ('1', self.t['tool_tm']),
                ('2', self.t['tool_pair']),
                ('3', self.t['tool_dna']),
                ('4', self.t['tool_units']),
                ('5', self.t['tool_structure']),
                ('6', self.t['tool_layout']),
                ('7', self.t['tool_pcr']),
                ('8', self.t['tool_xlsx']),
                ('9', self.t['tool_gradient']),
                ('B', self.t['back']),
            ]
            listing = ' · '.join(f'{key} {label}' for key, label in tools)
            for line in wrap(listing, inner):
                lines.append(self.theme.paint(line, 'muted'))
        else:
            actions = [
                self.theme.paint(self.t['group_inspect'], 'dim', bold=True),
                self.tool_menu_row(
                    [('1', self.t['tool_tm'], 'accent'), ('2', self.t['tool_pair'], 'accent')],
                    inner,
                ),
                self.tool_menu_row(
                    [('3', self.t['tool_dna'], 'accent'), ('4', self.t['tool_units'], 'accent')],
                    inner,
                ),
                '',
                self.theme.paint(self.t['group_structure'], 'dim', bold=True),
                self.tool_menu_row(
                    [
                        ('5', self.t['tool_structure'], 'accent2'),
                        ('7', self.t['tool_pcr'], 'accent2'),
                    ],
                    inner,
                ),
                self.tool_menu_row(
                    [('9', self.t['tool_gradient'], 'accent2')],
                    inner,
                ),
                '',
                self.theme.paint(self.t['group_files'], 'dim', bold=True),
                self.tool_menu_row(
                    [
                        ('6', self.t['tool_layout'], 'accent2'),
                        ('8', self.t['tool_xlsx'], 'accent2'),
                    ],
                    inner,
                ),
                '',
                self.theme.paint('[B]', 'muted', bold=True) + ' ' + self.t['back'],
            ]
            lines.extend(box(self.t['tools'], actions, width, self.theme))

        if self.tool_output:
            lines.append('')
            lines.extend(box(self.t['tool_result'], self.tool_output, width, self.theme))

        if height - len(lines) >= 2:
            lines.append('')
            lines.extend(self.footer_lines(width, self.t['tool_footer']))
        return lines

    def tool_menu_row(self, items, width):
        column = max(20, (width - 2) // 2)
        cells = [
            self.menu_item((key, '', label, role), column)
            for key, label, role in items
        ]
        return pad(cells[0], column) + '  ' + (cells[1] if len(cells) > 1 else '')

    def prompt_text(self, title, hint=None, max_length=120):
        value = ''
        while True:
            width, height = terminal_geometry()

            lines = self.header(width)
            lines.append('')
            field = self.theme.paint(value, 'accent', bold=True) + '▌'
            lines.extend(box(title, [field], width, self.theme))
            lines.append('')
            footer = hint or ''
            if footer:
                footer += '  ·  '
            lines.extend(
                self.footer_lines(width, footer + self.t['prompt_footer'])
            )
            self.paint_lines(lines, width, height)

            key = self.term.read_key(timeout=0.2)
            if key is None:
                continue
            if key in ('ESC', 'CTRL_C'):
                return None
            if key == 'ENTER':
                return value.strip()
            if key == 'BACKSPACE':
                value = value[:-1]
            elif key == 'CTRL_U':
                value = ''
            elif key == 'CTRL_W':
                value = re.sub(r'\S+\s*$', '', value)
            elif len(key) == 1 and key.isprintable() and len(value) < max_length:
                value += key

    def tool_line(self, label, value, upper=True):
        text = str(label).upper() if upper else str(label)
        return self.theme.paint(text.ljust(12), 'dim') + ' ' + str(value)

    def tool_sequence_lines(self, label, sequence):
        # 40 nt + 13-column label indent fits the 56-column inner box at width 60.
        chunks = [sequence[i:i + 40] for i in range(0, len(sequence), 40)] or ['']
        lines = [self.tool_line(label, chunks[0])]
        for chunk in chunks[1:]:
            lines.append(self.theme.paint(' ' * 13, 'dim') + chunk)
        return lines

    def tool_rows(self, rows, long_keys=()):
        lines = []
        for key, value in rows:
            if value is None:
                value = self.t['no_structure']
            if key in long_keys:
                lines.extend(self.tool_sequence_lines(self.t[key], value))
            else:
                lines.append(self.tool_line(self.t[key], value))
        return lines

    def tool_preview_lines(self, label, sequence):
        """Show the first 240 nt; the TUI has no scrolling in v1."""
        lines = self.tool_sequence_lines(label, sequence[:240])
        remaining = len(sequence) - 240
        if remaining > 0:
            lines.append(self.theme.paint(f'… +{remaining} nt', 'dim'))
        return lines

    def set_tool_error(self, exc):
        self.tool_output = [self.theme.paint(f'✗ {exc}', 'error')]

    def tool_primer_tm(self):
        self.tool_output = []
        sequence = self.prompt_text(self.t['tool_tm'], self.t['primer_hint'])
        if sequence is None:
            return
        try:
            report = genetics.analyze_primer(sequence)
        except (genetics.ToolError, OSError, ImportError) as exc:
            self.set_tool_error(exc)
            return
        self.tool_output = self.tool_rows(
            tool_reports.primer_rows(report), {'sequence'}
        )

    def tool_pair(self):
        self.tool_output = []
        forward = self.prompt_text(self.t['forward'], self.t['primer_hint'])
        if forward is None:
            return
        reverse = self.prompt_text(self.t['reverse_primer'], self.t['primer_hint'])
        if reverse is None:
            return
        try:
            report = genetics.analyze_pair(forward, reverse)
        except (genetics.ToolError, OSError, ImportError) as exc:
            self.set_tool_error(exc)
            return
        self.tool_output = self.tool_rows(
            tool_reports.pair_rows(report), {'forward', 'reverse_primer'}
        )

    def tool_dna(self):
        self.tool_output = []
        sequence = self.prompt_text(self.t['tool_dna'], self.t['dna_hint'])
        if sequence is None:
            return
        try:
            rows = tool_reports.dna_rows(sequence)
        except (genetics.ToolError, OSError, ImportError) as exc:
            self.set_tool_error(exc)
            return

        self.tool_output = self.tool_rows(
            rows,
            {'sequence', 'complement', 'reverse_seq', 'reverse_complement'},
        )

    def tool_units(self):
        self.tool_output = []
        value = self.prompt_text(
            self.t['quantity'],
            f"{self.t['unit_hint']} {self.t['unit_list']}",
        )
        if value is None:
            return
        target = self.prompt_text(
            self.t['target_unit'],
            f"{self.t['unit_hint']} {self.t['unit_list']}",
        )
        if target is None:
            return
        try:
            rows = tool_reports.unit_rows(value, target)
        except (genetics.ToolError, OSError, ImportError) as exc:
            self.set_tool_error(exc)
            return
        self.tool_output = [
            self.tool_line(unit, amount, upper=False) for unit, amount in rows
        ]

    def tool_structure(self):
        self.tool_output = []
        sequence = self.prompt_text(self.t['tool_structure'], self.t['structure_hint'])
        if sequence is None:
            return
        try:
            report = seq_structure.analyze_structure(sequence)
        except (genetics.ToolError, OSError, ImportError) as exc:
            self.set_tool_error(exc)
            return

        self.tool_output = self.tool_rows(
            tool_reports.structure_rows(report),
            {'sequence', 'structure_fold'},
        )
        if not report.hits:
            self.tool_output.append(self.theme.paint(self.t['structure_none'], 'dim'))

    def tool_layout(self):
        self.tool_output = []
        path = self.prompt_text(self.t['tool_layout'], self.t['layout_hint'])
        if path is None:
            return
        try:
            report = plate_layout.load_layout(path)
        except (genetics.ToolError, OSError, ImportError) as exc:
            self.set_tool_error(exc)
            return

        self.tool_output = self.tool_rows(tool_reports.layout_rows(report))

    def tool_pcr(self):
        self.tool_output = []
        prompts = (
            (self.t['pcr_template'], self.t['pcr_hint'], {'max_length': 10000}),
            (self.t['pcr_forward'], self.t['pcr_primer_hint'], {}),
            (self.t['pcr_reverse'], self.t['pcr_primer_hint'], {}),
        )
        values = []
        for title, hint, options in prompts:
            value = self.prompt_text(title, hint, **options)
            if value is None:
                return
            values.append(value)
        try:
            report = pcr_tools.simulate_pcr(*values)
        except (genetics.ToolError, OSError, ImportError) as exc:
            self.set_tool_error(exc)
            return

        rows = [row for row in tool_reports.pcr_rows(report) if row[0] != 'sequence']
        self.tool_output = self.tool_rows(rows)
        self.tool_output.extend(
            self.tool_preview_lines(self.t['sequence'], report.sequence)
        )

    def tool_gradient(self):
        self.tool_output = []
        back = self.prompt_text(self.t['gradient_back'], self.t['gradient_hint'])
        if back is None:
            return
        front = self.prompt_text(self.t['gradient_front'], self.t['gradient_hint'])
        if front is None:
            return
        try:
            report = genetics.block_gradient(back, front)
        except (genetics.ToolError, OSError, ImportError) as exc:
            self.set_tool_error(exc)
            return
        self.tool_output = [
            self.tool_line(letter, value, upper=False)
            for letter, value in tool_reports.gradient_rows(report)
        ]

    def tool_xlsx(self):
        self.tool_output = []
        path = self.prompt_text(self.t['tool_xlsx'], self.t['xlsx_hint'])
        if path is None:
            return
        try:
            output = report_xlsx.export_workbook(path)
        except (genetics.ToolError, OSError, ImportError) as exc:
            self.set_tool_error(exc)
            return

        self.tool_output = [
            self.tool_line(self.t['xlsx_done'], str(output)),
        ]

    def render_results(self, width, height):
        lines = self.header(width)
        lines.append('')

        entries = self.result_entries
        if not entries:
            body = [
                self.theme.paint(self.t['no_results'], 'muted'),
                '',
                self.theme.paint(self.t['run_hint'], 'dim'),
            ]
            lines.extend(box(self.t['results'], body, width, self.theme))
        else:
            max_items = max(3, height - 12)
            self.clamp_result_view(max_items)
            visible = entries[self.result_offset:self.result_offset + max_items]
            body = []
            for index, entry in enumerate(visible, start=self.result_offset):
                selected = index == self.result_index
                marker = '›' if selected else ' '
                meta = (
                    f"{entry['files']} {self.t['files']} · "
                    f"{human_size(entry['size'])} · {entry['mtime']}"
                )
                line = f"{marker} {entry['name']:<14} {meta}"
                body.append(
                    self.theme.paint(line, 'accent', bold=True)
                    if selected
                    else line
                )
            lines.extend(box(self.t['results'], body, width, self.theme))
            lines.append('')
            selected_entry = entries[self.result_index]
            lines.append(
                self.theme.paint(
                    shorten_path(selected_entry['path'], width - 4),
                    'dim',
                )
            )
            lines.append(
                self.theme.paint(
                    f"{self.result_index + 1}/{len(entries)}",
                    'muted',
                )
            )

        lines.append('')
        lines.extend(self.footer_lines(width, self.t['results_footer']))
        return lines

    def render_run(self, width, height):
        lines = self.header(width)
        lines.append('')
        inner = width - 4

        state_label = {
            'running': self.t['working'],
            'done': self.t['done'],
            'error': self.t['error'],
        }.get(self.run_state, self.t['working'])
        state_role = {
            'running': 'accent',
            'done': 'success',
            'error': 'error',
        }.get(self.run_state, 'accent')

        lines.append(
            self.theme.paint('● ', state_role, bold=True)
            + self.theme.paint(state_label, state_role, bold=True)
        )

        if self.run_result is not None:
            lines.append(self.label_value(self.t['run_result'], self.run_result, inner))
            if self.run_elapsed:
                lines.append(
                    self.label_value(
                        self.t['time'],
                        f'{self.run_elapsed:.2f} s',
                        inner,
                    )
                )
        if self.run_error:
            for line in wrap(self.run_error, inner):
                lines.append(self.theme.paint(line, 'error'))

        lines.append('')
        max_lines = max(4, height - 14)
        for message in self.progress[-max_lines:]:
            lines.append(self.theme.paint('│ ', 'dim') + message)

        if self.run_state != 'running':
            lines.append('')
            lines.append(self.theme.paint(self.t['press_any'], 'dim'))
        return lines

    def handle_key(self, key):
        if key == 'CTRL_C' or key in ('q', 'Q', '0'):
            self.screen = 'quit'
            return

        if key in ('l', 'L'):
            self.lang = 'en' if self.lang == 'ru' else 'ru'
            self.notice = None
            return

        if key in ('?',):
            self.screen = 'help'
            return

        if key == 'ESC' and self.screen in ('help', 'config', 'results', 'tools'):
            self.screen = 'home'
            return

        if self.screen == 'home':
            self.handle_home_key(key)
        elif self.screen == 'help':
            if key in ('b', 'B', 'h', 'H', '5'):
                self.screen = 'home'
        elif self.screen == 'config':
            if key in ('b', 'B'):
                self.screen = 'home'
            elif key in ('f', 'F', 'e', 'E', 'ENTER'):
                self.edit_excel()
            elif key in ('s', 'S'):
                self.edit_sheets()
            elif key in ('r', 'R'):
                self.edit_range()
            elif key in ('o', 'O'):
                self.open_path(self.base_dir)
        elif self.screen == 'results':
            self.handle_results_key(key)
        elif self.screen == 'tools':
            self.handle_tools_key(key)

    def handle_home_key(self, key):
        if key in ('r', 'R', 'ENTER', '1'):
            self.do_run()
        elif key in ('d', 'D', '2'):
            self.open_results()
        elif key in ('o', 'O', '3'):
            self.open_latest()
        elif key in ('c', 'C', '4'):
            self.screen = 'config'
        elif key in ('t', 'T', '7'):
            self.screen = 'tools'
            self.tool_output = []
        elif key in ('h', 'H', '5'):
            self.screen = 'help'

    def handle_tools_key(self, key):
        if key in ('b', 'B'):
            self.screen = 'home'
        elif key == '1':
            self.tool_primer_tm()
        elif key == '2':
            self.tool_pair()
        elif key == '3':
            self.tool_dna()
        elif key == '4':
            self.tool_units()
        elif key == '5':
            self.tool_structure()
        elif key == '6':
            self.tool_layout()
        elif key == '7':
            self.tool_pcr()
        elif key == '8':
            self.tool_xlsx()
        elif key == '9':
            self.tool_gradient()

    def handle_results_key(self, key):
        if key in ('b', 'B'):
            self.screen = 'home'
        elif key in ('UP', 'k', 'K'):
            self.move_result(-1)
        elif key in ('DOWN', 'j', 'J'):
            self.move_result(1)
        elif key in ('o', 'O', 'ENTER'):
            self.open_selected_result()
        elif key in ('c', 'C'):
            self.copy_result_columns()
        elif key in ('r', 'R'):
            self.do_run()

    def copy_result_columns(self):
        """Copy plate*_column.txt from the selected result (A1–H12 row-major)."""
        if not self.result_entries:
            self.notice = (self.t['no_results'], 'warning')
            return
        folder = Path(self.result_entries[self.result_index]['path'])
        blocks = []
        for key in app_config.PLATE_KEYS:
            path = folder / f'{key}_column.txt'
            if not path.is_file():
                continue
            values = path.read_text(encoding='utf-8').splitlines()
            blocks.append((key, values))
        if not blocks:
            self.notice = (self.t['extract_empty'], 'warning')
            return
        text = extract_plates.format_observations(blocks, include_headers=True)
        if copy_text_to_clipboard(text):
            self.notice = (
                f"{self.t['extract_copied']}: {folder.name} ({len(blocks)})",
                'success',
            )
        else:
            # Fallback: keep a paste-ready file next to the result.
            fallback = folder / 'plates_column_clipboard.txt'
            fallback.write_text(text + '\n', encoding='utf-8')
            self.notice = (f"{self.t['clipboard_failed']}: {fallback.name}", 'warning')

    def do_run(self):
        if not self.config:
            self.notice = (self.config_error or self.t['config_missing'], 'error')
            return

        self.screen = 'run'
        self.run_state = 'running'
        self.progress = []
        self.run_result = None
        self.run_error = None
        self.run_elapsed = 0.0
        self.notice = None
        self.draw()

        error_buffer = io.StringIO()
        started = time.monotonic()

        try:
            with redirect_stderr(error_buffer):
                result = run_pipeline.run(
                    base_dir=self.base_dir,
                    config=self.config,
                    log=self.on_log,
                )
            self.run_result = result
            self.run_state = 'done'
            self.notice = (f"{self.t['last']}: {result.name}", 'success')
        except (run_pipeline.PipelineError, OSError) as exc:
            self.run_state = 'error'
            self.run_error = str(exc)
            self.notice = (str(exc), 'error')

        self.run_elapsed = time.monotonic() - started
        self.result_entries = self._load_results()
        self.result_index = max(0, len(self.result_entries) - 1)
        self.draw()

        if self.term is not None:
            self.term.read_key()

        self.screen = 'home'

    def on_log(self, message):
        text = str(message).rstrip()
        if not text or not text.strip('=').strip():
            return
        self.progress.append(text)
        if len(self.progress) > 500:
            self.progress = self.progress[-500:]
        self.draw()

    def open_results(self):
        self.result_entries = self._load_results()
        self.result_index = max(0, len(self.result_entries) - 1)
        self.result_offset = 0
        self.screen = 'results'

    def move_result(self, delta):
        if not self.result_entries:
            return
        self.result_index = max(0, min(len(self.result_entries) - 1, self.result_index + delta))

    def clamp_result_view(self, max_items):
        if self.result_index < self.result_offset:
            self.result_offset = self.result_index
        elif self.result_index >= self.result_offset + max_items:
            self.result_offset = self.result_index - max_items + 1

    def open_latest(self):
        if self.result_entries:
            self.open_path(self.result_entries[-1]['path'])
        else:
            self.notice = (self.t['no_results'], 'warning')

    def open_selected_result(self):
        if self.result_entries:
            self.open_path(self.result_entries[self.result_index]['path'])

    def excel_path(self):
        if not self.config:
            return None
        path = Path(self.config.get('excel_file', ''))
        return path if path.is_absolute() else self.base_dir / path

    def edit_excel(self):
        candidates = app_config.discover_excel(self.base_dir)
        hint = ', '.join(path.name for path in candidates) or self.t['excel_hint']
        text = self.prompt_text(self.t['choose_excel'], hint)
        if text is None:
            return

        path = text
        if text.isdigit() and 1 <= int(text) <= len(candidates):
            path = candidates[int(text) - 1]

        try:
            config = app_config.build_config(self.base_dir, excel_file=path)
        except (app_config.ConfigError, OSError, ValueError) as exc:
            self.notice = (str(exc), 'error')
            return
        self.config = config
        self.config_error = None
        self.notice = (f"{self.t['excel']}: {config['excel_file']}", 'success')

    def edit_sheets(self):
        if not self.config:
            self.notice = (self.t['config_missing'], 'error')
            return
        try:
            available = app_config.sheet_names(self.excel_path())
        except (app_config.ConfigError, OSError, ValueError) as exc:
            self.notice = (str(exc), 'error')
            return

        text = self.prompt_text(
            self.t['choose_sheets'],
            ', '.join(f'{index} {name}' for index, name in enumerate(available, 1)),
        )
        if text is None:
            return
        parts = [
            part.strip()
            for part in (text.split(',') if ',' in text else text.split())
            if part.strip()
        ]
        if parts and all(part.isdigit() for part in parts):
            numbers = [int(part) for part in parts]
            if any(number < 1 or number > len(available) for number in numbers):
                self.notice = (self.t['bad_selection'], 'error')
                return
            names = [available[number - 1] for number in numbers]
        else:
            names = parts
        try:
            config = app_config.build_config(
                self.base_dir,
                excel_file=self.excel_path(),
                sheets=names,
                data_range=self.config.get('data_range'),
            )
        except (app_config.ConfigError, OSError, ValueError) as exc:
            self.notice = (str(exc), 'error')
            return

        self.config = config
        self.config_error = None
        self.notice = (f"{self.t['sheets']}: {', '.join(names)}", 'success')

    def edit_range(self):
        if not self.config:
            self.notice = (self.t['config_missing'], 'error')
            return
        text = self.prompt_text(self.t['choose_range'], self.range_text(self.config))
        if text is None:
            return
        try:
            data_range = app_config.parse_range(text)
        except (app_config.ConfigError, ValueError) as exc:
            self.notice = (str(exc), 'error')
            return

        config = dict(self.config)
        config['data_range'] = data_range
        self.config = config
        self.notice = (f"{self.t['range']}: {self.range_text(config)}", 'success')

    def open_path(self, path):
        path = Path(path)
        try:
            if os.name == 'nt':
                os.startfile(str(path))
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', str(path)])
            else:
                if not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
                    self.notice = (self.t['no_desktop'], 'warning')
                    return
                subprocess.Popen(
                    ['xdg-open', str(path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            self.notice = (f"{self.t['opened']}: {path.name}", 'success')
        except Exception as exc:
            self.notice = (f"{self.t['open_failed']}: {exc}", 'error')

    def _load_results(self):
        entries = []
        if not self.base_dir.exists():
            return entries

        for path in self.base_dir.iterdir():
            if not path.is_dir() or not RESULT_PATTERN.match(path.name):
                continue
            try:
                files = [item for item in path.iterdir() if item.is_file()]
                size = sum(item.stat().st_size for item in files)
                modified = max(
                    (item.stat().st_mtime for item in files),
                    default=path.stat().st_mtime,
                )
            except OSError:
                continue
            entries.append(
                {
                    'path': path,
                    'name': path.name,
                    'number': int(RESULT_PATTERN.match(path.name).group(1) or 1),
                    'files': len(files),
                    'size': size,
                    'mtime': time.strftime('%d.%m %H:%M', time.localtime(modified)),
                }
            )
        entries.sort(key=lambda entry: entry['number'])
        return entries

    def range_text(self, config):
        data_range = config.get('data_range', {})
        start_row = data_range.get('start_row', '?')
        end_row = data_range.get('end_row', '?')
        start_col = data_range.get('start_col', 1)
        end_col = data_range.get('end_col', 1)
        return f"{column_letter(start_col)}{start_row}:{column_letter(end_col)}{end_row}"
