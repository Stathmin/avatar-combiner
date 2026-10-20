"""Local web interface for the plate combiner.

Run with ``run_pipeline.py --web``. NiceGUI serves a single-user app on
127.0.0.1; no data leaves the machine. The command line stays available.
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

from nicegui import context, ui

import app_config
import pcr_tools
import plate_layout
import report_xlsx
import run_pipeline
import seq_import
import seq_structure
import tools as genetics

TOOLS = (
    ('tm', 'primer_tm'),
    ('pair', 'primer_pair'),
    ('dna', 'dna'),
    ('units', 'units'),
    ('structure', 'structure'),
    ('pcr', 'pcr'),
    ('import', 'import_seq'),
    ('layout', 'plate_layout'),
    ('xlsx', 'xlsx_export'),
)

LANG = {'code': 'en'}

TEXTS = {
    'en': {
        'pipeline': 'Pipeline',
        'results': 'Results',
        'genetics_tools': 'GENETICS TOOLS',
        'language': 'Language',
        'workbook': 'Workbook',
        'excel_file': 'Excel file',
        'upload_xlsx': 'Upload .xlsx',
        'sheets': 'Sheets',
        'plate': 'Plate',
        'data_range': 'Data range',
        'run': 'Run',
        'all_tools': 'All tools',
        'result': 'Result',
        'primer_tm': 'Primer Tm',
        'primer_pair': 'Primer pair',
        'dna': 'DNA',
        'units': 'Units',
        'structure': 'Structure',
        'pcr': 'PCR',
        'files': 'Files',
        'import_seq': 'Import sequence',
        'plate_layout': 'Plate layout',
        'xlsx_export': 'XLSX export',
        'sequence': 'Sequence',
        'forward': 'Forward',
        'reverse': 'Reverse',
        'template': 'Template',
        'value': 'Value',
        'target_unit': 'Target unit',
        'result_folder': 'Result folder',
        'upload_sequence': 'Sequence file (.gb, .dna, .fa)',
        'upload_layout': 'Wellmap layout (.toml)',
        'analyse': 'Analyse',
        'analyse_pair': 'Analyse pair',
        'transform': 'Transform',
        'convert': 'Convert',
        'fold': 'Fold',
        'simulate': 'Simulate',
        'export_xlsx': 'Export XLSX',
        'no_results': 'No results yet.',
        'uploaded': 'Uploaded',
        'failed': 'Run failed',
        'done': 'Done',
        'length': 'length',
        'gc': 'GC',
        'tm': 'Tm',
        'hairpin': 'hairpin',
        'dimer': 'dimer',
        'hetero': 'hetero',
        'end3': "3' end",
        'complement': 'complement',
        'reverse_seq': 'reverse',
        'revcomp': 'revcomp',
        'product': 'product',
        'wells': 'wells',
        'conditions': 'conditions',
        'name': 'name',
        'format': 'format',
        'topology': 'topology',
        'records': 'records',
        'features': 'features',
        'dg': 'dG',
        'fold_label': 'fold',
        'error': 'Error',
    },
    'ru': {
        'pipeline': 'Пайплайн',
        'results': 'Результаты',
        'genetics_tools': 'ГЕНЕТИЧЕСКИЕ ИНСТРУМЕНТЫ',
        'language': 'Язык',
        'workbook': 'Файл Excel',
        'excel_file': 'Файл Excel',
        'upload_xlsx': 'Загрузить .xlsx',
        'sheets': 'Листы',
        'plate': 'Планшет',
        'data_range': 'Диапазон',
        'run': 'Запустить',
        'all_tools': 'Все инструменты',
        'result': 'Результат',
        'primer_tm': 'Tm праймера',
        'primer_pair': 'Пара праймеров',
        'dna': 'ДНК',
        'units': 'Единицы',
        'structure': 'Структура',
        'pcr': 'ПЦР',
        'files': 'Файлы',
        'import_seq': 'Импорт последовательности',
        'plate_layout': 'Раскладка планшета',
        'xlsx_export': 'Экспорт XLSX',
        'sequence': 'Последовательность',
        'forward': 'Прямой',
        'reverse': 'Обратный',
        'template': 'Матрица',
        'value': 'Значение',
        'target_unit': 'Целевая единица',
        'result_folder': 'Папка результата',
        'upload_sequence': 'Файл последовательности (.gb, .dna, .fa)',
        'upload_layout': 'Раскладка wellmap (.toml)',
        'analyse': 'Анализ',
        'analyse_pair': 'Анализ пары',
        'transform': 'Преобразовать',
        'convert': 'Перевести',
        'fold': 'Сложить',
        'simulate': 'Симулировать',
        'export_xlsx': 'Экспорт XLSX',
        'no_results': 'Результатов пока нет.',
        'uploaded': 'Загружено',
        'failed': 'Ошибка запуска',
        'done': 'Готово',
        'length': 'длина',
        'gc': 'GC',
        'tm': 'Tm',
        'hairpin': 'шпилька',
        'dimer': 'димер',
        'hetero': 'гетеродимер',
        'end3': "3' конец",
        'complement': 'комплемент',
        'reverse_seq': 'реверс',
        'revcomp': 'обратный комплемент',
        'product': 'продукт',
        'wells': 'лунок',
        'conditions': 'условия',
        'name': 'название',
        'format': 'формат',
        'topology': 'топология',
        'records': 'записей',
        'features': 'признаков',
        'dg': 'dG',
        'fold_label': 'складка',
        'error': 'Ошибка',
    },
}


def tr(key):
    return TEXTS[LANG['code']].get(key, key)


def change_language(code):
    LANG['code'] = code if code in TEXTS else 'en'
    ui.navigate.reload()


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

    def shell(title, active):
        with ui.left_drawer(value=True, bordered=True).classes('bg-grey-2') as drawer:
            ui.label('AVATAR COMBINER').classes('text-sm font-bold mt-2')
            ui.link(tr('pipeline'), '/').classes('text-black no-underline')
            ui.link(tr('results'), '/results').classes('text-black no-underline')
            ui.separator()
            ui.label(tr('genetics_tools')).classes('text-xs opacity-60')
            for key, label_key in TOOLS:
                classes = 'text-black no-underline'
                if active == key:
                    classes += ' font-bold'
                ui.link(tr(label_key), f'/tools?tool={key}').classes(classes)
            ui.separator()
            with ui.row().classes('items-center gap-1'):
                ui.label(tr('language')).classes('text-xs opacity-60')
                ui.button(
                    'EN',
                    on_click=lambda: change_language('en'),
                ).props('flat dense')
                ui.button(
                    'RU',
                    on_click=lambda: change_language('ru'),
                ).props('flat dense')

        with ui.header().classes('items-center'):
            ui.button(icon='menu', on_click=lambda: drawer.toggle()).props(
                'flat color=white'
            )
            ui.label(title).classes('text-xl font-bold')

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
            ui.label(f"{tr('result')}: {Path(folder).name}").classes('text-lg font-bold')
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
        shell(tr('pipeline'), 'pipeline')

        if state.error:
            ui.label(state.error).classes('text-red-600')

        workbooks = state.workbooks()
        options = {str(path): path.name for path in workbooks}
        current = str(state.config_path()) if state.config else None
        if current not in options:
            current = None

        with ui.card().classes('w-full'):
            ui.label(tr('workbook')).classes('text-lg font-bold')
            workbook_select = ui.select(
                options,
                value=current,
                label=tr('excel_file'),
            ).classes('w-96')
            upload = ui.upload(
                label=tr('upload_xlsx'),
                auto_upload=True,
                max_file_size=50_000_000,
            )

        with ui.card().classes('w-full'):
            ui.label(tr('sheets')).classes('text-lg font-bold')
            sheet_row = ui.row().classes('w-full')

        range_input = ui.input(
            tr('data_range'),
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
                    ui.select([], label=f"{tr('plate')} {index + 1}").classes('w-56')
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
            ui.notify(f"{tr('uploaded')}: {name}", type='positive')

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
                ui.notify(f"{tr('failed')}: {exc}", type='negative')
            except Exception as exc:
                ui.notify(str(exc), type='negative')
            else:
                state.last_result = result
                render_result(result, result_box)
                ui.notify(f"{tr('done')}: {result.name}", type='positive')
            finally:
                state.running = False
                button.props(remove='loading')

        button = ui.button(tr('run'), on_click=run_now).props('color=primary')
        load_sheets()

    @ui.page('/results')
    def results_page():
        ui.page_title(tr('results'))
        shell(tr('results'), 'results')

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
            ui.label(tr('no_results'))
            return

        for folder in folders:
            with ui.card().classes('w-full'):
                render_result(folder, ui.column().classes('w-full'))

    @ui.page('/tools')
    def tools_page():
        ui.page_title('Genetics tools')
        tool_key = context.client.request.query_params.get('tool', 'tm')
        shell(tr('genetics_tools'), tool_key)

        def show(container, text):
            container.clear()
            with container:
                ui.code(str(text)).classes('w-full')

        def safe_show(container, function):
            try:
                show(container, function())
            except Exception as exc:
                show(container, f"{tr('error')}: {exc}")

        with ui.tabs().classes('w-full') as tabs:
            tm_tab = ui.tab(tr('primer_tm'))
            pair_tab = ui.tab(tr('primer_pair'))
            dna_tab = ui.tab(tr('dna'))
            units_tab = ui.tab(tr('units'))
            structure_tab = ui.tab(tr('structure'))
            pcr_tab = ui.tab(tr('pcr'))
            files_tab = ui.tab(tr('files'))

        tab_map = {
            'tm': tm_tab,
            'pair': pair_tab,
            'dna': dna_tab,
            'units': units_tab,
            'structure': structure_tab,
            'pcr': pcr_tab,
            'import': files_tab,
            'layout': files_tab,
            'xlsx': files_tab,
        }

        ui.label(tr('all_tools')).classes('text-lg font-bold mt-2')
        with ui.row().classes('flex-wrap gap-1'):
            index = (
                ('primer_tm', tm_tab),
                ('primer_pair', pair_tab),
                ('dna', dna_tab),
                ('units', units_tab),
                ('structure', structure_tab),
                ('pcr', pcr_tab),
                ('import_seq', files_tab),
                ('plate_layout', files_tab),
                ('xlsx_export', files_tab),
            )
            for label_key, tab in index:
                ui.button(
                    tr(label_key),
                    on_click=lambda tab=tab: tabs.set_value(tab),
                ).props('flat dense')

        with ui.tab_panels(tabs, value=tab_map.get(tool_key, tm_tab)).classes('w-full'):
            with ui.tab_panel(tm_tab):
                sequence = ui.input(tr('sequence'))
                out = ui.column()
                ui.button(
                    tr('analyse'),
                    on_click=lambda: safe_show(
                        out, lambda: _primer_report(genetics.analyze_primer(sequence.value))
                    ),
                )

            with ui.tab_panel(pair_tab):
                forward = ui.input(tr('forward'))
                reverse = ui.input(tr('reverse'))
                out = ui.column()
                ui.button(
                    tr('analyse_pair'),
                    on_click=lambda: safe_show(
                        out,
                        lambda: _pair_report(
                            genetics.analyze_pair(forward.value, reverse.value)
                        ),
                    ),
                )

            with ui.tab_panel(dna_tab):
                sequence = ui.input(tr('sequence'))
                out = ui.column()
                ui.button(
                    tr('transform'),
                    on_click=lambda: safe_show(out, lambda: _dna_report(sequence.value)),
                )

            with ui.tab_panel(units_tab):
                quantity = ui.input(tr('value'), placeholder='25 uM')
                target = ui.input(tr('target_unit'), placeholder='nM')
                out = ui.column()
                ui.button(
                    tr('convert'),
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
                sequence = ui.input(tr('sequence'))
                out = ui.column()
                ui.button(
                    tr('fold'),
                    on_click=lambda: safe_show(
                        out,
                        lambda: _structure_report(
                            seq_structure.analyze_structure(sequence.value)
                        ),
                    ),
                )

            with ui.tab_panel(pcr_tab):
                template = ui.textarea(tr('template'))
                forward = ui.input(tr('forward'))
                reverse = ui.input(tr('reverse'))
                out = ui.column()
                ui.button(
                    tr('simulate'),
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

                ui.label(tr('upload_sequence'))
                ui.upload(on_upload=on_sequence, auto_upload=True)
                ui.label(tr('upload_layout'))
                ui.upload(on_upload=on_layout, auto_upload=True)

                result_dirs = sorted(
                    path.name
                    for path in state.base_dir.iterdir()
                    if path.is_dir()
                    and run_pipeline.RESULT_DIR_PATTERN.match(path.name)
                )
                folder = ui.select(result_dirs, label=tr('result_folder'))
                ui.button(
                    tr('export_xlsx'),
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
            f"{tr('sequence')} {report.sequence}",
            f"{tr('length')}   {report.length} nt",
            f"{tr('gc')}       {report.gc:.1f}%",
            f"{tr('tm')}       {report.tm:.1f} C",
            f"{tr('hairpin')}  {_thermo(report.hairpin)}",
            f"{tr('dimer')}    {_thermo(report.homodimer)}",
        ]
    )


def _pair_report(report):
    return '\n'.join(
        [
            f"{tr('forward')}  {report.forward.sequence}  Tm {report.forward.tm:.1f} C",
            f"{tr('reverse')}  {report.reverse.sequence}  Tm {report.reverse.tm:.1f} C",
            f"dT       {abs(report.forward.tm - report.reverse.tm):.1f} C",
            f"{tr('hetero')}   {_thermo(report.heterodimer)}",
            f"{tr('end3')}   {_thermo(report.end_stability)}",
        ]
    )


def _dna_report(sequence):
    sequence = genetics.normalize_dna(sequence)
    return '\n'.join(
        [
            f"{tr('length')}     {len(sequence)} nt",
            f"{tr('gc')}         {genetics.gc_content(sequence):.1f}%",
            f"{tr('complement')} {genetics.complement(sequence)}",
            f"{tr('reverse_seq')}    {genetics.reverse(sequence)}",
            f"{tr('revcomp')}    {genetics.reverse_complement(sequence)}",
        ]
    )


def _structure_report(report):
    dg = 'n/a' if report.dg is None else f'{report.dg:.2f} kcal/mol'
    tm = 'n/a' if report.tm is None else f'{report.tm:.1f} C'
    return '\n'.join(
        [
            f"{tr('sequence')} {report.sequence}",
            f"{tr('dg')}       {dg}",
            f"{tr('tm')}       {tm}",
            f"{tr('fold_label')}     {report.dot_bracket}",
        ]
    )


def _pcr_report(report):
    return '\n'.join(
        [
            f"{tr('product')}  {report.length} nt",
            f"{tr('sequence')} {report.sequence}",
        ]
    )


def _sequence_report(record):
    return '\n'.join(
        [
            f"{tr('name')}      {record.name}",
            f"{tr('format')}    {record.source_format}",
            f"{tr('length')}    {len(record.sequence)} nt",
            f"{tr('topology')}  {record.topology}",
            f"{tr('records')}   {record.record_count}",
            f"{tr('features')}  {len(record.features)}",
        ]
    )


def _layout_report(report):
    return '\n'.join(
        [
            f"{tr('wells')}       {report.wells}",
            f"{tr('conditions')}  {', '.join(report.conditions) or 'none'}",
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
