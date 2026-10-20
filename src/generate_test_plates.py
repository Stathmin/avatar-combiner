#!/usr/bin/env python3
"""
Генерация тестовых данных для 4 планшетов 96-луночного формата.
Создаёт 4 CSV файла с уникальными ID образцов.
"""

import csv


def generate_plate(filename, start_id):
    """
    Генерирует CSV файл для одного 96-луночного планшета.
    
    Args:
        filename: имя выходного файла
        start_id: начальный номер для ID образцов (1-based)
    """
    rows_96 = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    columns_96 = list(range(1, 13))  # 1-12
    
    samples = []
    sample_num = start_id
    
    for row in rows_96:
        for col in columns_96:
            sample_id = f"S{sample_num:03d}"
            samples.append({
                'id': sample_id,
                'row': row,
                'column': col
            })
            sample_num += 1
    
    # Запись в CSV
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'row', 'column'])
        writer.writeheader()
        writer.writerows(samples)
    
    print(f"Создан файл {filename}: {len(samples)} образцов (ID {samples[0]['id']}-{samples[-1]['id']})")


def main():
    """Генерирует 4 планшета с уникальными ID."""
    plates = [
        ('plate1.csv', 1),
        ('plate2.csv', 97),
        ('plate3.csv', 193),
        ('plate4.csv', 289)
    ]
    
    for filename, start_id in plates:
        generate_plate(filename, start_id)
    
    print("\nВсего создано: 4 планшета, 384 образца (S001-S384)")


if __name__ == '__main__':
    main()

