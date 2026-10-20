import shutil
from pathlib import Path

import run_pipeline

WORKBOOK = Path(__file__).resolve().parents[1] / 'src' / 'планшеты соя пробелы.xlsx'


def test_run_uses_provided_config(tmp_path, monkeypatch):
    seen = {}
    monkeypatch.setattr(
        run_pipeline.extract_plates_from_excel,
        'main',
        lambda **kwargs: seen.update(kwargs),
    )
    monkeypatch.setattr(run_pipeline.combine_plates, 'main', lambda **kwargs: None)
    config = {
        'excel_file': 'x.xlsx',
        'sheets': {'plate1': {'sheet_name': 'a'}},
        'data_range': {'start_row': 3, 'end_row': 10, 'start_col': 2, 'end_col': 13},
    }
    (tmp_path / 'x.xlsx').write_bytes(b'x')

    result = run_pipeline.run(base_dir=tmp_path, config=config, log=lambda message: None)

    assert seen['config'] is config
    assert result.name.startswith('Результат')


def test_run_auto_detects_workbook_without_config(tmp_path, monkeypatch):
    shutil.copy(WORKBOOK, tmp_path / 'plates.xlsx')
    seen = {}
    monkeypatch.setattr(
        run_pipeline.extract_plates_from_excel,
        'main',
        lambda **kwargs: seen.update(kwargs),
    )
    monkeypatch.setattr(run_pipeline.combine_plates, 'main', lambda **kwargs: None)

    run_pipeline.run(base_dir=tmp_path, log=lambda message: None)

    assert [item['sheet_name'] for item in seen['config']['sheets'].values()] == [
        'пл1',
        'пл2',
        'пл3',
        'пл4',
    ]
