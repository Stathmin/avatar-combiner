#!/usr/bin/env python3
"""
Объединение 4 планшетов 96-луночного формата в один 384-луночный.
Чередование образцов из планшетов 1-2 и 3-4 по строкам.
"""

import csv
import os
import sys
from pathlib import Path


def convert_row_interleaved(old_row, plate_num, column):
    """
    Преобразует строку из старого планшета в новую с чередованием.
    
    Планшеты 1 и 2 чередуются в колонках 1-12:
    - Планшет 1: A→A, B→C, C→E, D→G, E→I, F→K, G→M, H→O (нечётные строки)
    - Планшет 2: A→B, B→D, C→F, D→H, E→J, F→L, G→N, H→P (чётные строки)
    
    Планшеты 3 и 4 чередуются в колонках 13-24:
    - Планшет 3: A→A, B→C, C→E, D→G, E→I, F→K, G→M, H→O (нечётные строки)
    - Планшет 4: A→B, B→D, C→F, D→H, E→J, F→L, G→N, H→P (чётные строки)
    
    Args:
        old_row: буква строки в старом планшете (A-H)
        plate_num: номер планшета (1-4)
        column: номер столбца в старом планшете (1-12)
    
    Returns:
        буква строки в новом планшете
    """
    old_rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    new_rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P']
    
    old_index = old_rows.index(old_row)
    
    # Определяем, нечётный или чётный планшет в паре
    if plate_num in [1, 3]:
        # Нечётные строки: 0, 2, 4, 6, 8, 10, 12, 14
        new_index = old_index * 2
    else:  # plate_num in [2, 4]
        # Чётные строки: 1, 3, 5, 7, 9, 11, 13, 15
        new_index = old_index * 2 + 1
    
    return new_rows[new_index]


def _empty_plate_rows():
    rows_96 = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    return [
        {'id': '', 'row': row, 'column': column}
        for row in rows_96
        for column in range(1, 13)
    ]


def _complete_plate_rows(rows):
    """Fill any missing A1–H12 wells with blank ids (preserves sparse CSVs)."""
    by_well = {}
    for row in rows:
        key = (row['row'], int(row['column']))
        by_well[key] = row
    completed = []
    for row_label, column in (
        (row, column)
        for row in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        for column in range(1, 13)
    ):
        existing = by_well.get((row_label, column))
        if existing is not None:
            completed.append(existing)
        else:
            completed.append({'id': '', 'row': row_label, 'column': column})
    return completed


def _read_plate_rows(input_file):
    """Read plate CSV rows; missing file → 96 blank wells (sparse-plate pad)."""
    path = Path(input_file)
    if not path.is_file():
        return _empty_plate_rows(), path.stem
    with open(path, 'r', encoding='utf-8') as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            if 'id' not in row or 'row' not in row or 'column' not in row:
                raise KeyError(
                    f"missing column in '{path.name}' "
                    f"(need id, row, column)"
                )
            sample_id = '' if row['id'] is None else str(row['id'])
            if sample_id.strip().lower() in ('nan', 'none'):
                sample_id = ''
            rows.append(
                {
                    'id': sample_id,
                    'row': str(row['row']).strip().upper(),
                    'column': int(row['column']),
                }
            )
    return _complete_plate_rows(rows), path.stem


def combine_plates(input_files, output_file, log=print):
    """
    Объединяет до 4 планшетов в один 384-луночный с чередованием по строкам.

    Missing plate CSVs are treated as empty 96-well plates so unselected
    slots stay blank in the 384 layout. Blank/NaN sample ids stay empty.
    
    Args:
        input_files: список путей к входным CSV файлам (1–4; pad to 4 slots)
        output_file: путь к выходному CSV файлу
    """
    all_samples = []
    files = list(input_files)
    while len(files) < 4:
        files.append(None)

    for plate_num, input_file in enumerate(files[:4], start=1):
        if input_file is None:
            plate_rows, plate_id = _empty_plate_rows(), f'plate{plate_num}'
            log(f'{plate_id}: padded empty slot')
        else:
            try:
                plate_rows, plate_id = _read_plate_rows(input_file)
            except KeyError as exc:
                raise ValueError(str(exc)) from exc
            if not Path(input_file).is_file():
                log(f'{plate_id}: padded empty slot (file missing)')

        if plate_num in [1, 2]:
            column_offset = 0  # Колонки 1-12
        else:  # plate_num in [3, 4]
            column_offset = 12  # Колонки 13-24

        for row in plate_rows:
            sample_id = row['id']
            old_row = row['row']
            old_column = int(row['column'])

            new_row = convert_row_interleaved(old_row, plate_num, old_column)
            new_column = old_column + column_offset

            all_samples.append({
                'id': sample_id,
                'название_старого_планшета': plate_id,
                'строка_в_старом': old_row,
                'столбец_в_старом': old_column,
                'строка_в_новом': new_row,
                'столбец_в_новом': new_column
            })
    
    # Сортируем по (строка_в_новом, столбец_в_новом)
    rows_384 = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P']
    def sort_key(sample):
        row_index = rows_384.index(sample['строка_в_новом'])
        return (row_index, sample['столбец_в_новом'])
    
    all_samples_sorted = sorted(all_samples, key=sort_key)
    
    # Записываем результат
    fieldnames = ['id', 'название_старого_планшета', 'строка_в_старом', 
                  'столбец_в_старом', 'строка_в_новом', 'столбец_в_новом']
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_samples_sorted)
    
    log(f"Объединено {len(input_files)} планшетов")
    log(f"Всего образцов: {len(all_samples)}")
    log(f"Результат записан в '{output_file}'")
    
    return all_samples


