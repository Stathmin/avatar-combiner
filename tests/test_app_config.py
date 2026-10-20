import shutil
from pathlib import Path

import pytest

import app_config

WORKBOOK = Path(__file__).resolve().parents[1] / 'src' / 'планшеты соя пробелы.xlsx'


def workbook_in(tmp_path):
    shutil.copy(WORKBOOK, tmp_path / 'plates.xlsx')
    return tmp_path / 'plates.xlsx'


def test_discovers_workbook_and_first_four_sheets(tmp_path):
    workbook_in(tmp_path)

    config, error, source = app_config.load_config(tmp_path)

    assert error is None
    assert source == 'auto'
    assert config['excel_file'] == 'plates.xlsx'
    assert [item['sheet_name'] for item in config['sheets'].values()] == [
        'пл1',
        'пл2',
        'пл3',
        'пл4',
    ]
    assert config['data_range'] == app_config.DEFAULT_RANGE


def test_explicit_sheet_order_and_range(tmp_path):
    workbook_in(tmp_path)

    config = app_config.build_config(
        tmp_path,
        sheets=['пл2', 'пл1', 'пл4', 'пл3'],
        data_range=app_config.parse_range('B4:M9'),
    )

    assert [item['sheet_name'] for item in config['sheets'].values()] == [
        'пл2',
        'пл1',
        'пл4',
        'пл3',
    ]
    assert config['data_range'] == {
        'start_row': 4,
        'end_row': 9,
        'start_col': 2,
        'end_col': 13,
    }


def test_unknown_sheet_is_rejected(tmp_path):
    workbook_in(tmp_path)

    with pytest.raises(app_config.ConfigError, match='sheet not found'):
        app_config.build_config(tmp_path, sheets=['a', 'b', 'c', 'd'])


def test_missing_workbook_is_not_fatal_for_load(tmp_path):
    config, error, source = app_config.load_config(tmp_path)

    assert config is None
    assert 'no Excel file' in error
    assert source == 'auto'


def test_parse_range_rejects_garbage():
    with pytest.raises(app_config.ConfigError):
        app_config.parse_range('not-a-range')


def test_existing_config_json_wins(tmp_path):
    (tmp_path / 'config.json').write_text('{"excel_file": "x.xlsx"}', encoding='utf-8')

    config, error, source = app_config.load_config(tmp_path)

    assert error is None
    assert source == 'config.json'
    assert config == {'excel_file': 'x.xlsx'}
