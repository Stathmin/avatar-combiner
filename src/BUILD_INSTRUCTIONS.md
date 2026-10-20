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
uv run pyinstaller --onefile --optimize 2 \
  --name аватар_объединитель_4х_планшетов \
  --hidden-import ui \
  --hidden-import tools \
  --hidden-import primer3 \
  --hidden-import primer3.thermoanalysis \
  --hidden-import primer3.p3helpers \
  --collect-binaries primer3 \
  --collect-data primer3 \
  --hidden-import Bio.Seq \
  --hidden-import Bio.Data.IUPACData \
  --hidden-import pint \
  --collect-data pint \
  --hidden-import extract_plates_from_excel \
  --hidden-import combine_plates \
  run_pipeline.py
```

Для Linux используйте имя без `.exe`, например `avatar_combiner`.

`build_binary.py` дополнительно исключает `numpy`, `pandas`, `matplotlib`, `PIL`,
`tkinter`, `setuptools` и тестовые пакеты. Библиотеки инструментов: `Bio.Seq`,
`Pint` и `Primer3-py`. `NumPy` намеренно не включается в сборку.

Если в системе есть `upx`, скрипт автоматически включает сжатие. UPX может вызывать
ложные срабатывания антивируса, поэтому это опция, а не требование.

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

### Быстрые клавиши

`R` запуск · `T` инструменты · `D` результаты · `O` открыть последний ·
`C` настройки · `H` помощь · `L` язык · `Q` выход.

Для запуска без интерфейса:

```bash
./dist/avatar_combiner --no-ui
```
