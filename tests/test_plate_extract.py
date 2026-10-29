"""AV-10: row-major plate observation columns for clipboard paste."""

from pathlib import Path

import extract_plates_from_excel as extract
import run_pipeline
import shutil

WORKBOOK = Path(__file__).resolve().parents[1] / 'src' / 'планшеты соя пробелы.xlsx'


def test_observations_column_is_row_major():
    plate = [
        {'id': 'B1', 'row': 'B', 'column': 1},
        {'id': 'A2', 'row': 'A', 'column': 2},
        {'id': 'A1', 'row': 'A', 'column': 1},
        {'id': '', 'row': 'H', 'column': 12},
    ]
    values = extract.observations_column(plate)
    assert len(values) == 96
    assert values[0] == 'A1'
    assert values[1] == 'A2'
    assert values[12] == 'B1'
    assert values[-1] == ''


def test_format_observations_multiline_and_headers():
    text = extract.format_observations(
        [('пл1', ['a', '', 'c']), ('пл2', ['d'])],
        include_headers=True,
    )
    assert text.splitlines() == ['# пл1', 'a', '', 'c', '', '# пл2', 'd']


def test_pipeline_writes_column_files(tmp_path):
    shutil.copy(WORKBOOK, tmp_path / 'plates.xlsx')
    result = run_pipeline.run(base_dir=tmp_path, log=lambda message: None)

    for name in ('plate1_column.txt', 'plate2_column.txt', 'plate3_column.txt', 'plate4_column.txt'):
        path = result / name
        assert path.is_file()
        lines = path.read_text(encoding='utf-8').splitlines()
        assert len(lines) == 96
