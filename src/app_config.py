"""Configuration discovery without a required config.json.

The app auto-detects the workbook in its folder and takes the first four sheets.
The config screen can change the file, the sheets and the data range for the
current session; no JSON file has to exist or be edited.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from xlsx_reader import load_workbook

EXCEL_SUFFIXES = ('.xlsx', '.xlsm')
PLATE_KEYS = ('plate1', 'plate2', 'plate3', 'plate4')

DEFAULT_RANGE = {
    'start_row': 3,
    'end_row': 10,
    'start_col': 2,
    'end_col': 13,
}

_RANGE_RE = re.compile(r'^([A-Za-z]+)(\d+)\s*[:\-]\s*([A-Za-z]+)(\d+)$')


class ConfigError(ValueError):
    """Raised when the workbook, sheets or range cannot be used."""


def discover_excel(base_dir):
    """Return Excel workbooks in a folder, ignoring Office lock files."""
    base = Path(base_dir)
    if not base.is_dir():
        return []
    return sorted(
        path
        for path in base.iterdir()
        if path.is_file()
        and path.suffix.lower() in EXCEL_SUFFIXES
        and not path.name.startswith('~$')
    )


def sheet_names(path):
    """Return sheet names from an Excel workbook."""
    with load_workbook(path) as workbook:
        return workbook.sheetnames


def build_config(base_dir, excel_file=None, sheets=None, data_range=None):
    """Build a runtime config from a workbook and optional selections."""
    base = Path(base_dir)

    if excel_file:
        path = Path(excel_file)
        if not path.is_absolute():
            path = base / path
    else:
        found = discover_excel(base)
        if not found:
            raise ConfigError(f'no Excel file in {base}')
        path = found[0]

    if not path.is_file():
        raise ConfigError(f'Excel file not found: {path}')

    try:
        available = sheet_names(path)
    except Exception as exc:
        raise ConfigError(f'cannot read {path.name}: {exc}') from exc

    if sheets is None:
        sheets = available[:4]
    sheets = [str(name).strip() for name in sheets]
    if len(sheets) != 4:
        raise ConfigError('select exactly four sheets')
    if len(set(sheets)) != 4:
        raise ConfigError('sheet names must be unique')

    missing = [name for name in sheets if name not in available]
    if missing:
        raise ConfigError(f"sheet not found: {', '.join(missing)}")

    selected_range = dict(DEFAULT_RANGE)
    if data_range:
        selected_range.update(data_range)

    return {
        'excel_file': _relative_name(path, base),
        'sheets': {
            key: {'sheet_name': name}
            for key, name in zip(PLATE_KEYS, sheets)
        },
        'data_range': selected_range,
        'row_labels_col': 1,
        'column_labels_row': 2,
        'metadata_row': 1,
    }


def load_config(base_dir):
    """Return ``(config, error, source)``.

    An existing ``config.json`` wins for backwards compatibility. Without one,
    the workbook is auto-discovered; that is not an error.
    """
    path = Path(base_dir) / 'config.json'
    if path.exists():
        try:
            with open(path, encoding='utf-8') as config_file:
                return json.load(config_file), None, 'config.json'
        except (OSError, json.JSONDecodeError) as exc:
            return None, str(exc), 'config.json'

    try:
        return build_config(base_dir), None, 'auto'
    except ConfigError as exc:
        return None, str(exc), 'auto'


def parse_range(text):
    """Parse ``B3:M10`` into the data_range dictionary."""
    match = _RANGE_RE.match(str(text).strip())
    if not match:
        raise ConfigError('use a range like B3:M10')

    start_col, start_row, end_col, end_row = match.groups()
    start_col = _column_index(start_col)
    end_col = _column_index(end_col)
    start_row, end_row = int(start_row), int(end_row)

    if start_row < 1 or start_col < 1 or end_row < start_row or end_col < start_col:
        raise ConfigError('range must run from the top-left to the bottom-right')

    return {
        'start_row': start_row,
        'end_row': end_row,
        'start_col': start_col,
        'end_col': end_col,
    }


def update_sheets(config, names):
    """Return a config with four new sheet names, preserving the range."""
    config = dict(config)
    config['sheets'] = {
        key: {'sheet_name': name}
        for key, name in zip(PLATE_KEYS, names)
    }
    return config


def _relative_name(path, base):
    try:
        return str(path.resolve().relative_to(base.resolve()))
    except ValueError:
        return str(path)


def _column_index(letters):
    index = 0
    for char in letters.upper():
        index = index * 26 + (ord(char) - ord('A') + 1)
    return index
