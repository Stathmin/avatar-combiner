#!/usr/bin/env python3
"""
Скрипт для сборки исполняемого файла из run_pipeline.py.
Создаёт exe на Windows или бинарник на Linux с минимальным набором зависимостей.
"""

import importlib.util
import os
import platform
import shutil
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
    """Проверяет runtime-зависимости."""
    print(
        '✓ Runtime: Bio.Seq/SeqIO, Pint, Primer3-py, seqfold, snapgene_reader, '
        'pydna, wellmap, pandas, openpyxl'
    )
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
        '--optimize', '1',  # Keep docstrings: pydna.alphabet builds tables from __doc__.
        '--log-level', 'WARN',
        # Модули, которые подключаются лениво
        '--hidden-import', 'extract_plates_from_excel',
        '--hidden-import', 'combine_plates',
        '--hidden-import', 'ui',
        '--hidden-import', 'tools',
        '--hidden-import', 'primer3',
        '--hidden-import', 'primer3.thermoanalysis',
        '--hidden-import', 'primer3.p3helpers',
        '--collect-binaries', 'primer3',
        '--collect-data', 'primer3',
        '--hidden-import', 'Bio.Seq',
        '--hidden-import', 'Bio.Data.IUPACData',
        '--hidden-import', 'pint',
        '--collect-data', 'pint',
        # Генетический набор: локальные модули и их библиотеки
        '--hidden-import', 'seq_structure',
        '--hidden-import', 'seq_import',
        '--hidden-import', 'plate_layout',
        '--hidden-import', 'pcr_tools',
        '--hidden-import', 'report_xlsx',
        '--hidden-import', 'web_app',
        '--collect-all', 'nicegui',
        '--collect-all', 'seqfold',
        '--hidden-import', 'snapgene_reader',
        '--hidden-import', 'xmltodict',
        '--hidden-import', 'html2text',
        # plate_layout imports wellmap.file directly and stubs wellmap.plot,
        # so matplotlib is never loaded at runtime.
        '--hidden-import', 'wellmap.file',
        '--hidden-import', 'pydna',
        '--hidden-import', 'openpyxl',
        # pydna.amplify only needs this subset; collect-all pulls the gel module
        # (matplotlib plotting) and other unused submodules.
        '--hidden-import', 'pydna.amplify',
        '--hidden-import', 'pydna.dseqrecord',
        '--hidden-import', 'pydna.dseq',
        '--hidden-import', 'pydna.seq',
        '--hidden-import', 'pydna.seqrecord',
        '--hidden-import', 'pydna.amplicon',
        '--hidden-import', 'pydna.primer',
        '--hidden-import', 'pydna.tm',
        '--hidden-import', 'pydna.alphabet',
        '--hidden-import', 'pydna.codon',
        '--hidden-import', 'pydna.common_sub_strings',
        '--hidden-import', 'pydna.crispr',
        '--hidden-import', 'pydna.opencloning_models',
        '--hidden-import', 'pydna.types',
        '--hidden-import', 'pydna.utils',
        '--hidden-import', 'seguid',
        # seguid resolves its own version through importlib.metadata.
        '--copy-metadata', 'seguid',
        '--copy-metadata', 'pydna',
        # Исключаем только заведомо необязательные модули, чтобы уменьшить размер.
        # Библиотеки stdlib, которые могут понадобиться во время работы
        # (unittest, concurrent, http, ssl, xml.dom), не исключаем.
        '--exclude-module', 'pandas.tests',
        '--exclude-module', 'pydna.gel',
        # matplotlib enters only through wellmap.plot, which plate_layout stubs.
        # PIL is used only by matplotlib, so both leave the bundle (~25 MB).
        '--exclude-module', 'matplotlib',
        '--exclude-module', 'PIL',
        '--exclude-module', 'wellmap.plot',
        '--exclude-module', 'tkinter',
        '--exclude-module', 'pytest',
        '--exclude-module', 'ruff',
        '--exclude-module', 'pip',
        '--exclude-module', 'setuptools',
        '--exclude-module', 'pkg_resources',
        '--exclude-module', 'xmlrpc',
        '--exclude-module', 'pydoc',
        '--exclude-module', 'pdb',
        '--exclude-module', 'doctest',
        '--exclude-module', 'wsgiref',
        # NiceGUI imports webbrowser to open the local UI.
        script_name
    ]

    upx = shutil.which('upx')
    if upx:
        print(f"✓ UPX: {upx}")
        cmd[-1:-1] = ['--upx-dir', str(Path(upx).resolve().parent)]
    else:
        print("UPX не найден; сборка без дополнительного сжатия")

    if system != 'Windows':
        cmd.insert(-1, '--strip')
    
    # Добавляем иконку для Windows, если указана
    if icon and os.path.exists(icon):
        cmd[-1:-1] = ['--icon', icon]
    
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
        print("\nПримечание: положите файл Excel рядом с программой.")
        print("config.json не обязателен: файл и листы находятся автоматически.")
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()

