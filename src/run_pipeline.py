#!/usr/bin/env python3
"""
Мастер-скрипт для запуска полного пайплайна обработки планшетов.
Автоматически определяет, нужно ли извлекать данные из Excel, и запускает соответствующие скрипты.
"""

import json
import re
import sys
from pathlib import Path

# Импортируем функции из других модулей
try:
    import combine_plates
    import extract_plates_from_excel
except ImportError as e:
    print(f"Ошибка импорта модулей: {e}", file=sys.stderr)
    print("Убедитесь, что все необходимые файлы находятся в той же директории.", file=sys.stderr)
    sys.exit(1)


RESULT_DIR_PATTERN = re.compile(r'^Результат(?:\s+(\d+))?$')


def application_dir():
    """Возвращает папку, в которой лежат exe/скрипт, config и Excel."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def create_result_dir(base_dir):
    """Создаёт следующую папку «Результат N» и возвращает её путь."""
    base_dir = Path(base_dir)
    used_numbers = []

    for entry in base_dir.iterdir():
        if not entry.is_dir():
            continue
        match = RESULT_DIR_PATTERN.match(entry.name)
        if match:
            used_numbers.append(int(match.group(1) or 1))

    next_number = max(used_numbers, default=0) + 1
    result_dir = base_dir / f'Результат {next_number}'
    result_dir.mkdir()
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


def run(base_dir=None):
    """Выполняет пайплайн и пишет все результаты в новую папку «Результат N»."""
    base_dir = Path(base_dir) if base_dir else application_dir()
    config_path = base_dir / 'config.json'

    print("="*60)
    print("Мастер-скрипт обработки планшетов")
    print("="*60)

    # Читаем конфигурацию
    config = read_config(config_path)

    excel_file = config.get('excel_file')
    excel_path = None
    if excel_file:
        excel_path = Path(excel_file)
        if not excel_path.is_absolute():
            excel_path = base_dir / excel_path

    # Создаём папку результатов при каждом запуске
    result_dir = create_result_dir(base_dir)
    print(f"\nПапка результатов: {result_dir.name}")

    extracted = False

    # Проверяем наличие Excel файла
    if excel_path and excel_path.exists():
        print(f"\nНайден Excel файл: {excel_path.name}")
        print("Запускаем извлечение данных из Excel...")
        print(f"{'='*60}\n")

        try:
            # Запускаем извлечение данных из Excel напрямую
            extract_plates_from_excel.main(
                config_path=config_path,
                output_dir=result_dir,
                base_dir=base_dir,
            )
            extracted = True
            print("\n✓ Извлечение данных из Excel выполнено успешно")
        except Exception as e:
            print(f"\n✗ Ошибка при извлечении данных из Excel: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        if excel_file:
            print(f"\nExcel файл '{excel_file}' не найден в папке программы.")
        else:
            print("\nExcel файл не указан в конфигурации.")
        print("Пропускаем этап извлечения из Excel.")
        print("Предполагается, что CSV файлы планшетов уже существуют.")

    # Всегда запускаем объединение планшетов
    print("\nЗапускаем объединение планшетов...")
    print(f"{'='*60}\n")

    try:
        combine_plates.main(
            output_dir=result_dir,
            input_dir=result_dir if extracted else base_dir,
        )
        print("\n✓ Объединение планшетов выполнено успешно")
    except Exception as e:
        print(f"\n✗ Ошибка при объединении планшетов: {e}", file=sys.stderr)
        sys.exit(1)

    print("\n" + "="*60)
    print("Пайплайн выполнен успешно!")
    print(f"Результаты: {result_dir}")
    print("="*60)


def main():
    """Основная функция."""
    run()


if __name__ == '__main__':
    main()

