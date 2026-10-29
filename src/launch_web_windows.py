#!/usr/bin/env python3
"""Windows-friendly launcher for the local web UI.

Picks a free port (default 8080), writes PID/port files under %%TEMP%%,
opens the default browser, then runs the NiceGUI server in-process.
Used by start-web.bat so lab users can double-click without remembering flags.
"""

from __future__ import annotations

import atexit
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

PID_FILE = Path(os.environ.get('TEMP', '.')) / 'avatar-combiner-web.pid'
PORT_FILE = Path(os.environ.get('TEMP', '.')) / 'avatar-combiner-web.port'
DEFAULT_PORT = 8080


def application_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def pick_port(preferred: int = DEFAULT_PORT) -> int:
    """Return the first free localhost port at or above ``preferred``.

    Do not set SO_REUSEADDR while probing: on Windows it can make a busy
    LISTEN port look free, so start-web would collide instead of stepping up.
    """
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(('127.0.0.1', port))
            except OSError:
                continue
            return port
    return preferred


def write_runtime(port: int) -> None:
    PID_FILE.write_text(str(os.getpid()), encoding='ascii')
    PORT_FILE.write_text(str(port), encoding='ascii')


def clear_runtime() -> None:
    for path in (PID_FILE, PORT_FILE):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def open_browser_when_ready(url: str, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(('127.0.0.1', int(url.rsplit(':', 1)[-1])), 0.4):
                webbrowser.open(url)
                return
        except OSError:
            time.sleep(0.35)
    webbrowser.open(url)


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    preferred = DEFAULT_PORT
    show_browser = True
    for index, arg in enumerate(argv):
        if arg == '--port' and index + 1 < len(argv):
            preferred = int(argv[index + 1])
        if arg == '--no-browser':
            show_browser = False

    port = pick_port(preferred)
    url = f'http://127.0.0.1:{port}'
    write_runtime(port)
    atexit.register(clear_runtime)

    print('=' * 60)
    print('Avatar Combiner — web UI')
    print('=' * 60)
    print(f'Open:  {url}')
    print('Stop:  Ctrl+C, close this window, or run stop-web.bat')
    if port != preferred:
        print(f'Note:  port {preferred} was busy; using {port}')
    print('=' * 60)
    print(flush=True)

    if show_browser:
        threading.Thread(
            target=open_browser_when_ready,
            args=(url,),
            daemon=True,
        ).start()

    # Ensure src/ is importable when launched as a script.
    root = application_dir()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    import web_app

    web_app.main(base_dir=root, port=port, show=False)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
