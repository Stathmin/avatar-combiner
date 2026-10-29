#!/usr/bin/env python3
"""
Извлечение данных планшетов из Excel файла в CSV формат.
Принимает готовый config от UI или читает config.json в CLI-режиме.
"""

import csv
import math
from pathlib import Path

import app_config

ROWS_96 = ('A', 'B', 'C', 'D', 'E', 'F', 'G', 'H')


def cell_to_id(cell_value):
    """Normalize an Excel cell to a sample id string; blanks/NaN → ''."""
    if cell_value is None:
        return ''
    if isinstance(cell_value, float) and math.isnan(cell_value):
        return ''
    text = str(cell_value).strip()
    if text in ('', 'nan', 'NaN', 'None'):
        return ''
    return text


def empty_plate_data():
    """96 empty wells in row-major A1–A12 … H1–H12 order."""
    return [
        {'id': '', 'row': row, 'column': column}
        for row in ROWS_96
        for column in range(1, 13)
    ]


def observations_column(plate_data):
    """Return well values in A1–A12, B1–B12, … order (one string per well)."""
    by_well = {}
    for item in plate_data:
        row = str(item.get('row', '')).strip().upper()
        try:
            column = int(item.get('column'))
        except (TypeError, ValueError):
            continue
        by_well[(row, column)] = cell_to_id(item.get('id', ''))
    return [
        by_well.get((row, column), '')
        for row in ROWS_96
        for column in range(1, 13)
    ]


def format_observations(plates, include_headers=False):
    """Format one or more plates as newline-separated values for clipboard/paste.

    ``plates`` is an ordered mapping/list of ``(label, values)``.
    Blank wells stay as empty lines. Multiple plates are separated by a blank
    line; optional ``# label`` headers keep sections clear.
    """
    blocks = []
    for label, values in plates:
        lines = list(values)
        if include_headers:
            lines = [f'# {label}', *lines]
        blocks.append('\n'.join(lines))
    return '\n\n'.join(blocks)


def extract_plate_data(workbook, sheet_name, config):
    """
    Извлекает данные планшета из указанного листа Excel.
    
    Args:
        workbook: объект openpyxl Workbook
        sheet_name: имя листа
        config: словарь с конфигурацией
    
    Returns:
        tuple: (данные планшета как список dict, метаданные из первой строки)
    """
    try:
        sheet = workbook[sheet_name]
    except KeyError as exc:
        raise ValueError(f"лист '{sheet_name}' не найден в файле") from exc
    
    data_range = config['data_range']
    start_row = data_range['start_row']  # 3
    end_row = data_range['end_row']      # 10
    start_col = data_range['start_col']  # 2 (B)
    end_col = data_range['end_col']      # 13 (M)
    
    row_labels_col = config['row_labels_col']  # 1 (A)
    column_labels_row = config['column_labels_row']  # 2
    metadata_row = config['metadata_row']  # 1
    
    # Извлекаем метаданные из первой строки (A1:M1)
    metadata_cells = []
    for col in range(1, end_col + 1):
        cell_value = sheet.cell(row=metadata_row, column=col).value
        if cell_value is not None:
            metadata_cells.append(str(cell_value))
    metadata_text = ' '.join(metadata_cells).strip()
    
    # Извлекаем данные из B3:M10 (пустые / NaN → '')
    plate_data = []

    row_idx = 0
    for excel_row in range(start_row, end_row + 1):
        # Получаем метку строки из колонки A
        row_label_cell = sheet.cell(row=excel_row, column=row_labels_col).value
        if row_label_cell is not None and str(row_label_cell).strip():
            row_label = str(row_label_cell).strip().upper()
        else:
            # Если метка отсутствует, используем стандартную последовательность
            row_label = ROWS_96[row_idx] if row_idx < len(ROWS_96) else chr(ord('A') + row_idx)

        # Извлекаем данные из столбцов B-M
        for excel_col in range(start_col, end_col + 1):
            # Получаем метку столбца из строки 2
            col_label_cell = sheet.cell(row=column_labels_row, column=excel_col).value
            if col_label_cell is not None:
                try:
                    col_label = int(col_label_cell)
                except (ValueError, TypeError):
                    col_label = excel_col - start_col + 1
            else:
                col_label = excel_col - start_col + 1

            sample_id = cell_to_id(sheet.cell(row=excel_row, column=excel_col).value)

            plate_data.append({
                'id': sample_id,
                'row': row_label,
                'column': col_label
            })

        row_idx += 1

    return plate_data, metadata_text


