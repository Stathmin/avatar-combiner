"""Validate a microplate layout written in wellmap TOML.

wellmap is imported inside the function so the TUI does not load pandas at
startup. wellmap raises LayoutError for unknown wells and ranges; every failure
is converted to ToolError.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tools import ToolError

STRUCTURAL = frozenset(
    {'well', 'well0', 'row', 'col', 'row_i', 'col_j', 'path', 'plate'}
)


@dataclass(frozen=True)
class LayoutReport:
    wells: int
    conditions: tuple[str, ...]


def load_layout(path):
    """Return well count and user conditions for a wellmap TOML file."""
    path = Path(path)
    if not path.is_file():
        raise ToolError(f'file not found: {path}')

    try:
        frame = _load_wellmap()(str(path))
    except Exception as exc:
        raise ToolError(
            f'cannot read {path.name} ({type(exc).__name__}): {exc}'
        ) from exc

    conditions = tuple(
        str(column) for column in frame.columns if column not in STRUCTURAL
    )
    return LayoutReport(wells=len(frame), conditions=conditions)


def _load_wellmap():
    """Return ``wellmap.file.load`` without importing matplotlib.

    wellmap's package ``__init__`` imports ``.plot``, which imports matplotlib
    at module level. The validator only needs ``wellmap.file``, so install a
    stub package and a stub ``wellmap.plot`` (for the ``Style`` import) first.
    This keeps matplotlib and Pillow out of the frozen build.
    """
    import importlib
    import importlib.util
    import sys
    import types

    if 'wellmap' not in sys.modules:
        spec = importlib.util.find_spec('wellmap')
        if spec is None or not spec.submodule_search_locations:
            raise ImportError('wellmap package not found')
        package = types.ModuleType('wellmap')
        package.__path__ = list(spec.submodule_search_locations)
        sys.modules['wellmap'] = package

    if 'wellmap.plot' not in sys.modules:
        plot = types.ModuleType('wellmap.plot')
        plot.Style = dict
        plot.show = lambda *args, **kwargs: None
        plot.show_df = lambda *args, **kwargs: None
        plot.UsageError = ValueError
        sys.modules['wellmap.plot'] = plot

    return importlib.import_module('wellmap.file').load
