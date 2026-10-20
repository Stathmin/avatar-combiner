import shutil
from pathlib import Path

import pytest

import run_pipeline

WORKBOOK = Path(__file__).resolve().parents[1] / 'src' / 'планшеты соя пробелы.xlsx'


def test_run_uses_provided_config(tmp_path, monkeypatch):
    shutil.copy(WORKBOOK, tmp_path / 'plates.xlsx')
    seen = {}
    monkeypatch.setattr(
        run_pipeline.extract_plates_from_excel,
        'main',
        lambda **kwargs: seen.update(kwargs),
    )
    monkeypatch.setattr(run_pipeline.combine_plates, 'main', lambda **kwargs: None)
    config = {
        'excel_file': 'plates.xlsx',
        'sheets': {
            'plate1': {'sheet_name': 'пл1'},
            'plate2': {'sheet_name': 'пл2'},
            'plate3': {'sheet_name': 'пл3'},
            'plate4': {'sheet_name': 'пл4'},
        },
        'data_range': {'start_row': 3, 'end_row': 10, 'start_col': 2, 'end_col': 13},
    }

    result = run_pipeline.run(base_dir=tmp_path, config=config, log=lambda message: None)

    assert seen['config']['excel_file'] == 'plates.xlsx'
    assert result.name.startswith('Результат')


def test_missing_workbook_creates_no_result(tmp_path):
    config = {
        'excel_file': 'missing.xlsx',
        'sheets': {
            'plate1': {'sheet_name': 'a'},
            'plate2': {'sheet_name': 'b'},
            'plate3': {'sheet_name': 'c'},
            'plate4': {'sheet_name': 'd'},
        },
        'data_range': {'start_row': 3, 'end_row': 10, 'start_col': 2, 'end_col': 13},
    }

    with pytest.raises(run_pipeline.PipelineError):
        run_pipeline.run(base_dir=tmp_path, config=config, log=lambda message: None)

    assert not (tmp_path / 'Результат 1').exists()


def test_invalid_range_creates_no_result(tmp_path):
    shutil.copy(WORKBOOK, tmp_path / 'plates.xlsx')
    config = {
        'excel_file': 'plates.xlsx',
        'sheets': {
            'plate1': {'sheet_name': 'пл1'},
            'plate2': {'sheet_name': 'пл2'},
            'plate3': {'sheet_name': 'пл3'},
            'plate4': {'sheet_name': 'пл4'},
        },
        'data_range': {'start_row': 10, 'end_row': 3, 'start_col': 2, 'end_col': 13},
    }

    with pytest.raises(run_pipeline.PipelineError):
        run_pipeline.run(base_dir=tmp_path, config=config, log=lambda message: None)

    assert not (tmp_path / 'Результат 1').exists()


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
