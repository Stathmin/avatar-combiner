from pathlib import Path

import build_binary


def test_dist_web_bats_are_ascii_and_glob_exe(tmp_path: Path):
    """cmd.exe mis-reads UTF-8 Cyrillic in .bat files; bats must stay ASCII + glob."""
    build_binary._write_dist_web_bats(tmp_path, 'аватар_объединитель_4х_планшетов.exe')
    start = (tmp_path / 'start-web.bat').read_text(encoding='utf-8-sig')
    stop = (tmp_path / 'stop-web.bat').read_text(encoding='utf-8-sig')
    assert start.isascii()
    assert stop.isascii()
    assert '*.exe' in start
    assert 'аватар' not in start
    assert 'аватар' not in stop
    assert '--web' in start
