"""Genetics helpers used by the Tools screen.

Domain logic comes from established libraries:

- Primer Tm / hairpin / dimers: Primer3 via ``primer3-py``.
- Complement / reverse complement / IUPAC handling: Biopython ``Bio.Seq``.
- Unit conversion: Pint with two small genetics unit definitions.

The PyInstaller bundle keeps Biopython intact, because ``pydna`` needs
``Bio.SeqIO``, ``Bio.SeqRecord`` and ``Bio.Restriction``, and includes
``seqfold``, ``pydna``, ``wellmap``, ``pandas``, ``openpyxl`` and ``matplotlib``
(imported eagerly by ``wellmap``). Only tests and optional modules are excluded.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pint
import primer3
from Bio.Data.IUPACData import ambiguous_dna_letters, unambiguous_dna_letters
from Bio.Seq import Seq


class ToolError(ValueError):
    """Raised for invalid user input or unsupported conversions."""


# ---------------------------------------------------------------------------
# DNA sequence tools
# ---------------------------------------------------------------------------


def normalize_dna(sequence):
    """Uppercase and strip whitespace; reject non-IUPAC characters."""
    sequence = re.sub(r'\s+', '', str(sequence)).upper()
    if not sequence:
        raise ToolError('sequence is empty')

    invalid = sorted(set(sequence) - set(ambiguous_dna_letters))
    if invalid:
        raise ToolError(f'unsupported base(s): {", ".join(invalid)}')
    return sequence


def normalize_primer(sequence):
    """Normalize a primer and require unambiguous A/C/G/T bases."""
    sequence = normalize_dna(sequence)
    invalid = sorted(set(sequence) - set(unambiguous_dna_letters))
    if invalid:
        raise ToolError('primer must contain only A, C, G and T')
    return sequence


def complement(sequence):
    """Return the complement without reversing the sequence."""
    return str(Seq(normalize_dna(sequence)).complement())


def reverse_complement(sequence):
    """Return the reverse complement."""
    return str(Seq(normalize_dna(sequence)).reverse_complement())


def reverse(sequence):
    """Return the sequence reversed, without complementing it."""
    return str(Seq(normalize_dna(sequence)))[::-1]


def gc_content(sequence):
    """Return GC content as a percentage."""
    sequence = normalize_dna(sequence)
    return 100.0 * (sequence.count('G') + sequence.count('C')) / len(sequence)


# ---------------------------------------------------------------------------
# Primer thermodynamics
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PrimerReport:
    sequence: str
    length: int
    gc: float
    tm: float
    hairpin: object
    homodimer: object


@dataclass(frozen=True)
class PrimerPairReport:
    forward: PrimerReport
    reverse: PrimerReport
    heterodimer: object
    end_stability: object


def analyze_primer(sequence):
    """Return Tm, GC, hairpin and homodimer data for one primer."""
    sequence = normalize_primer(sequence)
    return PrimerReport(
        sequence=sequence,
        length=len(sequence),
        gc=gc_content(sequence),
        tm=primer3.calc_tm(sequence),
        hairpin=primer3.calc_hairpin(sequence),
        homodimer=primer3.calc_homodimer(sequence),
    )


def analyze_pair(forward, reverse_primer):
    """Return primer metrics and pair-level heterodimer/end stability."""
    forward = normalize_primer(forward)
    reverse_primer = normalize_primer(reverse_primer)
    return PrimerPairReport(
        forward=analyze_primer(forward),
        reverse=analyze_primer(reverse_primer),
        heterodimer=primer3.calc_heterodimer(forward, reverse_primer),
        end_stability=primer3.calc_end_stability(forward, reverse_primer),
    )


def thermo_text(result, label):
    """Format Primer3's ThermoResult compactly."""
    if not getattr(result, 'structure_found', False):
        return f'{label}: none'
    return (
        f'{label}: Tm {result.tm:.1f} °C · '
        f'ΔG {result.dg / 1000.0:.2f} kcal/mol'
    )


# ---------------------------------------------------------------------------
# PCR block gradient (CFX-style rows A–H)
# ---------------------------------------------------------------------------

GRADIENT_ROWS = 'ABCDEFGH'

# Bio-Rad does not publish a closed-form T100/CFX row-temperature formula.
# Approximation: fixed spatial weights shared across gradient spans.
#   T_row = front + (back - front) * w_row
# Weights are the mean of (T - front) / span from six T100 UI screenshots
# (spans 8–12 °C). Not an official Bio-Rad model.
# Residual after 0.1 °C display rounding: 65→55 row B is 64.2 vs UI 64.3.
_GRADIENT_WEIGHTS = (
    1.0,
    0.925,
    0.8,
    0.6102777777777778,
    0.3836111111111111,
    0.1938888888888889,
    0.07055555555555555,
    0.0,
)
_GRADIENT_MAX_SPAN = 24.0  # CFX/T100 documented maximum gradient range (°C)


@dataclass(frozen=True)
class GradientReport:
    back: float
    front: float
    rows: tuple  # ((letter, temp_c), ...) for A–H


def _parse_celsius(value, label):
    text = str(value).strip().replace(',', '.').replace('°', '').rstrip('Cc')
    try:
        return float(text)
    except ValueError as exc:
        raise ToolError(f'{label} must be a temperature in °C') from exc


