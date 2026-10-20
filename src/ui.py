"""Lightweight terminal UI for the plate combiner.

No third-party packages: ANSI styling, raw-key input and layout are stdlib only.
The palette follows a small three-layer token model: primitive colours →
semantic roles → components/screens.
"""

import io
import json
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

import run_pipeline
from run_pipeline import __version__, application_dir, next_result_number

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
}

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
}

RESET = '\x1b[0m'
RESET_FG = '\x1b[39m\x1b[22m'
ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')


TEXT = {
    'en': {
        'subtitle': '4 × 96-well plates  →  1 × 384-well plate',
        'status': 'STATUS',
        'ready': 'READY',
        'excel': 'Excel',
        'sheets': 'Sheets',
        'next': 'Next',
        'last': 'Last',
        'none': 'none',
        'actions': 'ACTIONS',
        'run': 'Run pipeline',
        'results': 'Results',
        'open_last': 'Open last result',
        'config': 'Config',
        'help': 'Help',
        'language': 'Language',
        'quit': 'Quit',
        'back': 'Back',
        'footer': 'R run  ·  D results  ·  O open  ·  C config  ·  H help  ·  L language  ·  Q quit',
        'help_footer': 'L switch language  ·  B back  ·  Q quit',
        'config_footer': 'E edit config  ·  O open folder  ·  B back',
        'results_footer': '↑↓ select  ·  Enter/O open  ·  R run  ·  B back',
        'no_results': 'No result folders yet. Press R to run.',
        'run_hint': 'Each run creates a new «Результат N» folder.',
        'working': 'RUNNING',
        'done': 'DONE',
        'error': 'ERROR',
        'press_any': 'Press any key to return',
        'open_folder': 'Open program folder',
        'edit_config': 'Open config.json',
        'range': 'Range',
        'opened': 'Opened',
        'open_failed': 'Could not open',
        'config_missing': 'config.json not found',
        'files': 'files',
        'folder': 'Folder',
        'run_result': 'Result',
        'time': 'Time',
        'ids': 'IDs',
        'no_desktop': 'No desktop session; open the path manually',
    },
    'ru': {
        'subtitle': '4 планшета × 96 лунок  →  1 планшет × 384 лунки',
        'status': 'СТАТУС',
        'ready': 'ГОТОВО',
        'excel': 'Excel',
        'sheets': 'Листы',
        'next': 'Далее',
        'last': 'Последний',
        'none': 'нет',
        'actions': 'ДЕЙСТВИЯ',
        'run': 'Запустить',
        'results': 'Результаты',
        'open_last': 'Открыть последний',
        'config': 'Настройки',
        'help': 'Помощь',
        'language': 'Язык',
        'quit': 'Выход',
        'back': 'Назад',
        'footer': 'R запуск  ·  D результаты  ·  O открыть  ·  C настройки  ·  H помощь  ·  Q выход',
        'help_footer': 'L сменить язык  ·  B назад  ·  Q выход',
        'config_footer': 'E открыть config  ·  O открыть папку  ·  B назад',
        'results_footer': '↑↓ выбор  ·  Enter/O открыть  ·  R запуск  ·  B назад',
        'no_results': 'Папок результатов пока нет. Нажмите R.',
        'run_hint': 'Каждый запуск создаёт новую папку «Результат N».',
        'working': 'РАБОТА',
        'done': 'ГОТОВО',
        'error': 'ОШИБКА',
        'press_any': 'Нажмите любую клавишу',
        'open_folder': 'Открыть папку программы',
        'edit_config': 'Открыть config.json',
        'range': 'Диапазон',
        'opened': 'Открыто',
        'open_failed': 'Не удалось открыть',
        'config_missing': 'config.json не найден',
        'files': 'файлов',
        'folder': 'Папка',
        'run_result': 'Результат',
        'time': 'Время',
        'ids': 'ID',
        'no_desktop': 'Нет графической сессии; откройте путь вручную',
    },
}


