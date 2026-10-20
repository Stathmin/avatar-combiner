#!/usr/bin/env python3
"""
Объединение 4 планшетов 96-луночного формата в один 384-луночный.
Чередование образцов из планшетов 1-2 и 3-4 по строкам.
"""

import csv
import os
import sys


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
    
    # Определяем смещение для столбцов
    if plate_num in [1, 2]:
        column_offset = 0  # Колонки 1-12
    else:  # plate_num in [3, 4]
        column_offset = 12  # Колонки 13-24
    
    # Определяем, нечётный или чётный планшет в паре
    if plate_num in [1, 3]:
        # Нечётные строки: 0, 2, 4, 6, 8, 10, 12, 14
        new_index = old_index * 2
    else:  # plate_num in [2, 4]
        # Чётные строки: 1, 3, 5, 7, 9, 11, 13, 15
        new_index = old_index * 2 + 1
    
    return new_rows[new_index]


def combine_plates(input_files, output_file):
    """
    Объединяет 4 планшета в один 384-луночный с чередованием по строкам.
    
    Args:
        input_files: список путей к входным CSV файлам
        output_file: путь к выходному CSV файлу
    """
    all_samples = []
    
    for plate_num, input_file in enumerate(input_files, start=1):
        # Получаем ID планшета из имени файла
        plate_id = os.path.splitext(os.path.basename(input_file))[0]
        
        # Определяем смещение для столбцов
        if plate_num in [1, 2]:
            column_offset = 0  # Колонки 1-12
        else:  # plate_num in [3, 4]
            column_offset = 12  # Колонки 13-24
        
        # Читаем данные планшета
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    sample_id = row['id']
                    old_row = row['row']
                    old_column = int(row['column'])
                    
                    # Преобразуем координаты
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
        except FileNotFoundError:
            print(f"Ошибка: файл '{input_file}' не найден.", file=sys.stderr)
            sys.exit(1)
        except KeyError as e:
            print(f"Ошибка: отсутствует колонка в файле '{input_file}': {e}", file=sys.stderr)
            sys.exit(1)
    
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
    
    print(f"Объединено {len(input_files)} планшетов")
    print(f"Всего образцов: {len(all_samples)}")
    print(f"Результат записан в '{output_file}'")
    
    return all_samples


def create_pivot_table(input_file, output_file):
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
    
    print(f"Пивот-таблица создана: '{output_file}'")


def create_id_list(input_file, output_file):
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
    
    print(f"Список ID создан: '{output_file}' ({len(ids)} образцов)")


def main():
    """Основная функция."""
    # Стандартные имена файлов
    input_files = ['plate1.csv', 'plate2.csv', 'plate3.csv', 'plate4.csv']
    output_file = 'combined_384_plate.csv'
    
    # Проверка наличия входных файлов
    missing_files = [f for f in input_files if not os.path.exists(f)]
    if missing_files:
        print(f"Ошибка: следующие файлы не найдены: {', '.join(missing_files)}", file=sys.stderr)
        print("Сначала запустите generate_test_plates.py для создания тестовых данных.", file=sys.stderr)
        sys.exit(1)
    
    combine_plates(input_files, output_file)
    
    # Создаём пивот-таблицу
    pivot_output = 'combined_384_plate_pivot.csv'
    create_pivot_table(output_file, pivot_output)
    
    # Создаём список ID
    id_list_output = 'combined_384_plate_ids.txt'
    create_id_list(output_file, id_list_output)


if __name__ == '__main__':
    main()

