"""Oligo secondary-structure analysis backed by seqfold.

Seqfold can return non-finite energies and a malformed dot-bracket for short or
unstructured oligos. This module normalises both before they reach the UI.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import seqfold

from tools import normalize_primer


@dataclass(frozen=True)
class StructureHit:
    energy: float
    description: str


@dataclass(frozen=True)
class StructureReport:
    sequence: str
    dg: Optional[float]
    tm: Optional[float]
    dot_bracket: str
    hits: tuple[StructureHit, ...]


def analyze_structure(sequence):
    """Return dG, Tm, dot-bracket and folding hits for an ACGT oligo."""
    sequence = normalize_primer(sequence)
    folded = seqfold.fold(sequence)
    return StructureReport(
        sequence=sequence,
        dg=_finite(seqfold.dg(sequence)),
        tm=_finite(seqfold.tm(sequence)),
        dot_bracket=_safe_dot(sequence, seqfold.dot_bracket(sequence, folded)),
        hits=tuple(
            StructureHit(energy=float(hit.e), description=str(hit.desc))
            for hit in folded
            if math.isfinite(float(hit.e))
        ),
    )


def _finite(value) -> Optional[float]:
    value = float(value)
    return value if math.isfinite(value) else None


def _safe_dot(sequence, dot):
    if len(dot) != len(sequence):
        return '.' * len(sequence)

    depth = 0
    for char in dot:
        if char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
            if depth < 0:
                return '.' * len(sequence)

    return dot if depth == 0 else '.' * len(sequence)
