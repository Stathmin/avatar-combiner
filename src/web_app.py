"""Local web interface for the plate combiner.

Run with ``run_pipeline.py --web``. NiceGUI serves a single-user app on
127.0.0.1; no data leaves the machine. The command line stays available.
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

from nicegui import ui

import app_config
import pcr_tools
import plate_layout
import report_xlsx
import run_pipeline
import seq_import
import seq_structure
import tools as genetics


class State:
    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        self.config, self.error, _source = app_config.load_config(self.base_dir)
        self.logs = []
        self.running = False
        self.last_result = None
        self.uploads = self.base_dir / '.uploads'
        self.uploads.mkdir(exist_ok=True)

    def workbooks(self):
        found = app_config.discover_excel(self.base_dir)
        return found + sorted(self.uploads.glob('*.xlsx'))

    def sheets(self):
        if not self.config:
            return []
        try:
            path = self.config_path()
            return app_config.sheet_names(path)
        except Exception:
            return []

    def config_path(self):
        path = Path(self.config.get('excel_file', ''))
        return path if path.is_absolute() else self.base_dir / path

    def apply(self, excel_file, sheets, range_text):
        config = app_config.build_config(
            self.base_dir,
            excel_file=excel_file,
            sheets=sheets,
            data_range=app_config.parse_range(range_text),
        )
        self.config = config
        self.error = None
        return config


def build_app(base_dir):
    state = State(base_dir)

    def drain_logs(element):
        while state.logs:
            element.push(state.logs.pop(0))

    def download_file(path):
        path = Path(path)
        ui.download(str(path), filename=path.name)

    def result_files(folder):
        return sorted(path for path in Path(folder).iterdir() if path.is_file())

    def render_result(folder, container):
        container.clear()
        with container:
            ui.label(f'Result: {Path(folder).name}').classes('text-lg font-bold')
            manifest = Path(folder) / 'manifest.json'
            if manifest.is_file():
                data = json.loads(manifest.read_text(encoding='utf-8'))
                ui.code(json.dumps(data, ensure_ascii=False, indent=2), language='json')
            with ui.row().classes('flex-wrap'):
                for path in result_files(folder):
                    ui.button(
                        path.name,
                        on_click=lambda path=path: download_file(path),
                    ).props('flat dense')

    @ui.page('/')
    def index():
        ui.page_title('Avatar Combiner')
        with ui.header().classes('items-center justify-between'):
            ui.label('Avatar Combiner').classes('text-xl font-bold')
            with ui.row():
                ui.link('Tools', '/tools')
                ui.link('Results', '/results')

        if state.error:
            ui.label(state.error).classes('text-red-600')

        workbooks = state.workbooks()
        options = {str(path): path.name for path in workbooks}
        current = str(state.config_path()) if state.config else None
        if current not in options:
            current = None

        with ui.card().classes('w-full'):
            ui.label('Workbook').classes('text-lg font-bold')
            workbook_select = ui.select(
                options,
                value=current,
                label='Excel file',
            ).classes('w-96')
            upload = ui.upload(
                label='Upload .xlsx',
                auto_upload=True,
                max_file_size=50_000_000,
            )

        with ui.card().classes('w-full'):
            ui.label('Sheets').classes('text-lg font-bold')
            sheet_row = ui.row().classes('w-full')

        range_input = ui.input(
            'Data range',
            value='B3:M10',
        ).classes('w-60')

        log = ui.log(max_lines=1000).classes('w-full h-64 font-mono text-xs')
        result_box = ui.column().classes('w-full')
        ui.timer(0.3, lambda: drain_logs(log))

        def current_sheets():
            values = []
            for index in range(4):
                select = sheet_selects[index]
                values.append(select.value)
            return values

        sheet_selects = []
        with sheet_row:
            for index in range(4):
                sheet_selects.append(
                    ui.select([], label=f'Plate {index + 1}').classes('w-56')
                )

        def load_sheets():
            names = state.sheets()
            defaults = [''] * 4
            if state.config:
                defaults = [
                    state.config['sheets'][f'plate{index}']['sheet_name']
                    for index in range(1, 5)
                ]
            for index, select in enumerate(sheet_selects):
                select.options = names
                select.value = defaults[index] if defaults[index] in names else (
                    names[index] if index < len(names) else None
                )
                select.update()

        def on_workbook(event):
            if not event.value:
                return
            try:
                state.apply(event.value, None, range_input.value)
            except Exception as exc:
                ui.notify(str(exc), type='negative')
                return
            load_sheets()

        workbook_select.on_value_change(on_workbook)

        async def on_upload(event):
            name = Path(event.file.name).name
            target = state.uploads / name
            target.write_bytes(await event.file.read())
            try:
                state.config = app_config.build_config(
                    state.base_dir, excel_file=target
                )
                state.error = None
            except Exception as exc:
                ui.notify(str(exc), type='negative')
                return
            workbook_select.options = {
                str(path): path.name for path in state.workbooks()
            }
            workbook_select.value = str(target)
            workbook_select.update()
            load_sheets()
            ui.notify(f'Uploaded {name}', type='positive')

        upload.on_upload(on_upload)

        async def run_now():
            if state.running:
                return
            try:
                excel = workbook_select.value
                sheets = [value for value in current_sheets() if value]
                config = state.apply(excel, sheets, range_input.value)
            except Exception as exc:
                ui.notify(str(exc), type='negative')
                return

            state.running = True
            result_box.clear()
            log.clear()
            button.props('loading')
            try:
                result = await asyncio.to_thread(
                    run_pipeline.run,
                    base_dir=state.base_dir,
                    log=lambda message: state.logs.append(str(message)),
                    config=config,
                )
            except SystemExit as exc:
                ui.notify(f'Run failed: {exc}', type='negative')
            except Exception as exc:
                ui.notify(str(exc), type='negative')
            else:
                state.last_result = result
                render_result(result, result_box)
                ui.notify(f'Done: {result.name}', type='positive')
            finally:
                state.running = False
                button.props(remove='loading')

        button = ui.button('Run', on_click=run_now).props('color=primary')
        load_sheets()

    @ui.page('/results')
    def results_page():
        ui.page_title('Results')
        with ui.header().classes('items-center justify-between'):
            ui.label('Results').classes('text-xl font-bold')
            with ui.row():
                ui.link('Home', '/')
                ui.link('Tools', '/tools')

        folders = sorted(
            (
                path
                for path in state.base_dir.iterdir()
                if path.is_dir() and run_pipeline.RESULT_DIR_PATTERN.match(path.name)
            ),
            key=lambda path: path.name,
            reverse=True,
        )
        if not folders:
            ui.label('No results yet.')
            return

        for folder in folders:
            with ui.card().classes('w-full'):
                render_result(folder, ui.column().classes('w-full'))

    @ui.page('/tools')
    def tools_page():
        ui.page_title('Genetics tools')
        with ui.header().classes('items-center justify-between'):
            ui.label('Genetics tools').classes('text-xl font-bold')
            with ui.row():
                ui.link('Home', '/')
                ui.link('Results', '/results')

        def show(container, text):
            container.clear()
            with container:
                ui.code(str(text)).classes('w-full')

        def safe_show(container, function):
            try:
                show(container, function())
            except Exception as exc:
                show(container, f'Error: {exc}')

        with ui.tabs().classes('w-full') as tabs:
            tm_tab = ui.tab('Primer Tm')
            pair_tab = ui.tab('Primer pair')
            dna_tab = ui.tab('DNA')
            units_tab = ui.tab('Units')
            structure_tab = ui.tab('Structure')
            pcr_tab = ui.tab('PCR')
            files_tab = ui.tab('Files')

        with ui.tab_panels(tabs, value=tm_tab).classes('w-full'):
            with ui.tab_panel(tm_tab):
                sequence = ui.input('Sequence')
                out = ui.column()
                ui.button(
                    'Analyse',
                    on_click=lambda: safe_show(
                        out, lambda: _primer_report(genetics.analyze_primer(sequence.value))
                    ),
                )

            with ui.tab_panel(pair_tab):
                forward = ui.input('Forward')
                reverse = ui.input('Reverse')
                out = ui.column()
                ui.button(
                    'Analyse pair',
                    on_click=lambda: safe_show(
                        out,
                        lambda: _pair_report(
                            genetics.analyze_pair(forward.value, reverse.value)
                        ),
                    ),
                )

            with ui.tab_panel(dna_tab):
                sequence = ui.input('Sequence')
                out = ui.column()
                ui.button(
                    'Transform',
                    on_click=lambda: safe_show(out, lambda: _dna_report(sequence.value)),
                )

            with ui.tab_panel(units_tab):
                quantity = ui.input('Value', placeholder='25 uM')
                target = ui.input('Target unit', placeholder='nM')
                out = ui.column()
                ui.button(
                    'Convert',
                    on_click=lambda: safe_show(
                        out,
                        lambda: '\n'.join(
                            f'{unit} {genetics.format_number(amount)}'
                            for unit, amount in genetics.convert_text(
                                quantity.value, target.value
                            )
                        ),
                    ),
                )

            with ui.tab_panel(structure_tab):
                sequence = ui.input('Sequence')
                out = ui.column()
                ui.button(
                    'Fold',
                    on_click=lambda: safe_show(
                        out,
                        lambda: _structure_report(
                            seq_structure.analyze_structure(sequence.value)
                        ),
                    ),
                )

            with ui.tab_panel(pcr_tab):
                template = ui.textarea('Template')
                forward = ui.input('Forward')
                reverse = ui.input('Reverse')
                out = ui.column()
                ui.button(
                    'Simulate',
                    on_click=lambda: safe_show(
                        out,
                        lambda: _pcr_report(
                            pcr_tools.simulate_pcr(
                                template.value,
                                forward.value,
                                reverse.value,
                            )
                        ),
                    ),
                )

            with ui.tab_panel(files_tab):
                out = ui.column()

                async def on_sequence(event):
                    suffix = Path(event.file.name).suffix.lower()
                    target = Path(tempfile.mkdtemp()) / f'input{suffix}'
                    target.write_bytes(await event.file.read())
                    safe_show(
                        out, lambda: _sequence_report(seq_import.load_sequence(target))
                    )

                async def on_layout(event):
                    target = Path(tempfile.mkdtemp()) / 'plate.toml'
                    target.write_bytes(await event.file.read())
                    safe_show(
                        out, lambda: _layout_report(plate_layout.load_layout(target))
                    )

                ui.label('Sequence file (.gb, .dna, .fa)')
                ui.upload(on_upload=on_sequence, auto_upload=True)
                ui.label('Wellmap layout (.toml)')
                ui.upload(on_upload=on_layout, auto_upload=True)

                result_dirs = sorted(
                    path.name
                    for path in state.base_dir.iterdir()
                    if path.is_dir()
                    and run_pipeline.RESULT_DIR_PATTERN.match(path.name)
                )
                folder = ui.select(result_dirs, label='Result folder')
                ui.button(
                    'Export XLSX',
                    on_click=lambda: safe_show(
                        out,
                        lambda: str(
                            report_xlsx.export_workbook(
                                state.base_dir / folder.value
                            )
                        ),
                    ),
                )

    return state


def _primer_report(report):
    return '\n'.join(
        [
            f'sequence {report.sequence}',
            f'length   {report.length} nt',
            f'GC       {report.gc:.1f}%',
            f'Tm       {report.tm:.1f} C',
            f'hairpin  {_thermo(report.hairpin)}',
            f'dimer    {_thermo(report.homodimer)}',
        ]
    )


def _pair_report(report):
    return '\n'.join(
        [
            f'forward  {report.forward.sequence}  Tm {report.forward.tm:.1f} C',
            f'reverse  {report.reverse.sequence}  Tm {report.reverse.tm:.1f} C',
            f'dT       {abs(report.forward.tm - report.reverse.tm):.1f} C',
            f'hetero   {_thermo(report.heterodimer)}',
            f"3' end   {_thermo(report.end_stability)}",
        ]
    )


def _dna_report(sequence):
    sequence = genetics.normalize_dna(sequence)
    return '\n'.join(
        [
            f'length     {len(sequence)} nt',
            f'GC         {genetics.gc_content(sequence):.1f}%',
            f'complement {genetics.complement(sequence)}',
            f'reverse    {genetics.reverse(sequence)}',
            f'revcomp    {genetics.reverse_complement(sequence)}',
        ]
    )


def _structure_report(report):
    dg = 'n/a' if report.dg is None else f'{report.dg:.2f} kcal/mol'
    tm = 'n/a' if report.tm is None else f'{report.tm:.1f} C'
    return '\n'.join(
        [
            f'sequence {report.sequence}',
            f'dG       {dg}',
            f'Tm       {tm}',
            f'fold     {report.dot_bracket}',
        ]
    )


def _pcr_report(report):
    return '\n'.join(
        [
            f'product  {report.length} nt',
            f'sequence {report.sequence}',
        ]
    )


def _sequence_report(record):
    return '\n'.join(
        [
            f'name      {record.name}',
            f'format    {record.source_format}',
            f'length    {len(record.sequence)} nt',
            f'topology  {record.topology}',
            f'records   {record.record_count}',
            f'features  {len(record.features)}',
        ]
    )


def _layout_report(report):
    return '\n'.join(
        [
            f'wells       {report.wells}',
            f'conditions  {", ".join(report.conditions) or "none"}',
        ]
    )


def _thermo(result):
    if not getattr(result, 'structure_found', False):
        return 'none'
    return f'Tm {result.tm:.1f} C, dG {result.dg / 1000.0:.2f} kcal/mol'


def main(base_dir=None, port=8080, show=True):
    build_app(base_dir or run_pipeline.application_dir())
    ui.run(
        host='127.0.0.1',
        port=port,
        title='Avatar Combiner',
        favicon='◈',
        reload=False,
        show=show,
        dark=None,
    )
