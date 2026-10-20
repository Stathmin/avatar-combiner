"""Local web interface for the plate combiner.

Run with ``run_pipeline.py --web``. NiceGUI serves a single-user app on
127.0.0.1; no data leaves the machine. The command line stays available.
"""

from __future__ import annotations

import asyncio
import json
import secrets
import tempfile
import time
from pathlib import Path

from nicegui import app, context, ui

import app_config
import pcr_tools
import plate_layout
import report_xlsx
import run_pipeline
import seq_import
import seq_structure
import tool_reports
import tools as genetics
from i18n import TEXT

TOOLS = (
    ('tm', 'tool_tm'),
    ('pair', 'tool_pair'),
    ('dna', 'tool_dna'),
    ('units', 'tool_units'),
    ('structure', 'tool_structure'),
    ('pcr', 'tool_pcr'),
    ('import', 'tool_import'),
    ('layout', 'tool_layout'),
    ('xlsx', 'tool_xlsx'),
)



THEME_CSS = """
:root {
  --paper: #f6efe3;
  --paper-2: #fffaf2;
  --ink: #2b2019;
  --muted: #77685a;
  --line: #e3d3bf;
  --rust: #a64b2a;
  --amber: #d08a2f;
  --olive: #5f6f46;
  --cocoa: #241a13;
}
html { color-scheme: light; }
body {
  background:
    radial-gradient(1100px 600px at 8% -10%, #f2d7b3 0%, transparent 55%),
    radial-gradient(900px 520px at 100% 0%, #ecd0ad 0%, transparent 52%),
    var(--paper);
  color: var(--ink);
  font-family: ui-sans-serif, system-ui, 'Segoe UI', Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
}
body::before {
  content: ''; position: fixed; inset: 0; pointer-events: none; z-index: 0;
  opacity: .5;
  background-image: radial-gradient(rgba(43, 32, 25, .035) 1px, transparent 1px);
  background-size: 3px 3px;
}
.q-layout, .q-page-container, .q-page { background: transparent !important; }
.q-page { max-width: 1120px; margin: 0 auto; padding: 30px 24px 72px; }
.app-header {
  background: rgba(246, 239, 227, .82) !important;
  backdrop-filter: blur(16px) saturate(1.1);
  border-bottom: 1px solid var(--line);
  color: var(--ink) !important;
  box-shadow: none !important;
}
.app-header .q-btn { color: var(--ink) !important; }
.app-drawer {
  background: linear-gradient(180deg, #fdf7ec 0%, #f2e3cf 100%) !important;
  border-right: 1px solid var(--line);
}
.brand {
  font-size: 11px; font-weight: 700; letter-spacing: .22em;
  color: var(--muted); text-transform: uppercase;
}
.nav-link {
  display: block; border-radius: 10px; padding: 7px 10px !important;
  color: var(--ink) !important; text-decoration: none !important;
  transition: background .16s ease, transform .16s ease;
}
.nav-link:hover { background: #efdfc9; transform: translateX(2px); }
.nav-link.nav-active {
  background: linear-gradient(90deg, #f0d9b8, #f7e9d4);
  font-weight: 650; box-shadow: inset 3px 0 0 var(--rust);
}
.panel {
  background: linear-gradient(180deg, rgba(255, 251, 244, .97), rgba(255, 247, 236, .92)) !important;
  border: 1px solid var(--line) !important;
  border-radius: 18px !important;
  box-shadow: 0 20px 46px -28px rgba(82, 48, 22, .45) !important;
  padding: 18px 20px;
  transition: transform .18s ease, box-shadow .18s ease;
}
.panel:hover { transform: translateY(-1px); box-shadow: 0 26px 54px -30px rgba(82, 48, 22, .5) !important; }
.hero { gap: 2px; padding: 6px 2px 18px; }
.hero-kicker {
  font-size: 11px; letter-spacing: .26em; text-transform: uppercase;
  color: var(--rust); font-weight: 700;
}
.hero-title {
  font-size: clamp(34px, 5vw, 54px); line-height: 1; letter-spacing: -.035em;
  font-weight: 800;
  background: linear-gradient(100deg, var(--rust), var(--amber) 60%, var(--olive));
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.hero-sub { color: var(--muted); max-width: 62ch; font-size: 14px; }
.badge {
  display: inline-flex; align-items: center; gap: 6px;
  border: 1px solid var(--line); border-radius: 999px;
  padding: 3px 10px; font-size: 11px; color: var(--muted);
  background: rgba(255, 250, 242, .7);
}
.q-card { border-radius: 18px; }
.q-card .text-lg { letter-spacing: -.01em; }
.q-btn { text-transform: none !important; border-radius: 11px !important; letter-spacing: .01em; }
.q-btn--flat { border-radius: 9px !important; }
.q-field--outlined .q-field__control {
  background: var(--paper-2); border-radius: 12px;
}
.q-field--outlined .q-field__control:before { border-color: var(--line); }
.q-field--outlined.q-field--focused .q-field__control:after { border-color: var(--rust); }
.q-field__label { color: var(--muted) !important; }
.q-tab { text-transform: none !important; letter-spacing: .01em; }
.q-tab--active { color: var(--rust) !important; }
.q-tab__indicator { background: linear-gradient(90deg, var(--rust), var(--amber)) !important; }
.log-panel {
  background: var(--cocoa) !important; color: #f3e2c8 !important;
  border-radius: 14px !important; border: 1px solid #3a2a20;
  padding: 12px 14px !important; font-size: 12px;
}
.tool-index { gap: 6px; }
.tool-index .q-btn {
  border: 1px solid var(--line); background: rgba(255, 250, 242, .75);
  color: var(--ink) !important;
}
.tool-index .q-btn:hover { border-color: var(--amber); background: #f7e7cf; }
.footer-note { color: var(--muted); font-size: 12px; }
.q-notification { border-radius: 12px !important; }
::selection { background: #f0c98f; color: var(--cocoa); }
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb { background: #d8c3a6; border-radius: 999px; }
::-webkit-scrollbar-track { background: transparent; }
@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; animation: none !important; }
}
"""
def current_lang():
    try:
        return app.storage.user.get('lang', 'en')
    except Exception:
        return 'en'


