"""Run the web UI against an arbitrary base directory (dev/e2e only)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from nicegui import ui  # noqa: E402

import web_app  # noqa: E402

base_dir = Path(sys.argv[1])
port = int(sys.argv[2])

web_app.build_app(base_dir)
ui.run(
    host='127.0.0.1',
    port=port,
    show=False,
    reload=False,
    dark=False,
    storage_secret='dev-e2e-secret',
)
