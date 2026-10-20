"""Minimal XLSX reader built on the standard library.

The plate pipeline only needs sheet names and cell values, so this module
supports the parts of the OOXML workbook format used by Excel:

- shared strings, including rich-text runs;
- inline strings;
- numbers, booleans, errors and cached formula results;
- cells addressed by A1 references.

It intentionally does not evaluate formulas or render styles.
"""

import posixpath
import re
import xml.etree.ElementTree as ET
import zipfile

_MAIN_NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
_REL_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
_PKG_REL_NS = 'http://schemas.openxmlformats.org/package/2006/relationships'

_NS = f'{{{_MAIN_NS}}}'
_REL_ID = f'{{{_REL_NS}}}id'
_CELL_REF = re.compile(r'^([A-Z]+)(\d+)$')


class Cell:
    """A cell with a single ``value`` attribute, like openpyxl's read cells."""

    __slots__ = ('value',)

    def __init__(self, value):
        self.value = value


class Sheet:
    """A worksheet backed by a ``(row, column) -> value`` dictionary."""

    def __init__(self, name, cells):
        self.name = name
        self._cells = cells

    def cell(self, row, column):
        return Cell(self._cells.get((row, column)))


class Workbook:
    """Workbook facade compatible with the small part of openpyxl we use."""

    def __init__(self, filename, **_kwargs):
        self._zip = zipfile.ZipFile(filename)
        self._shared_strings = _read_shared_strings(self._zip)
        self._sheet_targets = _read_sheet_targets(self._zip)
        self._sheets = {}

    @property
    def sheetnames(self):
        return list(self._sheet_targets)

    def __getitem__(self, sheet_name):
        if sheet_name not in self._sheet_targets:
            raise KeyError(sheet_name)
        if sheet_name not in self._sheets:
            cells = _read_cells(
                self._zip,
                self._sheet_targets[sheet_name],
                self._shared_strings,
            )
            self._sheets[sheet_name] = Sheet(sheet_name, cells)
        return self._sheets[sheet_name]

    def close(self):
        self._zip.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def load_workbook(filename, **_kwargs):
    """Open an ``.xlsx``/``.xlsm`` workbook without third-party packages."""
    return Workbook(filename)


def _read_shared_strings(archive):
    try:
        data = archive.read('xl/sharedStrings.xml')
    except KeyError:
        return []

    root = ET.fromstring(data)
    return [
        ''.join(node.text or '' for node in item.iter(f'{_NS}t'))
        for item in root.findall(f'{_NS}si')
    ]


def _read_sheet_targets(archive):
    workbook = ET.fromstring(archive.read('xl/workbook.xml'))
    relationships = ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))

    targets = {
        rel.get('Id'): rel.get('Target')
        for rel in relationships.findall(f'{{{_PKG_REL_NS}}}Relationship')
    }

    result = {}
    sheets = workbook.find(f'{_NS}sheets')
    if sheets is None:
        return result

    for sheet in sheets.findall(f'{_NS}sheet'):
        relationship_id = sheet.get(_REL_ID)
        target = targets.get(relationship_id)
        if target is None:
            continue
        result[sheet.get('name')] = _normalize_target(target)
    return result


def _normalize_target(target):
    if target.startswith('/'):
        return target.lstrip('/')
    return posixpath.normpath(posixpath.join('xl', target))


def _read_cells(archive, sheet_target, shared_strings):
    root = ET.fromstring(archive.read(sheet_target))
    sheet_data = root.find(f'{_NS}sheetData')
    if sheet_data is None:
        return {}

    cells = {}
    auto_row = 0

    for row in sheet_data.findall(f'{_NS}row'):
        auto_row += 1
        row_number = int(row.get('r')) if row.get('r') else auto_row
        auto_column = 0

        for cell in row.findall(f'{_NS}c'):
            ref = cell.get('r')
            if ref:
                match = _CELL_REF.match(ref)
                if not match:
                    continue
                column = _column_index(match.group(1))
                cell_row = int(match.group(2))
            else:
                auto_column += 1
                column = auto_column
                cell_row = row_number

            auto_column = max(auto_column, column)
            value = _cell_value(cell, shared_strings)
            if value is not None:
                cells[(cell_row, column)] = value

    return cells


def _cell_value(cell, shared_strings):
    cell_type = cell.get('t')

    if cell_type == 'inlineStr':
        inline = cell.find(f'{_NS}is')
        return _text(inline) if inline is not None else None

    value_node = cell.find(f'{_NS}v')
    if value_node is None:
        return None

    raw = value_node.text or ''
    if cell_type == 's':
        try:
            return shared_strings[int(raw)]
        except (IndexError, ValueError):
            return raw
    if cell_type == 'b':
        return 'TRUE' if raw == '1' else 'FALSE'
    if cell_type in ('str', 'e', 'd'):
        return raw

    return _number_text(raw)


def _text(node):
    return ''.join(child.text or '' for child in node.iter(f'{_NS}t'))


def _number_text(raw):
    if raw == '':
        return None
    try:
        number = float(raw)
    except ValueError:
        return raw
    return str(int(number)) if number.is_integer() else raw


def _column_index(letters):
    index = 0
    for letter in letters:
        index = index * 26 + (ord(letter) - ord('A') + 1)
    return index
