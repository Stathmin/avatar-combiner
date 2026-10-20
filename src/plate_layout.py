"""Validate a microplate layout written in wellmap TOML.

wellmap is imported inside the function so the TUI does not load pandas at
startup. wellmap raises LayoutError for unknown wells and ranges; every failure
is converted to ToolError.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tools import ToolError

STRUCTURAL = frozenset({'well', 'well0', 'row', 'col', 'row_i', 'col_j'})


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
        from wellmap import load as load_wellmap

        frame = load_wellmap(str(path))
    except Exception as exc:
        raise ToolError(f'cannot read {path.name}: {exc}') from exc

    conditions = tuple(
        str(column) for column in frame.columns if column not in STRUCTURAL
    )
    return LayoutReport(wells=len(frame), conditions=conditions)
