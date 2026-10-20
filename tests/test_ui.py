import json

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
