"""Shared report rows for the genetics tools.

Each function returns ``(label_key, value)`` pairs. UIs decide layout and
localization; no numeric formatting or field ordering is duplicated there.
``None`` means "no structure" and is rendered with the UI's ``none`` label.
"""

from __future__ import annotations

from tools import convert_text, format_number, normalize_dna


def primer_rows(report):
    return [
        ('sequence', report.sequence),
        ('length', f'{report.length} nt'),
        ('gc', f'{report.gc:.1f}%'),
        ('tm', f'{report.tm:.1f} °C'),
        ('hairpin', _thermo(report.hairpin)),
        ('homodimer', _thermo(report.homodimer)),
    ]


def pair_rows(report):
    delta = abs(report.forward.tm - report.reverse.tm)
    rows = [
        ('forward', f'{report.forward.sequence} · Tm {report.forward.tm:.1f} °C'),
        ('reverse_primer', f'{report.reverse.sequence} · Tm {report.reverse.tm:.1f} °C'),
        ('gc', f'F {report.forward.gc:.1f}% · R {report.reverse.gc:.1f}%'),
        ('delta_tm', f'{delta:.1f} °C'),
        ('homodimer_forward', _thermo(report.forward.homodimer)),
        ('homodimer_reverse', _thermo(report.reverse.homodimer)),
        ('heterodimer', _thermo(report.heterodimer)),
        ('end_stability', _thermo(report.end_stability)),
    ]
    warnings = _pair_warnings(report, delta)
    if warnings:
        rows.append(('warnings', warnings))
    return rows


def dna_rows(sequence):
    sequence = normalize_dna(sequence)
    return [
        ('length', f'{len(sequence)} nt'),
        ('gc', f'{_gc(sequence):.1f}%'),
        ('complement', _complement(sequence)),
        ('reverse_seq', _reverse(sequence)),
        ('reverse_complement', _reverse_complement(sequence)),
    ]


def structure_rows(report):
    return [
        ('sequence', report.sequence),
        ('length', f'{len(report.sequence)} nt'),
        ('dg', 'n/a' if report.dg is None else f'{report.dg:.2f} kcal/mol'),
        ('tm', 'n/a' if report.tm is None else f'{report.tm:.1f} °C'),
        ('structure_fold', report.dot_bracket),
        ('pairs', _pairs(report.dot_bracket)),
    ]


def pcr_rows(report):
    rows = [
        ('product', f'{report.length} nt'),
        ('sequence', report.sequence),
    ]
    if report.degenerate:
        rows.append(('degenerate', str(report.degenerate)))
    return rows


def sequence_rows(record):
    return [
        ('name', record.name),
        ('format', record.source_format),
        ('length', f'{len(record.sequence)} nt'),
        ('topology', record.topology),
        ('records', str(record.record_count)),
        ('features', str(len(record.features))),
    ]


def layout_rows(report):
    return [
        ('wells', str(report.wells)),
        ('conditions', ', '.join(report.conditions) or 'none'),
    ]


def unit_rows(text, target_unit=None):
    return [
        (unit, format_number(amount))
        for unit, amount in convert_text(text, target_unit)
    ]


def _thermo(result):
    if not getattr(result, 'structure_found', False):
        return None
    return (
        f'Tm {result.tm:.1f} °C · '
        f'ΔG {result.dg / 1000.0:.2f} kcal/mol'
    )


def _pairs(dot_bracket):
    stacks = {}
    pairs = []
    for index, char in enumerate(dot_bracket, start=1):
        if char == '(':
            stacks.setdefault('(', []).append(index)
        elif char == ')' and stacks.get('('):
            pairs.append(f'{stacks["("].pop()}-{index}')
    return ', '.join(pairs) or 'none'


def _pair_warnings(report, delta):
    issues = []
    for label, primer in (('forward', report.forward), ('reverse', report.reverse)):
        if primer.gc < 40 or primer.gc > 60:
            issues.append(f'{label} GC {primer.gc:.1f}%')
        if primer.tm < 55 or primer.tm > 65:
            issues.append(f'{label} Tm {primer.tm:.1f} °C')
    if delta > 3:
        issues.append(f'ΔTm {delta:.1f} °C')
    if getattr(report.heterodimer, 'structure_found', False):
        issues.append('heterodimer present')
    if getattr(report.end_stability, 'structure_found', False):
        issues.append("3' end binding")
    for label, primer in (('forward', report.forward), ('reverse', report.reverse)):
        if getattr(primer.homodimer, 'structure_found', False):
            issues.append(f'{label} homodimer')
    return '; '.join(issues) or None


def _gc(sequence):
    return 100.0 * (sequence.count('G') + sequence.count('C')) / len(sequence)


def _complement(sequence):
    from Bio.Seq import Seq

    return str(Seq(sequence).complement())


def _reverse(sequence):
    return sequence[::-1]


def _reverse_complement(sequence):
    from Bio.Seq import Seq

    return str(Seq(sequence).reverse_complement())