def block_gradient(back_celsius, front_celsius):
    """Return per-row block temperatures for a T100/CFX-style 96-well gradient.

    Back row is A (hottest); front row is H (coolest). Intermediate rows use
    fixed relative weights fitted to Bio-Rad T100 UI screenshots — an
    approximation, not a proprietary Bio-Rad formula.
    """
    back = _parse_celsius(back_celsius, 'back row')
    front = _parse_celsius(front_celsius, 'front row')

    if front > back:
        raise ToolError(
            'front row must be ≤ back row (CFX: A hottest, H coolest)'
        )

    span = back - front
    if span > _GRADIENT_MAX_SPAN:
        raise ToolError(
            f'gradient span {span:.1f} °C exceeds CFX maximum '
            f'{_GRADIENT_MAX_SPAN:.0f} °C'
        )

    rows = tuple(
        (letter, round(front + span * weight, 1))
        for letter, weight in zip(GRADIENT_ROWS, _GRADIENT_WEIGHTS)
    )
    return GradientReport(back=back, front=front, rows=rows)


# ---------------------------------------------------------------------------
# Unit conversion
# ---------------------------------------------------------------------------

UREG = pint.UnitRegistry()

# Pint already has bp (point) and kb (kilobarn) aliases, so define explicit
# genetics units with their own dimension. This keeps bp/kb conversions correct
# without touching Pint's physical-unit definitions.
for _definition in (
    'base_pair = [base_pair]',
    'bp = 1 * base_pair',
    'kb = 1000 * base_pair',
    'Mb = 1e6 * base_pair',
):
    UREG.define(_definition)

DISPLAY_UNITS = {
    'length': (('bp', 'bp'), ('kb', 'kb'), ('Mb', 'Mb')),
    'mass': (('pg', 'pg'), ('ng', 'ng'), ('ug', 'ug'), ('mg', 'mg'), ('g', 'g')),
    'volume': (('nL', 'nL'), ('uL', 'uL'), ('mL', 'mL'), ('L', 'L')),
    'amount': (
        ('pmol', 'pmol'),
        ('nmol', 'nmol'),
        ('umol', 'umol'),
        ('mmol', 'mmol'),
        ('mol', 'mol'),
    ),
    'concentration': (('nM', 'nM'), ('uM', 'uM'), ('mM', 'mM'), ('M', 'M')),
    'temperature': (('C', 'degC'), ('F', 'degF'), ('K', 'kelvin')),
}

_UNIT_ALIASES = {
    'c': 'degC',
    '°c': 'degC',
    'f': 'degF',
    '°f': 'degF',
    'k': 'kelvin',
}


def dimensions():
    """Return the supported quantity names."""
    return list(DISPLAY_UNITS)


def units_for(dimension):
    """Return display units for one quantity."""
    return [display for display, _ in DISPLAY_UNITS.get(dimension, ())]


def parse_quantity(text):
    """Parse text such as ``25 uM`` into ``(magnitude, unit, dimensionality)``."""
    quantity = _parse_quantity(text)
    return quantity.magnitude, str(quantity.units), quantity.dimensionality


def convert(value, from_unit, to_unit):
    """Convert a value between units of the same dimension."""
    from_unit = _normalize_temperature_unit(from_unit)
    to_unit = _normalize_temperature_unit(to_unit)
    try:
        return UREG.Quantity(value, from_unit).to(to_unit).magnitude
    except (pint.DimensionalityError, pint.UndefinedUnitError) as exc:
        raise ToolError(f'cannot convert {from_unit} to {to_unit}') from exc


def convert_text(text, target_unit=None):
    """Convert a quantity, or list all units when no target is given."""
    quantity = _parse_quantity(text)

    if target_unit and str(target_unit).strip():
        target = _normalize_temperature_unit(target_unit)
        try:
            converted = quantity.to(target)
        except (pint.DimensionalityError, pint.UndefinedUnitError) as exc:
            raise ToolError(f'cannot convert {quantity.units} to {target}') from exc
        return [(_display_unit(target), converted.magnitude)]

    for units in DISPLAY_UNITS.values():
        if quantity.dimensionality == UREG.Unit(units[0][1]).dimensionality:
            return [(display, quantity.to(unit).magnitude) for display, unit in units]

    raise ToolError(f'unsupported unit: {quantity.units}')


def format_number(value):
    """Format a number without trailing zeros."""
    if abs(value) < 1e-15:
        value = 0.0
    return f'{value:.6g}'


def format_conversion(unit, value):
    return f'{format_number(value)} {unit}'


def _parse_quantity(text):
    text = str(text).strip().replace(',', '.')
    text = _normalize_temperature_text(text)
    try:
        quantity = UREG.parse_expression(text)
    except (pint.PintError, ValueError) as exc:
        raise ToolError('use a value and a unit, for example: 25 uM') from exc

    if not isinstance(quantity, pint.Quantity):
        raise ToolError('use a value and a unit, for example: 25 uM')
    return quantity


def _normalize_temperature_text(text):
    match = re.match(
        r'^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*(?:°\s*)?([CFK])\s*$',
        text,
        re.IGNORECASE,
    )
    if not match:
        return text
    return f'{match.group(1)} {_UNIT_ALIASES[match.group(2).lower()]}'


def _normalize_temperature_unit(unit):
    text = str(unit).strip()
    match = re.match(r'^(?:°\s*)?([CFK])$', text, re.IGNORECASE)
    if match:
        return _UNIT_ALIASES[match.group(1).lower()]
    return text


def _display_unit(unit):
    for units in DISPLAY_UNITS.values():
        for display, canonical in units:
            if unit in (display, canonical):
                return display
    return str(unit)
