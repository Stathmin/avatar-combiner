#!/usr/bin/env python3
"""
Скрипт для сборки исполняемого файла из run_pipeline.py.
Создаёт exe на Windows или бинарник на Linux с минимальным набором зависимостей.
"""

import importlib.util
import os
import platform
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def check_pyinstaller():
    """Проверяет наличие PyInstaller в uv-окружении."""
    if importlib.util.find_spec('PyInstaller') is not None:
        print("✓ PyInstaller установлен")
        return True

    print(
        "PyInstaller не найден. Установите группу сборки: uv sync --group build",
        file=sys.stderr,
    )
    return False


def check_dependencies():
    """Проверяет наличие необходимых зависимостей."""
    if importlib.util.find_spec('openpyxl') is None:
        print("openpyxl не найден. Запустите: uv sync", file=sys.stderr)
        return False

    print("✓ openpyxl установлен")
    return True


def build_binary():
    """Собирает исполняемый файл."""
    system = platform.system()
    script_name = 'run_pipeline.py'
    os.chdir(SCRIPT_DIR)

    if not os.path.exists(script_name):
        print(f"✗ Файл '{script_name}' не найден", file=sys.stderr)
        return False

    # Имя должно совпадать с именем exe из инструкции
    if system == 'Windows':
        exe_name = 'аватар_объединитель_4х_планшетов'
    else:
        exe_name = 'avatar_combiner'
    icon = None
    
    print(f"\n{'='*60}")
    print(f"Сборка исполняемого файла для {system}")
    print(f"{'='*60}\n")
    
    # Команда PyInstaller
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',  # Один исполняемый файл
        '--name', exe_name,
        '--clean',  # Очистить кэш перед сборкой
        '--noconfirm',  # Не спрашивать подтверждения
        '--hidden-import', 'openpyxl',  # Явно указать openpyxl
        '--hidden-import', 'openpyxl.cell._writer',  # Необходимые подмодули
        '--hidden-import', 'openpyxl.workbook',
        '--hidden-import', 'openpyxl.worksheet',
        '--collect-all', 'openpyxl',  # Собрать все данные openpyxl
        # Включаем необходимые модули как скрытые импорты
        '--hidden-import', 'extract_plates_from_excel',
        '--hidden-import', 'combine_plates',
        # Исключаем ненужные модули для уменьшения размера
        '--exclude-module', 'matplotlib',
        '--exclude-module', 'numpy',
        '--exclude-module', 'pandas',
        '--exclude-module', 'PIL',
        '--exclude-module', 'tkinter',
        script_name
    ]
    
    # Добавляем иконку для Windows, если указана
    if icon and os.path.exists(icon):
        cmd.extend(['--icon', icon])
    
    try:
        print("Запуск PyInstaller...")
        subprocess.check_call(cmd)
        
        # Определяем путь к результату
        if system == 'Windows':
            output_path = os.path.join('dist', f'{exe_name}.exe')
        else:
            output_path = os.path.join('dist', exe_name)
        
        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"\n{'='*60}")
            print("✓ Сборка завершена успешно!")
            print(f"  Исполняемый файл: {output_path}")
            print(f"  Размер: {size_mb:.2f} MB")
            print(f"{'='*60}\n")
            return True
        else:
            print(f"\n✗ Файл не найден по пути: {output_path}", file=sys.stderr)
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Ошибка при сборке: {e}", file=sys.stderr)
        return False


def main():
    """Основная функция."""
    print("="*60)
    print("Скрипт сборки исполняемого файла")
    print("="*60)
    
    # Проверяем зависимости
    if not check_pyinstaller():
        sys.exit(1)
    
    if not check_dependencies():
        sys.exit(1)
    
    # Собираем бинарник
    if build_binary():
        print("\nГотово! Исполняемый файл находится в папке 'dist'")
        print("\nПримечание: для работы программы нужен config.json")
        print("в той же директории, что и исполняемый файл.")
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()

