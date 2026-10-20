#!/usr/bin/env python3
"""
Мастер-скрипт для запуска полного пайплайна обработки планшетов.
Автоматически определяет, нужно ли извлекать данные из Excel, и запускает соответствующие скрипты.
"""

import argparse
import json
import re
import sys
import time
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


def write_manifest(result_dir, config, base_dir):
    """Write the run configuration into the result folder."""
    excel_file = config.get('excel_file')
    excel_path = Path(excel_file) if excel_file else None
    if excel_path is not None and not excel_path.is_absolute():
        excel_path = Path(base_dir) / excel_path

    manifest = {
        'version': __version__,
        'created_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'excel_file': excel_file,
        'excel_path': str(excel_path.resolve()) if excel_path else None,
        'sheets': config.get('sheets', {}),
        'data_range': config.get('data_range', {}),
        'row_labels_col': config.get('row_labels_col'),
        'column_labels_row': config.get('column_labels_row'),
        'metadata_row': config.get('metadata_row'),
    }
    output = Path(result_dir) / 'manifest.json'
    output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )
    return output


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class PipelineError(RuntimeError):
    """Raised when a run cannot start or cannot finish."""


def run(base_dir=None, log=print, config=None):
    """Run the pipeline into a fresh «Результат N» folder.

    Validation happens before the result folder is created, so a failed start
    leaves no empty or misleading result behind.
    """
    base_dir = Path(base_dir) if base_dir else application_dir()

    log("=" * 60)
    log("Мастер-скрипт обработки планшетов")
    log("=" * 60)

    if config is None:
        config, config_error, _source = app_config.load_config(base_dir)
        if config_error:
            raise PipelineError(config_error)
    else:
        try:
            config = app_config.validate_config(config, base_dir)
        except app_config.ConfigError as exc:
            raise PipelineError(str(exc)) from exc

    excel_file = config['excel_file']
    excel_path = Path(excel_file)
    if not excel_path.is_absolute():
        excel_path = base_dir / excel_path

    result_dir = create_result_dir(base_dir)
    log(f"\nПапка результатов: {result_dir.name}")
    write_manifest(result_dir, config, base_dir)

    log(f"\nНайден Excel файл: {excel_path.name}")
    log("Запускаем извлечение данных из Excel...")
    log(f"{'=' * 60}\n")

    try:
        extract_plates_from_excel.main(
            config_path=base_dir / 'config.json',
            output_dir=result_dir,
            base_dir=base_dir,
            config=config,
            log=log,
        )
    except Exception as exc:
        raise PipelineError(
            f'извлечение из Excel ({type(exc).__name__}): {exc}'
        ) from exc

    log("\n✓ Извлечение данных из Excel выполнено успешно")
    log("\nЗапускаем объединение планшетов...")
    log(f"{'=' * 60}\n")

    try:
        combine_plates.main(
            output_dir=result_dir,
            input_dir=result_dir,
            log=log,
        )
    except Exception as exc:
        raise PipelineError(
            f'объединение планшетов ({type(exc).__name__}): {exc}'
        ) from exc

    log("\n✓ Объединение планшетов выполнено успешно")
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
    parser.add_argument('--web', action='store_true', help='start the local web UI')
    parser.add_argument('--port', type=int, default=8080, help='web UI port (default 8080)')
    parser.add_argument('--no-browser', action='store_true', help='do not open a browser')
    parser.add_argument('--lang', choices=('en', 'ru'), help='UI language: en or ru')
    parser.add_argument('--version', action='store_true', help='show version and exit')
    parser.add_argument('-h', '--help', action='help', help='show this help and exit')
    args = parser.parse_args(argv)

    if args.version:
        print(f'avatar_combiner {__version__}')
        return 0

    if args.web:
        import web_app

        web_app.main(
            base_dir=application_dir(),
            port=args.port,
            show=not args.no_browser,
        )
        return 0

    interactive = _is_interactive()

    if args.ui and not interactive:
        print('Terminal UI needs an interactive terminal; using CLI mode.', file=sys.stderr)

    if not args.no_ui and interactive:
        from ui import App

        App(lang=args.lang).run()
        return 0

    try:
        run()
    except PipelineError as exc:
        print(f'Ошибка: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