def save_plate_csv(plate_data, output_file, log=print):
    """Сохраняет данные планшета в CSV файл."""
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'row', 'column'])
        writer.writeheader()
        writer.writerows(plate_data)

    log(f"Создан файл {output_file}: {len(plate_data)} образцов")


def save_metadata_csv(metadata_dict, output_file='metadata.csv', log=print):
    """Сохраняет метаданные всех планшетов в CSV файл."""
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['plate', 'metadata'])
        writer.writeheader()
        for plate_name in sorted(metadata_dict.keys()):
            writer.writerow({
                'plate': plate_name,
                'metadata': metadata_dict[plate_name]
            })

    log(f"Создан файл метаданных: {output_file}")


def main(config_path='config.json', output_dir=None, base_dir=None, log=print, config=None):
    """Основная функция."""
    config_path = Path(config_path)
    base_dir = Path(base_dir) if base_dir else config_path.parent
    output_dir = Path(output_dir) if output_dir else base_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Готовый config передаёт UI; CLI берёт его из app_config.
    if config is None:
        config, config_error, _source = app_config.load_config(base_dir)
        if config_error:
            raise app_config.ConfigError(config_error)

    excel_file = Path(config['excel_file'])
    if not excel_file.is_absolute():
        excel_file = base_dir / excel_file
    if not excel_file.is_file():
        raise FileNotFoundError(f"файл '{excel_file}' не найден")

    try:
        from openpyxl import load_workbook

        workbook = load_workbook(excel_file, data_only=True)
    except Exception as exc:
        raise ValueError(
            f"не удалось открыть '{excel_file}' ({type(exc).__name__}): {exc}"
        ) from exc
    
    # Selected plates from Excel; missing plate slots (2–4) get empty wells so
    # the 384 layout keeps A–P × 1–24 positions stable.
    metadata_dict = {}
    selected = set(app_config.selected_plate_keys(config))

    try:
        for plate_name in app_config.PLATE_KEYS:
            output_file = output_dir / f'{plate_name}.csv'
            column_file = output_dir / f'{plate_name}_column.txt'

            if plate_name in selected:
                plate_config = config['sheets'][plate_name]
                sheet_name = plate_config['sheet_name']
                plate_data, metadata = extract_plate_data(
                    workbook, sheet_name, config
                )
                if 'metadata' in plate_config and plate_config['metadata']:
                    final_metadata = plate_config['metadata']
                else:
                    final_metadata = (
                        metadata if metadata else f'Метаданные для {plate_name}'
                    )
            else:
                plate_data = empty_plate_data()
                final_metadata = ''
                log(f'{plate_name}: empty slot (no sheet selected)')

            metadata_dict[plate_name] = final_metadata
            save_plate_csv(plate_data, output_file, log=log)
            column_values = observations_column(plate_data)
            column_file.write_text(
                '\n'.join(column_values) + '\n', encoding='utf-8'
            )
            log(f'Создан столбец наблюдений: {column_file.name}')
    finally:
        workbook.close()

    # Сохраняем метаданные
    save_metadata_csv(metadata_dict, output_dir / 'metadata.csv', log=log)

    log(f"\nОбработано {len(selected)} планшетов (+ {4 - len(selected)} пустых слотов)")


if __name__ == '__main__':
    main()

