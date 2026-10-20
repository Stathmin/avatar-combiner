import zipfile
from pathlib import Path

import pytest

from xlsx_reader import load_workbook

WORKBOOK = Path(__file__).resolve().parents[1] / 'src' / 'планшеты соя пробелы.xlsx'


def test_reads_bundled_workbook():
    with load_workbook(WORKBOOK) as workbook:
        assert 'пл1' in workbook.sheetnames
        sheet = workbook['пл1']

        assert sheet.cell(2, 2).value == '1'
        assert sheet.cell(3, 1).value == 'A'
        assert sheet.cell(3, 2).value == '1924 1.1'
        assert sheet.cell(3, 13).value == '1924 35.2'
        assert sheet.cell(10, 13).value is None
        assert sheet.cell(100, 100).value is None


def test_missing_sheet_raises_key_error():
    with load_workbook(WORKBOOK) as workbook:
        with pytest.raises(KeyError):
            workbook['missing']


def test_inline_strings_rich_text_and_cached_values(tmp_path):
    path = tmp_path / 'tiny.xlsx'
    workbook_xml = (
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    relationships_xml = (
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/>'
        '</Relationships>'
    )
    sheet_xml = (
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData><row r="1">'
        '<c r="A1" t="inlineStr"><is><r><t>Hello</t></r>'
        '<r><t> world</t></r></is></c>'
        '<c r="B1" t="str"><v>cached</v></c>'
        '<c r="C1" t="n"><v>42</v></c>'
        '<c r="D1" t="b"><v>1</v></c>'
        '<c r="E1" t="e"><v>#N/A</v></c>'
        '</row></sheetData></worksheet>'
    )

    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('xl/workbook.xml', workbook_xml)
        archive.writestr('xl/_rels/workbook.xml.rels', relationships_xml)
        archive.writestr('xl/worksheets/sheet1.xml', sheet_xml)

    with load_workbook(path) as workbook:
        sheet = workbook['Sheet1']
        assert sheet.cell(1, 1).value == 'Hello world'
        assert sheet.cell(1, 2).value == 'cached'
        assert sheet.cell(1, 3).value == '42'
        assert sheet.cell(1, 4).value == 'TRUE'
        assert sheet.cell(1, 5).value == '#N/A'
