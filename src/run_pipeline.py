#!/usr/bin/env python3
"""
Мастер-скрипт для запуска полного пайплайна обработки планшетов.
Автоматически определяет, нужно ли извлекать данные из Excel, и запускает соответствующие скрипты.
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Импортируем функции из других модулей
try:
    import app_config
    import combine_plates
    import extract_plates_from_excel
except ImportError as e:
    print(f"Ошибка импорта модулей: {e}", file=sys.stderr)
    print("Убедитесь, что все необходимые файлы находятся в той же директории.", file=sys.stderr)
    sys.exit(1)


__version__ = '0.2.0'
RESULT_DIR_PATTERN = re.compile(r'^Результат(?:\s+(\d+))?$')


def application_dir():
    """Возвращает папку, в которой лежат exe/скрипт, config и Excel."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def next_result_number(base_dir):
    """Возвращает номер следующей папки результатов."""
    base_dir = Path(base_dir)
    if not base_dir.exists():
        return 1

    used_numbers = []
    for entry in base_dir.iterdir():
        if not entry.is_dir():
            continue
        match = RESULT_DIR_PATTERN.match(entry.name)
        if match:
            used_numbers.append(int(match.group(1) or 1))

    return max(used_numbers, default=0) + 1


def create_result_dir(base_dir):
    """Создаёт следующую папку «Результат N» и возвращает её путь."""
    base_dir = Path(base_dir)

    while True:
        result_dir = base_dir / f'Результат {next_result_number(base_dir)}'
        try:
            result_dir.mkdir()
        except FileExistsError:
            continue
        return result_dir


def read_config(config_path='config.json'):
    """Читает конфигурационный файл."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Ошибка: файл конфигурации '{config_path}' не найден.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Ошибка: неверный формат JSON в '{config_path}': {e}", file=sys.stderr)
        sys.exit(1)


def run(base_dir=None, log=print, config=None):
    """Выполняет пайплайн и пишет все результаты в новую папку «Результат N».

    ``config`` можно передать готовым словарём — тогда config.json не нужен.
    Без него читается config.json, а если его нет, файл Excel и листы
    определяются автоматически.
    """
    base_dir = Path(base_dir) if base_dir else application_dir()
    config_path = base_dir / 'config.json'

    log("=" * 60)
    log("Мастер-скрипт обработки планшетов")
    log("=" * 60)

    if config is None:
        if config_path.exists():
            config = read_config(config_path)
        else:
            config, config_error, _source = app_config.load_config(base_dir)
            if config_error:
                print(f"Ошибка: {config_error}", file=sys.stderr)
                sys.exit(1)

    excel_file = config.get('excel_file')
    excel_path = None
    if excel_file:
        excel_path = Path(excel_file)
        if not excel_path.is_absolute():
            excel_path = base_dir / excel_path

    # Создаём папку результатов при каждом запуске
    result_dir = create_result_dir(base_dir)
    log(f"\nПапка результатов: {result_dir.name}")

    extracted = False

    # Проверяем наличие Excel файла
    if excel_path and excel_path.exists():
        log(f"\nНайден Excel файл: {excel_path.name}")
        log("Запускаем извлечение данных из Excel...")
        log(f"{'=' * 60}\n")

        try:
            # Запускаем извлечение данных из Excel напрямую
            extract_plates_from_excel.main(
                config_path=config_path,
                output_dir=result_dir,
                base_dir=base_dir,
                config=config,
                log=log,
            )
            extracted = True
            log("\n✓ Извлечение данных из Excel выполнено успешно")
        except Exception as e:
            print(f"\n✗ Ошибка при извлечении данных из Excel: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        if excel_file:
            log(f"\nExcel файл '{excel_file}' не найден в папке программы.")
        else:
            log("\nExcel файл не указан в конфигурации.")
        log("Пропускаем этап извлечения из Excel.")
        log("Предполагается, что CSV файлы планшетов уже существуют.")

    # Всегда запускаем объединение планшетов
    log("\nЗапускаем объединение планшетов...")
    log(f"{'=' * 60}\n")

    try:
        combine_plates.main(
            output_dir=result_dir,
            input_dir=result_dir if extracted else base_dir,
            log=log,
        )
        log("\n✓ Объединение планшетов выполнено успешно")
    except Exception as e:
        print(f"\n✗ Ошибка при объединении планшетов: {e}", file=sys.stderr)
        sys.exit(1)

    log("\n" + "=" * 60)
    log("Пайплайн выполнен успешно!")
    log(f"Результаты: {result_dir}")
    log("=" * 60)
    return result_dir


def _is_interactive():
    try:
        return bool(sys.stdin and sys.stdin.isatty() and sys.stdout.isatty())
    except (AttributeError, OSError):
        return False


def main(argv=None):
    """Запускает интерфейс или обычный консольный пайплайн."""
    parser = argparse.ArgumentParser(
        prog='avatar_combiner',
        description=(
            'Объединение 4 планшетов 96-луночного формата в 384-луночный. '
            'Combine four 96-well plates into one 384-well plate.'
        ),
        add_help=False,
    )
    parser.add_argument('--no-ui', action='store_true', help='run without the terminal UI')
    parser.add_argument('--ui', action='store_true', help='force the terminal UI')
    parser.add_argument('--lang', choices=('en', 'ru'), help='UI language: en or ru')
    parser.add_argument('--version', action='store_true', help='show version and exit')
    parser.add_argument('-h', '--help', action='help', help='show this help and exit')
    args = parser.parse_args(argv)

    if args.version:
        print(f'avatar_combiner {__version__}')
        return 0

    interactive = _is_interactive()

    if args.ui and not interactive:
        print('Terminal UI needs an interactive terminal; using CLI mode.', file=sys.stderr)

    if not args.no_ui and interactive:
        from ui import App

        App(lang=args.lang).run()
        return 0

    run()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