def tr(key):
    return TEXT[current_lang()].get(key, key)


def change_language(code):
    app.storage.user['lang'] = code if code in TEXT else 'en'
    ui.navigate.reload()


class State:
    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        self._default_config, self._default_error, _source = app_config.load_config(
            self.base_dir
        )
        self.running = False
        self.uploads = self.base_dir / '.uploads'
        self.uploads.mkdir(exist_ok=True)
        self._prune_uploads()

    @property
    def config(self):
        try:
            stored = app.storage.user.get('config')
        except Exception:
            stored = None
        return stored if stored is not None else self._default_config

    @config.setter
    def config(self, value):
        app.storage.user['config'] = value

    @property
    def error(self):
        try:
            if 'config_error' in app.storage.user:
                return app.storage.user['config_error']
        except Exception:
            pass
        return self._default_error

    @error.setter
    def error(self, value):
        app.storage.user['config_error'] = value

    def _prune_uploads(self):
        cutoff = time.time() - 7 * 24 * 3600
        for path in self.uploads.glob('*'):
            try:
                if path.is_file() and path.stat().st_mtime < cutoff:
                    path.unlink()
            except OSError:
                pass

    def workbooks(self):
        found = app_config.discover_excel(self.base_dir)
        return found + sorted(self.uploads.glob('*.xlsx'))

    def sheets(self):
        if not self.config:
            return []
        try:
            path = self.config_path()
            return app_config.sheet_names(path)
        except (app_config.ConfigError, OSError, ValueError):
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
        app_config.validate_config(config, self.base_dir)
        self.config = config
        self.error = None
        return config