HELP = {
    'en': [
        ('Run', 'Press R or Enter. A new «Результат N» folder is created and every output is written there.'),
        ('Outputs', 'plate1-4.csv, metadata.csv, combined_384_plate.csv, combined_384_plate_pivot.csv and combined_384_plate_ids.txt.'),
        ('Config', 'config.json sets the Excel file and the four sheet names. Keep it next to the exe.'),
        ('Quick keys', 'R run · D results · O open last · C config · H help · L language · Q quit. Arrow keys move, Enter confirms.'),
        ('CFX', 'Paste combined_384_plate_ids.txt into Bio-Rad CFX Manager 3.1.'),
        ('Size', 'Runtime uses only the Python standard library: no pandas, numpy or openpyxl.'),
    ],
    'ru': [
        ('Запуск', 'Нажмите R или Enter. Будет создана папка «Результат N», в неё попадут все файлы.'),
        ('Результаты', 'plate1-4.csv, metadata.csv, combined_384_plate.csv, combined_384_plate_pivot.csv и combined_384_plate_ids.txt.'),
        ('Настройка', 'config.json задаёт Excel-файл и имена четырёх листов. Держите его рядом с exe.'),
        ('Быстрые клавиши', 'R запуск · D результаты · O открыть последний · C настройки · H помощь · L язык · Q quit. Стрелки — выбор, Enter — подтвердить.'),
        ('CFX', 'Вставьте combined_384_plate_ids.txt в Bio-Rad CFX Manager 3.1.'),
        ('Размер', 'В рантайме только стандартная библиотека Python: без pandas, numpy и openpyxl.'),
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

    def read_key(self):
        if os.name == 'nt':
            return self._read_windows()
        return self._read_posix()

    def _read_posix(self):
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
        if first in (b'\x7f', b'\x08'):
            return 'BACKSPACE'
        try:
            return first.decode('utf-8')
        except UnicodeDecodeError:
            return ''

    def _read_windows(self):
        import msvcrt

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

    @property
    def t(self):
        return TEXT[self.lang]

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
                while self.screen != 'quit':
                    self.draw()
                    self.handle_key(terminal.read_key())
        finally:
            sys.stdout.write(f'{RESET}\x1b[?25h\x1b[?1049l')
            sys.stdout.flush()

    def draw(self):
        width, height = shutil.get_terminal_size((100, 30))
        width = max(60, min(width, 118))
        height = max(20, height)

        lines = self.render_screen(width, height)
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
        config, error = self._load_config()
        inner = width - 4

        if error:
            excel = self.theme.paint(self.t['config_missing'], 'error')
            sheets = '—'
        else:
            excel_name = config.get('excel_file', '—')
            excel_path = self.base_dir / excel_name
            if excel_path.exists():
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
            sheets = ' · '.join(
                item.get('sheet_name', '—')
                for item in config.get('sheets', {}).values()
            ) or '—'

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
        for line in wrap(text, width - 4):
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
        config, error = self._load_config()

        if error:
            body = [self.theme.paint(self.t['config_missing'], 'error'), self.theme.paint(error, 'dim')]
        else:
            excel_name = config.get('excel_file', '—')
            excel_path = self.base_dir / excel_name
            excel_value = (
                self.theme.paint('✓ ', 'success')
                if excel_path.exists()
                else self.theme.paint('✗ ', 'error')
            ) + excel_name
            sheets = ' · '.join(
                item.get('sheet_name', '—')
                for item in config.get('sheets', {}).values()
            ) or '—'
            body = [
                self.label_value(self.t['folder'], self.base_dir, inner),
                self.label_value(self.t['config'], self.base_dir / 'config.json', inner),
                self.label_value(self.t['excel'], excel_value, inner),
                self.label_value(self.t['sheets'], sheets, inner),
                self.label_value(self.t['range'], self.range_text(config), inner),
            ]

        lines.extend(box(self.t['config'], body, width, self.theme))
        lines.append('')

        actions = [
            self.theme.paint('[E]', 'accent', bold=True) + ' ' + self.t['edit_config'],
            self.theme.paint('[O]', 'accent', bold=True) + ' ' + self.t['open_folder'],
            self.theme.paint('[B]', 'muted', bold=True) + ' ' + self.t['back'],
        ]
        lines.extend(box(self.t['actions'], actions, width, self.theme))
        lines.append('')
        lines.extend(self.footer_lines(width, self.t['config_footer']))
        return lines

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

        if key == 'ESC' and self.screen in ('help', 'config', 'results'):
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
            elif key in ('e', 'E', 'ENTER'):
                self.open_config()
            elif key in ('o', 'O'):
                self.open_path(self.base_dir)
        elif self.screen == 'results':
            self.handle_results_key(key)

    def handle_home_key(self, key):
        if key in ('r', 'R', 'ENTER', '1'):
            self.do_run()
        elif key in ('d', 'D', '2'):
            self.open_results()
        elif key in ('o', 'O', '3'):
            self.open_latest()
        elif key in ('c', 'C', '4'):
            self.screen = 'config'
        elif key in ('h', 'H', '5'):
            self.screen = 'help'

    def handle_results_key(self, key):
        if key in ('b', 'B'):
            self.screen = 'home'
        elif key in ('UP', 'k', 'K'):
            self.move_result(-1)
        elif key in ('DOWN', 'j', 'J'):
            self.move_result(1)
        elif key in ('o', 'O', 'ENTER'):
            self.open_selected_result()
        elif key in ('r', 'R'):
            self.do_run()

    def do_run(self):
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
                result = run_pipeline.run(base_dir=self.base_dir, log=self.on_log)
            self.run_result = result
            self.run_state = 'done'
            self.notice = (f"{self.t['last']}: {result.name}", 'success')
        except SystemExit as exc:
            self.run_state = 'error'
            self.run_error = error_buffer.getvalue().strip() or f'Exit code {exc.code}'
            self.notice = (self.run_error.splitlines()[-1], 'error')
        except Exception as exc:
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

    def open_config(self):
        config_path = self.base_dir / 'config.json'
        if config_path.exists():
            self.open_path(config_path)
        else:
            self.notice = (self.t['config_missing'], 'warning')

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

    def _load_config(self):
        path = self.base_dir / 'config.json'
        try:
            with open(path, encoding='utf-8') as config_file:
                return json.load(config_file), None
        except (OSError, json.JSONDecodeError) as exc:
            return None, str(exc)

    def range_text(self, config):
        data_range = config.get('data_range', {})
        start_row = data_range.get('start_row', '?')
        end_row = data_range.get('end_row', '?')
        start_col = data_range.get('start_col', 1)
        end_col = data_range.get('end_col', 1)
        return f"{column_letter(start_col)}{start_row}:{column_letter(end_col)}{end_row}"
