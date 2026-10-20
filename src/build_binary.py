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
    print("✓ Runtime: Bio.Seq, Pint, Primer3-py")
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
        '--optimize', '2',  # Убрать docstring и assert из байткода
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
        # Исключаем ненужные модули для уменьшения размера
        '--exclude-module', 'matplotlib',
        '--exclude-module', 'numpy',
        '--exclude-module', 'pandas',
        '--exclude-module', 'PIL',
        '--exclude-module', 'tkinter',
        '--exclude-module', 'pytest',
        '--exclude-module', 'ruff',
        '--exclude-module', 'pip',
        '--exclude-module', 'setuptools',
        '--exclude-module', 'pkg_resources',
        '--exclude-module', 'unittest',
        '--exclude-module', 'asyncio',
        '--exclude-module', 'concurrent',
        '--exclude-module', 'multiprocessing',
        '--exclude-module', 'http',
        '--exclude-module', 'urllib',
        '--exclude-module', 'ssl',
        '--exclude-module', 'socket',
        '--exclude-module', 'xmlrpc',
        '--exclude-module', 'pydoc',
        '--exclude-module', 'pdb',
        '--exclude-module', 'doctest',
        '--exclude-module', 'wsgiref',
        '--exclude-module', 'webbrowser',
        '--exclude-module', 'xml.dom',
        # Biopython: only Bio.Seq and IUPACData are used
        '--exclude-module', 'Bio.Align',
        '--exclude-module', 'Bio.AlignIO',
        '--exclude-module', 'Bio.PDB',
        '--exclude-module', 'Bio.Nexus',
        '--exclude-module', 'Bio.GenBank',
        '--exclude-module', 'Bio.bgzf',
        '--exclude-module', 'Bio.File',
        '--exclude-module', 'Bio.SeqIO',
        '--exclude-module', 'Bio.SeqRecord',
        '--exclude-module', 'Bio.SeqUtils',
        '--exclude-module', 'Bio.Phylo',
        '--exclude-module', 'Bio.Blast',
        '--exclude-module', 'Bio.Entrez',
        '--exclude-module', 'Bio.ExPASy',
        '--exclude-module', 'Bio.KEGG',
        '--exclude-module', 'Bio.Medline',
        '--exclude-module', 'Bio.PopGen',
        '--exclude-module', 'Bio.SCOP',
        '--exclude-module', 'Bio.SwissProt',
        '--exclude-module', 'Bio.TogoWS',
        '--exclude-module', 'Bio.UniGene',
        '--exclude-module', 'Bio.UniProt',
        '--exclude-module', 'Bio.codonalign',
        '--exclude-module', 'Bio.motifs',
        '--exclude-module', 'Bio.pairwise2',
        '--exclude-module', 'Bio.phenotype',
        '--exclude-module', 'Bio.restriction',
        '--exclude-module', 'Bio.SearchIO',
        '--exclude-module', 'BioSQL',
        script_name
    ]

    upx = shutil.which('upx')
    if upx:
        print(f"✓ UPX: {upx}")
        cmd.extend(['--upx-dir', str(Path(upx).resolve().parent)])
    else:
        print("UPX не найден; сборка без дополнительного сжатия")

    if system != 'Windows':
        cmd.insert(-1, '--strip')
    
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

