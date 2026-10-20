"""In-silico PCR backed by pydna.

pydna is imported inside the function to keep TUI startup light. Any failure
(no product, ambiguous binding, invalid input) becomes a ToolError.
"""

from __future__ import annotations

from dataclasses import dataclass

from tools import ToolError, normalize_primer


@dataclass(frozen=True)
class PcrReport:
    length: int
    sequence: str
    forward: str
    reverse: str


def simulate_pcr(template, forward, reverse, circular=False):
    """Return the product of a PCR on a template.

    ``PcrReport.sequence`` is the linearised amplicon starting at the forward
    primer and ending at the reverse primer, so template flanks are excluded.
    """
    try:
        from pydna.amplify import pcr
        from pydna.dseqrecord import Dseqrecord
    except ImportError as exc:
        raise ToolError('pydna is not available') from exc

    if not isinstance(circular, bool):
        raise ToolError('circular must be True or False')

    template = normalize_primer(template)
    forward = normalize_primer(forward)
    reverse = normalize_primer(reverse)

    try:
        amplicon = pcr(forward, reverse, Dseqrecord(template, circular=circular))
    except ValueError as exc:
        detail = str(exc).splitlines()[0]
        raise ToolError(f'no PCR product: {detail}') from exc

    return PcrReport(
        length=len(amplicon),
        sequence=str(amplicon.seq).upper(),
        forward=forward,
        reverse=reverse,
    )
