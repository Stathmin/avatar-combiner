"""Export pipeline CSV results to one formatted XLSX workbook.

pandas and openpyxl are imported inside export_workbook so the TUI does not pay
their import cost at startup.
"""

from __future__ import annotations

from pathlib import Path

from tools import ToolError

SHEETS = (
    ('combined', 'combined_384_plate.csv'),
    ('pivot', 'combined_384_plate_pivot.csv'),
    ('metadata', 'metadata.csv'),
    ('plate1', 'plate1.csv'),
    ('plate2', 'plate2.csv'),
    ('plate3', 'plate3.csv'),
    ('plate4', 'plate4.csv'),
)


def export_workbook(result_dir):
    """Write available CSV files from a result folder into one XLSX."""
    result_dir = Path(result_dir)
    if not result_dir.is_dir():
        raise ToolError(f'folder not found: {result_dir}')

    available = [
        (sheet, result_dir / filename)
        for sheet, filename in SHEETS
        if (result_dir / filename).is_file()
    ]
    if not available:
        raise ToolError(f'no CSV files in {result_dir}')

    import pandas as pd
    from openpyxl import load_workbook
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter

    output = result_dir / 'combined_384_plate.xlsx'
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet, path in available:
            pd.read_csv(path).to_excel(writer, sheet_name=sheet, index=False)

    workbook = load_workbook(output)
    for sheet in workbook.worksheets:
        sheet.freeze_panes = 'A2'
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        for column in sheet.columns:
            width = max(len(str(cell.value or '')) for cell in column) + 2
            sheet.column_dimensions[get_column_letter(column[0].column)].width = min(width, 40)
    workbook.save(output)

    return output
