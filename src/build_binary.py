#!/usr/bin/env python3
"""
Скрипт для сборки исполняемого файла из run_pipeline.py.
Создаёт exe на Windows или бинарник на Linux с минимальным набором зависимостей.
"""

import ast
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
        '✓ Runtime: Bio.Seq, Pint, Primer3-py, seqfold, pydna, wellmap, '
        'pandas, openpyxl'
    )
    return True


def collect_local_modules(entry='run_pipeline.py'):
    """Return every local module reachable from the entry point.

    Keeps the PyInstaller hidden-import list in sync with the real import
    graph instead of maintaining it by hand.
    """
    modules = {
        path.stem: path
        for path in SCRIPT_DIR.glob('*.py')
        if path.stem != 'build_binary'
    }
    seen = set()
    queue = [Path(entry).stem]

    while queue:
        name = queue.pop()
        if name in seen or name not in modules:
            continue
        seen.add(name)
        tree = ast.parse(modules[name].read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                candidates = [alias.name.split('.')[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                candidates = [node.module.split('.')[0]]
            else:
                continue
            queue.extend(
                dep for dep in candidates if dep in modules and dep not in seen
            )

    seen.discard(Path(entry).stem)
    return sorted(seen)


def _write_dist_web_bats(dist_dir: Path, exe_name: str) -> None:
    """Drop double-click start/stop helpers next to the packaged exe.

    A second PyInstaller target is unnecessary: the main exe already accepts
    ``--web``. Bats keep start/stop obvious for non-dev Windows users.
    Also copies the app icon and shortcut helpers so lab users can pin .lnk
    files with the four-nations mark (``.bat`` files cannot embed icons).

    Important: keep bat bodies ASCII-only. ``cmd.exe`` reads ``.bat`` files in
    the OEM/ANSI code page, so a UTF-8 Cyrillic exe name embedded in the bat
    becomes mojibake and fails with "is not recognized as an internal or
    external command" even though double-clicking the ``.exe`` works. Resolve
    the exe via ``*.exe`` glob instead (``exe_name`` is kept for callers /
    logging only).
    """
    del exe_name  # name is Cyrillic; do not embed it in the .bat text
    dist_dir.mkdir(parents=True, exist_ok=True)
    # ASCII-only templates — do not put non-ASCII in these strings.
    start = '''@echo off
REM Start the packaged Avatar Combiner web UI in the default browser.
REM Finds the .exe beside this bat (avoids cmd code-page issues with Cyrillic names).
setlocal EnableExtensions
cd /d "%~dp0"
title Avatar Combiner - Web UI  [close this window / Ctrl+C / stop-web.bat to stop]
set "PORT=8080"
set "EXE="
for %%F in ("%~dp0*.exe") do set "EXE=%%~fF"
if not defined EXE (
  echo [error] No .exe found in "%~dp0"
  pause
  exit /b 1
)
if not exist "%EXE%" (
  echo [error] Missing exe: %EXE%
  pause
  exit /b 1
)
echo %PORT%> "%TEMP%\\avatar-combiner-web.port"
echo Starting web UI on port %PORT%
echo Exe: %EXE%
echo Open http://127.0.0.1:%PORT%  (browser should open shortly)
echo Stop: close this window, Ctrl+C, or run stop-web.bat
start "" /b powershell -NoProfile -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:%PORT%'"
"%EXE%" --web --port %PORT% --no-browser
endlocal
'''
    # PID file, recorded port, then 8080–8099 sweep (match by path under this folder).
    stop = '''@echo off
setlocal EnableExtensions
set "PIDFILE=%TEMP%\\avatar-combiner-web.pid"
set "PORTFILE=%TEMP%\\avatar-combiner-web.port"
set "APPDIR=%~dp0"
echo Stopping Avatar Combiner web UI...
if exist "%PIDFILE%" (
  set /p APP_PID=<"%PIDFILE%"
  if defined APP_PID taskkill /PID %APP_PID% /T /F >nul 2>&1
  del "%PIDFILE%" >nul 2>&1
)
set "PORT=8080"
if exist "%PORTFILE%" set /p PORT=<"%PORTFILE%"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$port=%PORT%; $conns=Get-NetTCPConnection -LocalPort $port -State Listen -EA SilentlyContinue; foreach ($c in $conns) { try { Stop-Process -Id $c.OwningProcess -Force -EA Stop; Write-Output ('Killed PID '+$c.OwningProcess+' on port '+$port); } catch {} }" 2>nul
if exist "%PORTFILE%" del "%PORTFILE%" >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$dir=$env:APPDIR; if (-not $dir) { $dir='%~dp0' }; 8080..8099 | ForEach-Object { $port=$_; Get-NetTCPConnection -LocalPort $port -State Listen -EA SilentlyContinue | ForEach-Object { $proc=Get-Process -Id $_.OwningProcess -EA SilentlyContinue; if (-not $proc) { return }; $path=''; try { $path=$proc.Path } catch {}; if ($proc.ProcessName -match 'python|uv|avatar' -or ($path -and $dir -and $path.StartsWith($dir))) { Stop-Process -Id $proc.Id -Force -EA SilentlyContinue; Write-Output ('Killed '+$proc.ProcessName+' PID '+$proc.Id+' on port '+$port) } } }" 2>nul
echo Done.
pause
endlocal
'''
    # Write as UTF-8 with BOM so editors keep ASCII body; cmd still sees ASCII opcodes.
    (dist_dir / 'start-web.bat').write_text(start, encoding='utf-8-sig')
    (dist_dir / 'stop-web.bat').write_text(stop, encoding='utf-8-sig')

    # Ship icon + shortcut helpers beside the exe for lab desktops.
    icon_src = SCRIPT_DIR / 'assets' / 'app-icon.ico'
    if icon_src.is_file():
        shutil.copy2(icon_src, dist_dir / 'app-icon.ico')
    for name in ('create-shortcuts.ps1', 'create-shortcuts.bat'):
        helper = SCRIPT_DIR.parent / name
        if not helper.is_file():
            helper = SCRIPT_DIR / name
        if helper.is_file():
            shutil.copy2(helper, dist_dir / name)

    # Also drop plate-fold GIF beside the exe (resolve_plate_fold_gif first look).
    gif_src = SCRIPT_DIR.parent / 'docs' / 'media' / 'four-to-384.gif'
    if gif_src.is_file():
        media_dir = dist_dir / 'media'
        media_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(gif_src, media_dir / 'four-to-384.gif')


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
    # Four-nations app icon (Windows .ico; Linux PNG via --icon also accepted).
    icon_candidates = [
        SCRIPT_DIR / 'assets' / 'app-icon.ico',
        SCRIPT_DIR / 'assets' / 'app-icon-256.png',
        SCRIPT_DIR.parents[0] / 'docs' / 'media' / 'icons' / 'app-icon.ico',
    ]
    icon = next((str(p) for p in icon_candidates if p.is_file()), None)

    print(f"\n{'='*60}")
    print(f"Сборка исполняемого файла для {system}")
    print(f"{'='*60}\n")
    if icon:
        print(f"✓ App icon: {icon}")
    else:
        print("App icon not found under src/assets/; building without --icon")

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
        '--hidden-import', 'primer3',
        '--hidden-import', 'primer3.thermoanalysis',
        '--hidden-import', 'primer3.p3helpers',
        '--collect-binaries', 'primer3',
        '--collect-data', 'primer3',
        '--hidden-import', 'Bio.Seq',
        '--hidden-import', 'Bio.Data.IUPACData',
        '--hidden-import', 'pint',
        '--collect-data', 'pint',
        '--collect-all', 'nicegui',
        '--collect-all', 'seqfold',
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

    local_args = []
    for module in collect_local_modules():
        local_args.extend(['--hidden-import', module])
    cmd[-1:-1] = local_args

    upx = shutil.which('upx')
    if upx:
        print(f"✓ UPX: {upx}")
        cmd[-1:-1] = ['--upx-dir', str(Path(upx).resolve().parent)]
    else:
        print("UPX не найден; сборка без дополнительного сжатия")

    if system != 'Windows':
        cmd.insert(-1, '--strip')

    # Embed app icon in the Windows exe (and Linux binary when PNG/ICO present).
    if icon and os.path.exists(icon):
        cmd[-1:-1] = ['--icon', icon]

    # Bundle plate-fold GIF so frozen web UI can serve it from _MEIPASS/media/
    # (see internal/pipeline-gif-placement.md). Windows uses ';' as --add-data sep.
    gif_src = SCRIPT_DIR.parent / 'docs' / 'media' / 'four-to-384.gif'
    if gif_src.is_file():
        sep = ';' if system == 'Windows' else ':'
        cmd[-1:-1] = ['--add-data', f'{gif_src}{sep}media']
        print(f"✓ Plate-fold GIF: {gif_src} → media/")
    else:
        print(f"Plate-fold GIF not found at {gif_src}; web Quick-start GIF may be missing in exe")

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
            # Companion bats so lab users can start/stop --web without a second exe.
            dist_dir = Path(output_path).resolve().parent
            _write_dist_web_bats(dist_dir, Path(output_path).name)
            print(f"\n{'='*60}")
            print("✓ Сборка завершена успешно!")
            print(f"  Исполняемый файл: {output_path}")
            print(f"  Размер: {size_mb:.2f} MB")
            print(f"  Веб: {dist_dir / 'start-web.bat'} / {dist_dir / 'stop-web.bat'}")
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

