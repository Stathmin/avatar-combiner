# Инструкции по сборке исполняемого файла

## Быстрая сборка

Запустите скрипт сборки:
```bash
python3 build_binary.py
```

Скрипт автоматически:
- Проверит и установит PyInstaller при необходимости
- Проверит и установит зависимости (openpyxl)
- Соберёт исполняемый файл в папке `dist/`

## Ручная сборка

### Установка зависимостей
```bash
pip install -r requirements.txt
```

### Сборка для Linux
```bash
pyinstaller --onefile --name run_pipeline \
  --hidden-import openpyxl \
  --hidden-import extract_plates_from_excel \
  --hidden-import combine_plates \
  --collect-all openpyxl \
  run_pipeline.py
```

### Сборка для Windows
```bash
pyinstaller --onefile --name run_pipeline.exe \
  --hidden-import openpyxl \
  --hidden-import extract_plates_from_excel \
  --hidden-import combine_plates \
  --collect-all openpyxl \
  run_pipeline.py
```

## Использование

После сборки исполняемый файл будет находиться в папке `dist/`.

**Важно:** Для работы программы необходим файл `config.json` в той же директории, что и исполняемый файл.

### Linux
```bash
./dist/run_pipeline
```

### Windows
```cmd
dist\run_pipeline.exe
```

## Размер файла

Ожидаемый размер исполняемого файла: ~15-25 MB (зависит от платформы)

## Оптимизация

Для уменьшения размера можно использовать UPX (если установлен):
```bash
pyinstaller --onefile --upx-dir=/path/to/upx ...
```

