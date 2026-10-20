#!/usr/bin/env python3
"""
Мастер-скрипт для запуска полного пайплайна обработки планшетов.
Автоматически определяет, нужно ли извлекать данные из Excel, и запускает соответствующие скрипты.
"""

import json
import os
import sys

# Импортируем функции из других модулей
try:
    import extract_plates_from_excel
    import combine_plates
except ImportError as e:
    print(f"Ошибка импорта модулей: {e}", file=sys.stderr)
    print("Убедитесь, что все необходимые файлы находятся в той же директории.", file=sys.stderr)
    sys.exit(1)


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


def main():
    """Основная функция."""
    print("="*60)
    print("Мастер-скрипт обработки планшетов")
    print("="*60)
    
    # Читаем конфигурацию
    config = read_config()
    
    excel_file = config.get('excel_file')
    extract_script = 'extract_plates_from_excel.py'
    combine_script = 'combine_plates.py'
    
    # Проверяем наличие Excel файла
    if excel_file and os.path.exists(excel_file):
        print(f"\nНайден Excel файл: {excel_file}")
        print("Запускаем извлечение данных из Excel...")
        print(f"{'='*60}\n")
        
        try:
            # Запускаем извлечение данных из Excel напрямую
            extract_plates_from_excel.main()
            print(f"\n✓ Извлечение данных из Excel выполнено успешно")
        except Exception as e:
            print(f"\n✗ Ошибка при извлечении данных из Excel: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        if excel_file:
            print(f"\nExcel файл '{excel_file}' не найден в текущей директории.")
        else:
            print("\nExcel файл не указан в конфигурации.")
        print("Пропускаем этап извлечения из Excel.")
        print("Предполагается, что CSV файлы планшетов уже существуют.")
    
    # Всегда запускаем объединение планшетов
    print(f"\nЗапускаем объединение планшетов...")
    print(f"{'='*60}\n")
    
    try:
        combine_plates.main()
        print(f"\n✓ Объединение планшетов выполнено успешно")
    except Exception as e:
        print(f"\n✗ Ошибка при объединении планшетов: {e}", file=sys.stderr)
        sys.exit(1)
    
    print("\n" + "="*60)
    print("Пайплайн выполнен успешно!")
    print("="*60)


if __name__ == '__main__':
    main()

