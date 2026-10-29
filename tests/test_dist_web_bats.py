from pathlib import Path

import build_binary


def test_dist_web_bats_are_ascii_and_glob_exe(tmp_path: Path):
    """cmd.exe mis-reads non-ASCII/UTF-16 .bat files; bats must stay ASCII + glob.

    UTF-16 is especially bad: ``REM`` is seen as command ``R``, which launches
    R.exe when R is on PATH.
    """
    build_binary._write_dist_web_bats(tmp_path, 'аватар_объединитель_4х_планшетов.exe')
    start_bytes = (tmp_path / 'start-web.bat').read_bytes()
    stop_bytes = (tmp_path / 'stop-web.bat').read_bytes()
    assert not start_bytes.startswith(b'\xff\xfe')  # UTF-16 LE
    assert not start_bytes.startswith(b'\xef\xbb\xbf')  # UTF-8 BOM
    assert start_bytes.startswith(b'@echo off')
    start = start_bytes.decode('ascii')
    stop = stop_bytes.decode('ascii')
    assert start.isascii()
    assert stop.isascii()
    assert '*.exe' in start
    assert 'аватар' not in start
    assert 'аватар' not in stop
    assert '--web' in start