def build_app(base_dir):
    state = State(base_dir)

    def shell(title, active):
        ui.colors(
            primary='#a64b2a',
            secondary='#5f6f46',
            accent='#d08a2f',
            positive='#5f6f46',
            negative='#a64b2a',
            warning='#d08a2f',
            info='#6d7f8a',
        )
        ui.add_head_html(f'<style>{THEME_CSS}</style>', shared=True)

        with ui.left_drawer(value=True, bordered=True).classes('app-drawer') as drawer:
            ui.label('AVATAR COMBINER').classes('brand mt-2')
            ui.link(tr('pipeline'), '/').classes(
                'nav-link' + (' nav-active' if active == 'pipeline' else '')
            )
            ui.link(tr('results'), '/results').classes(
                'nav-link' + (' nav-active' if active == 'results' else '')
            )
            ui.separator()
            ui.label(tr('genetics_tools')).classes('text-xs opacity-60')
            for key, label_key in TOOLS:
                classes = 'nav-link'
                if active == key:
                    classes += ' nav-active'
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

        with ui.header().classes('app-header items-center'):
            ui.button(icon='menu', on_click=lambda: drawer.toggle()).props(
                'flat color=white'
            )
            ui.label(title).classes('text-xl font-bold')
            ui.space()
            ui.label('autumn 2026 · local').classes('badge')

    def drain_logs(element, lines):
        while lines:
            element.push(lines.pop(0))

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
        with ui.column().classes('hero'):
            ui.label(tr('hero_kicker')).classes('hero-kicker')
            ui.label('4 × 96  →  1 × 384').classes('hero-title')
            ui.label(tr('hero_sub')).classes('hero-sub')

        if state.error:
            ui.label(state.error).classes('text-red-600')

        workbooks = state.workbooks()
        options = {str(path): path.name for path in workbooks}
        current = str(state.config_path()) if state.config else None
        if current not in options:
            current = None
        selected = {'path': current}

        with ui.card().classes('w-full panel'):
            ui.label(tr('workbook')).classes('text-lg font-bold')
            workbook_select = ui.select(
                options,
                value=current,
                label=tr('excel_file'),
            ).classes('w-96').mark('workbook')
            upload = ui.upload(
                label=tr('upload_xlsx'),
                auto_upload=True,
                max_file_size=50_000_000,
            ).props('accept=".xlsx,.xlsm"')
            workbook_info = ui.label('').classes('text-xs opacity-70').mark('workbook_info')

        with ui.card().classes('w-full panel'):
            ui.label(tr('sheets')).classes('text-lg font-bold')
            sheet_row = ui.row().classes('w-full')
            sheet_status = ui.label('').classes('text-sm mt-1').mark('selection_status')

        range_input = ui.input(
            tr('data_range'),
            value='B3:M10',
        ).classes('w-60').mark('range')

        log = ui.log(max_lines=1000).classes('w-full h-64 font-mono text-xs log-panel')
        log_lines = []
        result_box = ui.column().classes('w-full')
        ui.timer(0.3, lambda: drain_logs(log, log_lines))

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
                    ui.select([], label=f"{tr('plate')} {index + 1}")
                    .classes('w-56')
                    .mark(f'sheet_{index + 1}')
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

        def refresh_validation():
            path = selected.get('path')
            if not path:
                sheet_status.text = ''
                workbook_info.text = ''
                button.enabled = False
                return
            try:
                sheets = [value for value in current_sheets() if value]
                state.apply(path, sheets, range_input.value)
            except (app_config.ConfigError, OSError, ValueError) as exc:
                sheet_status.text = str(exc)
                sheet_status.style('color: #b91c1c')
                workbook_info.text = ''
                button.enabled = False
                return
            sheet_status.text = tr('selection_ready')
            sheet_status.style('color: #4d7c0f')
            try:
                workbook_info.text = app_config.workbook_summary(path, state.config)
            except Exception:
                workbook_info.text = ''
            button.enabled = True

        def on_workbook(event):
            if not event.value:
                return
            selected['path'] = event.value
            try:
                state.apply(event.value, None, range_input.value)
            except (app_config.ConfigError, OSError, ValueError) as exc:
                ui.notify(str(exc), type='negative')
                return
            load_sheets()
            refresh_validation()

        workbook_select.on_value_change(on_workbook)

        async def on_upload(event):
            name = Path(event.file.name).name
            if Path(name).suffix.lower() not in ('.xlsx', '.xlsm'):
                ui.notify('select an .xlsx or .xlsm file', type='negative')
                return
            target = state.uploads / name
            target.write_bytes(await event.file.read())
            try:
                config = app_config.build_config(
                    state.base_dir, excel_file=target
                )
                app_config.validate_config(config, state.base_dir)
            except (app_config.ConfigError, OSError, ValueError) as exc:
                ui.notify(f'File rejected: {exc}', type='negative')
                target.unlink(missing_ok=True)
                return
            state.config = config
            state.error = None
            selected['path'] = str(target)
            workbook_select.options = {
                str(path): path.name for path in state.workbooks()
            }
            workbook_select.value = str(target)
            workbook_select.update()
            load_sheets()
            refresh_validation()
            ui.notify(
                f"{tr('uploaded')}: {name} · "
                f"{app_config.workbook_summary(target, state.config)}",
                type='positive',
            )

        upload.on_upload(on_upload)

        async def run_now():
            if state.running:
                ui.notify('a run is already in progress', type='warning')
                return
            try:
                excel = selected.get('path')
                if not excel:
                    raise app_config.ConfigError('select a workbook first')
                sheets = [value for value in current_sheets() if value]
                config = state.apply(excel, sheets, range_input.value)
            except (app_config.ConfigError, OSError, ValueError) as exc:
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
                    log=lambda message: log_lines.append(str(message)),
                    config=config,
                )
            except (run_pipeline.PipelineError, OSError) as exc:
                ui.notify(f"{tr('failed')}: {exc}", type='negative')
            else:
                render_result(result, result_box)
                ui.notify(f"{tr('done')}: {result.name}", type='positive')
            finally:
                state.running = False
                button.props(remove='loading')

        button = ui.button(tr('run'), on_click=run_now).props('color=primary size=lg')
        for select in sheet_selects:
            select.on_value_change(lambda event: refresh_validation())
        range_input.on_value_change(lambda event: refresh_validation())
        load_sheets()
        refresh_validation()

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
            with ui.card().classes('w-full panel'):
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
            except (genetics.ToolError, app_config.ConfigError, OSError, ValueError, ImportError) as exc:
                show(container, f"{tr('error')}: {exc}")

        with ui.tabs().classes('w-full') as tabs:
            tm_tab = ui.tab(tr('tool_tm'))
            pair_tab = ui.tab(tr('tool_pair'))
            dna_tab = ui.tab(tr('tool_dna'))
            units_tab = ui.tab(tr('tool_units'))
            structure_tab = ui.tab(tr('tool_structure'))
            pcr_tab = ui.tab(tr('tool_pcr'))
            files_tab = ui.tab(tr('files_tab'))

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
        with ui.row().classes('flex-wrap tool-index'):
            index = (
                ('tool_tm', tm_tab),
                ('tool_pair', pair_tab),
                ('tool_dna', dna_tab),
                ('tool_units', units_tab),
                ('tool_structure', structure_tab),
                ('tool_pcr', pcr_tab),
                ('tool_import', files_tab),
                ('tool_layout', files_tab),
                ('tool_xlsx', files_tab),
            )
            for label_key, tab in index:
                ui.button(
                    tr(label_key),
                    on_click=lambda tab=tab: tabs.set_value(tab),
                ).props('flat dense')

        with ui.tab_panels(tabs, value=tab_map.get(tool_key, tm_tab)).classes('w-full'):
            with ui.tab_panel(tm_tab):
                tm_sequence = ui.input(tr('sequence')).mark('tm_sequence')
                tm_out = ui.column()
                ui.button(
                    tr('analyse'),
                    on_click=lambda: safe_show(
                        tm_out,
                        lambda: _primer_report(
                            genetics.analyze_primer(tm_sequence.value)
                        ),
                    ),
                ).mark('tm_button')

            with ui.tab_panel(pair_tab):
                pair_forward = ui.input(tr('forward'))
                pair_reverse = ui.input(tr('reverse_primer'))
                pair_out = ui.column()
                ui.button(
                    tr('analyse_pair'),
                    on_click=lambda: safe_show(
                        pair_out,
                        lambda: _pair_report(
                            genetics.analyze_pair(
                                pair_forward.value, pair_reverse.value
                            )
                        ),
                    ),
                )

            with ui.tab_panel(dna_tab):
                dna_sequence = ui.input(tr('sequence'))
                dna_out = ui.column()
                ui.button(
                    tr('transform'),
                    on_click=lambda: safe_show(
                        dna_out, lambda: _dna_report(dna_sequence.value)
                    ),
                )

            with ui.tab_panel(units_tab):
                unit_quantity = ui.input(tr('value'), placeholder='25 uM').mark('unit_value')
                unit_target = ui.input(tr('target_unit'), placeholder='nM').mark('unit_target')
                unit_out = ui.column()
                ui.button(
                    tr('convert'),
                    on_click=lambda: safe_show(
                        unit_out,
                        lambda: '\n'.join(
                            f'{amount} {unit}'
                            for unit, amount in tool_reports.unit_rows(
                                unit_quantity.value, unit_target.value
                            )
                        ),
                    ),
                ).mark('unit_button')

            with ui.tab_panel(structure_tab):
                structure_sequence = ui.input(tr('sequence'))
                structure_out = ui.column()
                ui.button(
                    tr('fold'),
                    on_click=lambda: safe_show(
                        structure_out,
                        lambda: _structure_report(
                            seq_structure.analyze_structure(
                                structure_sequence.value
                            )
                        ),
                    ),
                )

            with ui.tab_panel(pcr_tab):
                pcr_template = ui.textarea(tr('template'))
                pcr_forward = ui.input(tr('forward'))
                pcr_reverse = ui.input(tr('reverse_primer'))
                pcr_out = ui.column()
                ui.button(
                    tr('simulate'),
                    on_click=lambda: safe_show(
                        pcr_out,
                        lambda: _pcr_report(
                            pcr_tools.simulate_pcr(
                                pcr_template.value,
                                pcr_forward.value,
                                pcr_reverse.value,
                            )
                        ),
                    ),
                )

            with ui.tab_panel(files_tab):
                files_out = ui.column()

                async def on_sequence(event):
                    suffix = Path(event.file.name).suffix.lower()
                    target = Path(tempfile.mkdtemp()) / f'input{suffix}'
                    target.write_bytes(await event.file.read())
                    safe_show(
                        files_out,
                        lambda: _sequence_report(seq_import.load_sequence(target)),
                    )

                async def on_layout(event):
                    target = Path(tempfile.mkdtemp()) / 'plate.toml'
                    target.write_bytes(await event.file.read())
                    safe_show(
                        files_out,
                        lambda: _layout_report(plate_layout.load_layout(target)),
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
                        files_out,
                        lambda: str(
                            report_xlsx.export_workbook(
                                state.base_dir / folder.value
                            )
                        ),
                    ),
                )

    return state


def render_rows(rows):
    return '\n'.join(
        f"{tr(key)}  {tr('none') if value is None else value}"
        for key, value in rows
    )


def _primer_report(report):
    return render_rows(tool_reports.primer_rows(report))


def _pair_report(report):
    return render_rows(tool_reports.pair_rows(report))


def _dna_report(sequence):
    return render_rows(tool_reports.dna_rows(sequence))


def _structure_report(report):
    return render_rows(tool_reports.structure_rows(report))


def _pcr_report(report):
    return render_rows(tool_reports.pcr_rows(report))


def _sequence_report(record):
    return render_rows(tool_reports.sequence_rows(record))


def _layout_report(report):
    return render_rows(tool_reports.layout_rows(report))


def main(base_dir=None, port=8080, show=True):
    build_app(base_dir or run_pipeline.application_dir())
    ui.run(
        host='127.0.0.1',
        port=port,
        title='Avatar Combiner',
        favicon='◈',
        reload=False,
        show=show,
        dark=False,
        storage_secret=secrets.token_hex(16),
    )
