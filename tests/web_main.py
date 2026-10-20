"""Main file used by NiceGUI's user-simulation fixture.

It runs inside the fixture's reset context, so pages registered here survive.
``ui.run`` is intercepted by the simulation.
"""

import os
from pathlib import Path

from nicegui import ui

import web_app

web_app.build_app(Path(os.environ['AVATAR_WEB_BASE']))
ui.run(reload=False, show=False)
