import json
from pathlib import Path

import pcr_tools
import ui


def make_app(tmp_path, lang='en'):
    app = ui.App(lang=lang)
    app.base_dir = tmp_path
    app.result_entries = app._load_results()
    app.result_index = max(0, len(app.result_entries) - 1)
    return app


def write_config(tmp_path):
    config = {
        'excel_file': 'plates.xlsx',
        'sheets': {
            'plate1': {'sheet_name': 'p1'},
            'plate2': {'sheet_name': 'p2'},
            'plate3': {'sheet_name': 'p3'},
            'plate4': {'sheet_name': 'p4'},
        },
        'data_range': {
            'start_row': 3,
            'end_row': 10,
            'start_col': 2,
            'end_col': 13,
        },
        'row_labels_col': 1,
        'column_labels_row': 2,
        'metadata_row': 1,
    }
    (tmp_path / 'config.json').write_text(
        json.dumps(config, ensure_ascii=False),
        encoding='utf-8',
    )


def plain(lines):
    return '\n'.join(ui.ANSI_RE.sub('', line) for line in lines)


def test_home_shows_hotkeys_and_next_folder(tmp_path):
    write_config(tmp_path)
    (tmp_path / 'Результат 1').mkdir()
    app = make_app(tmp_path)

    text = plain(app.render_home(100, 30))

    assert '[R]' in text
    assert '[T]' in text
    assert '[L]' in text
    assert 'Результат 2' in text
    assert 'READY' in text


def test_help_is_bilingual_on_wide_screen(tmp_path):
    app = make_app(tmp_path)

    text = plain(app.render_help(110, 40))

    assert 'ENGLISH' in text
    assert 'РУССКИЙ' in text
    assert 'Quick keys' in text
    assert 'Быстрые клавиши' in text


def test_language_toggle_and_navigation(tmp_path):
    app = make_app(tmp_path, lang='en')

    app.handle_key('l')
    assert app.lang == 'ru'

    app.handle_key('5')
    assert app.screen == 'help'

    app.handle_key('b')
    assert app.screen == 'home'

    app.handle_key('c')
    assert app.screen == 'config'


def test_unit_labels_preserve_case(tmp_path):
    app = make_app(tmp_path, lang='en')

    assert 'nM' in plain([app.tool_line('nM', '25000', upper=False)])
    assert 'NM' in plain([app.tool_line('nM', '25000')])


def test_tools_screen_and_navigation(tmp_path):
    app = make_app(tmp_path, lang='en')

    app.handle_key('t')
    assert app.screen == 'tools'

    text = plain(app.render_tools(100, 30))
    assert '[1]' in text
    assert '[4]' in text

    app.handle_key('b')
    assert app.screen == 'home'


def test_tools_hub_lists_all_groups(tmp_path):
    app = make_app(tmp_path, lang='en')

    text = plain(app.render_tools(100, 30))

    assert 'INSPECT' in text
    assert 'STRUCTURE' in text
    assert 'FILES' in text
    for key in ('[5]', '[6]', '[7]', '[8]', '[9]'):
        assert key in text


def test_tools_hub_dispatches_new_keys(tmp_path, monkeypatch):
    app = make_app(tmp_path, lang='en')
    calls = []
    for name in ('tool_structure', 'tool_import', 'tool_layout', 'tool_pcr', 'tool_xlsx'):
        monkeypatch.setattr(app, name, lambda name=name: calls.append(name))

    for key in '56789':
        app.handle_tools_key(key)

    assert calls == [
        'tool_structure',
        'tool_import',
        'tool_layout',
        'tool_pcr',
        'tool_xlsx',
    ]


def test_structure_tool_renders_report(tmp_path, monkeypatch):
    app = make_app(tmp_path, lang='en')
    monkeypatch.setattr(app, 'prompt_text', lambda *args, **kwargs: 'ACGTACGTACGT')

    app.tool_structure()
    text = plain(app.tool_output)

    assert 'kcal/mol' in text
    assert '((((....))))' in text
    assert '12 nt' in text


def test_layout_tool_renders_wells(tmp_path, monkeypatch):
    app = make_app(tmp_path, lang='en')
    path = tmp_path / 'plate.toml'
    path.write_text('[well.A1]\nsample = "soy1"\n', encoding='utf-8')
    monkeypatch.setattr(app, 'prompt_text', lambda *args, **kwargs: str(path))

    app.tool_layout()
    text = plain(app.tool_output)

    assert '1' in text
    assert 'sample' in text


def test_pcr_tool_renders_product(tmp_path, monkeypatch):
    app = make_app(tmp_path, lang='en')
    monkeypatch.setattr(app, 'prompt_text', lambda *args, **kwargs: 'ACGT')
    monkeypatch.setattr(
        pcr_tools,
        'simulate_pcr',
        lambda *args: pcr_tools.PcrReport(200, 'ACGT', 'ACGT', 'ACGT'),
    )

    app.tool_pcr()
    text = plain(app.tool_output)

    assert '200 nt' in text


def test_pcr_tool_allows_long_template(tmp_path, monkeypatch):
    app = make_app(tmp_path, lang='en')
    calls = []

    def fake_prompt(title, hint=None, max_length=120):
        calls.append({'title': title, 'hint': hint, 'max_length': max_length})
        return 'ACGT'

    monkeypatch.setattr(app, 'prompt_text', fake_prompt)
    monkeypatch.setattr(
        pcr_tools,
        'simulate_pcr',
        lambda *args: pcr_tools.PcrReport(200, 'ACGT', 'ACGT', 'ACGT'),
    )

    app.tool_pcr()

    assert calls[0]['max_length'] >= 10000
    assert calls[0]['hint'] == app.t['pcr_hint']
    assert calls[1]['max_length'] == 120
    assert calls[2]['max_length'] == 120


def test_long_sequences_are_previewed(tmp_path):
    app = make_app(tmp_path, lang='en')

    lines = app.tool_preview_lines('SEQ', 'A' * 1000)

    assert len(lines) <= 8
    assert '+760 nt' in plain(lines)


def test_sequence_lines_wrap_without_truncation(tmp_path):
    app = make_app(tmp_path, lang='en')

    lines = plain(app.tool_sequence_lines('SEQ', 'A' * 80)).splitlines()

    assert len(lines) == 2
    assert all(len(line) <= 53 for line in lines)


def test_xlsx_tool_writes_workbook(tmp_path, monkeypatch):
    app = make_app(tmp_path, lang='en')
    result_dir = tmp_path / 'Результат 1'
    result_dir.mkdir()
    (result_dir / 'combined_384_plate.csv').write_text('A\n1\n', encoding='utf-8')
    monkeypatch.setattr(app, 'prompt_text', lambda *args, **kwargs: str(result_dir))

    app.tool_xlsx()

    assert (result_dir / 'combined_384_plate.xlsx').is_file()


def test_ui_does_not_import_heavy_modules_at_startup():
    import subprocess
    import sys

    code = (
        'import sys, ui; '
        "print(any(m in sys.modules for m in "
        "['pandas', 'wellmap', 'pydna', 'openpyxl']))"
    )
    output = subprocess.run(
        [sys.executable, '-c', code],
        cwd=Path(__file__).resolve().parents[1] / 'src',
        capture_output=True,
        text=True,
        check=True,
    )
    assert output.stdout.strip() == 'False'


def test_tools_hub_compact_when_height_is_short(tmp_path):
    app = make_app(tmp_path, lang='en')
    app.tool_output = [f'line {index}' for index in range(8)]

    lines = app.render_tools(80, 24)

    assert len(lines) <= 24
    assert 'RESULT' in plain(lines)