def create_pivot_table(input_file, output_file, log=print):
    """
    Создаёт пивот-таблицу из объединённого файла.
    
    Args:
        input_file: путь к файлу combined_384_plate.csv
        output_file: путь к выходному файлу пивот-таблицы
    """
    # Инициализируем матрицу 16x24
    rows_384 = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P']
    columns_384 = list(range(1, 25))  # 1-24
    
    # Создаём словарь для быстрого доступа
    pivot_data = {}
    for row in rows_384:
        pivot_data[row] = {}
        for col in columns_384:
            pivot_data[row][col] = ''
    
    # Читаем данные и заполняем матрицу
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                new_row = row['строка_в_новом']
                new_col = int(row['столбец_в_новом'])
                plate_id = row['название_старого_планшета']
                old_row = row['строка_в_старом']
                old_col = row['столбец_в_старом']
                
                # Конкатенация: plate_id,old_row,old_col
                value = f"{plate_id},{old_row},{old_col}"
                pivot_data[new_row][new_col] = value
    except FileNotFoundError:
        print(f"Ошибка: файл '{input_file}' не найден.", file=sys.stderr)
        sys.exit(1)
    
    # Записываем пивот-таблицу в CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        # Заголовки: строка, затем столбцы 1-24
        fieldnames = ['строка'] + [str(col) for col in columns_384]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        # Записываем данные по строкам
        for row in rows_384:
            row_data = {'строка': row}
            for col in columns_384:
                row_data[str(col)] = pivot_data[row][col]
            writer.writerow(row_data)
    
    log(f"Пивот-таблица создана: '{output_file}'")


def create_id_list(input_file, output_file, log=print):
    """
    Создаёт список ID образцов из отсортированного combined_384_plate.csv.
    
    Порядок соответствует сортировке в CSV: A1-A24, B1-B24, ..., P1-P24
    
    Args:
        input_file: путь к файлу combined_384_plate.csv (уже отсортированному)
        output_file: путь к выходному файлу со списком ID
    """
    # Читаем данные из уже отсортированного файла
    ids = []
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ids.append(row['id'])
    except FileNotFoundError:
        print(f"Ошибка: файл '{input_file}' не найден.", file=sys.stderr)
        sys.exit(1)
    
    # Записываем ID в столбик без заголовка
    with open(output_file, 'w', encoding='utf-8') as f:
        for sample_id in ids:
            f.write(sample_id + '\n')
    
    log(f"Список ID создан: '{output_file}' ({len(ids)} образцов)")


def main(output_dir=None, input_dir=None, log=print):
    """Основная функция."""
    output_dir = Path(output_dir) if output_dir else Path('.')
    input_dir = Path(input_dir) if input_dir else output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Standard slots plate1–plate4; missing files pad as empty wells.
    input_files = [input_dir / f'plate{number}.csv' for number in range(1, 5)]
    output_file = output_dir / 'combined_384_plate.csv'
    if not any(path.exists() for path in input_files):
        raise FileNotFoundError(
            f'no plate CSV files in {input_dir} (need at least plate1.csv)'
        )

    combine_plates(input_files, output_file, log=log)
    
    # Создаём пивот-таблицу
    pivot_output = output_dir / 'combined_384_plate_pivot.csv'
    create_pivot_table(output_file, pivot_output, log=log)
    
    # Создаём список ID
    id_list_output = output_dir / 'combined_384_plate_ids.txt'
    create_id_list(output_file, id_list_output, log=log)


if __name__ == '__main__':
    main()

