# Инструкции по сборке исполняемого файла

## Быстрая сборка

Все команды выполняются через `uv`.

```bash
uv sync --group build
cd src
uv run python build_binary.py
```

Скрипт соберёт исполняемый файл в `src/dist/`.

## Ручная сборка

```bash
uv sync --group build
cd src
uv run pyinstaller --onefile --name аватар_объединитель_4х_планшетов \
  --hidden-import openpyxl \
  --hidden-import extract_plates_from_excel \
  --hidden-import combine_plates \
  --collect-all openpyxl \
  run_pipeline.py
```

Для Linux используйте имя без `.exe`, например `avatar_combiner`.

## Использование

Рядом с исполняемым файлом должны лежать:

- `config.json`;
- Excel-файл, указанный в `config.json`.

### Windows

```cmd
dist\аватар_объединитель_4х_планшетов.exe
```

### Linux

```bash
./dist/avatar_combiner
```

При каждом запуске создаётся папка `Результат N`. Все CSV и TXT пишутся в неё.
