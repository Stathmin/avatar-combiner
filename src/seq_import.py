"""Import sequences from FASTA, GenBank and SnapGene files.

FASTA and GenBank parsing use Biopython. SnapGene files use snapgene_reader.
All format errors surface as ToolError so the TUI can show one line.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from Bio import SeqIO
from snapgene_reader import snapgene_file_to_dict

from tools import ToolError

GENBANK_SUFFIXES = ('.gb', '.gbk', '.genbank')
FASTA_SUFFIXES = ('.fa', '.fasta', '.fna')
SNAPGENE_SUFFIXES = ('.dna',)

_STRANDS = {'+': 1, '-': -1, '.': 0, '=': 0}


@dataclass(frozen=True)
class Feature:
    name: str
    kind: str
    start: int
    end: int
    strand: int


@dataclass(frozen=True)
class SequenceRecord:
    name: str
    sequence: str
    topology: str
    features: tuple[Feature, ...]
    source_format: str
    record_count: int


def supported_extensions():
    """Return the accepted file suffixes."""
    return GENBANK_SUFFIXES + FASTA_SUFFIXES + SNAPGENE_SUFFIXES


def load_sequence(path):
    """Load the first record from a supported sequence file."""
    path = Path(path)
    if not path.is_file():
        raise ToolError(f'file not found: {path}')

    suffix = path.suffix.lower()
    try:
        if suffix in GENBANK_SUFFIXES:
            return _load_biopython(path, 'genbank')
        if suffix in FASTA_SUFFIXES:
            return _load_biopython(path, 'fasta')
        if suffix in SNAPGENE_SUFFIXES:
            return _load_snapgene(path)
    except ToolError:
        raise
    except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError, UnicodeError) as exc:
        raise ToolError(f'cannot read {path.name}: {exc}') from exc

    raise ToolError(f'unsupported file: {suffix or path.name}')


def _load_biopython(path, fmt):
    records = SeqIO.parse(str(path), fmt)
    first = next(records, None)
    if first is None:
        raise ToolError(f'no {fmt} records in {path.name}')

    count = 1 + sum(1 for _ in records)
    topology = str(first.annotations.get('topology', 'unknown')).lower()
    return SequenceRecord(
        name=first.name or first.id or path.stem,
        sequence=str(first.seq).upper(),
        topology=topology if topology in ('linear', 'circular') else 'unknown',
        features=tuple(_bio_feature(feature) for feature in first.features),
        source_format=fmt,
        record_count=count,
    )


def _load_snapgene(path):
    data = snapgene_file_to_dict(str(path))
    sequence = str(data.get('seq', '')).upper()
    if not sequence:
        raise ToolError(f'no sequence in {path.name}')

    return SequenceRecord(
        name=path.stem,
        sequence=sequence,
        topology=str(data.get('dna', {}).get('topology', 'unknown')).lower(),
        features=tuple(_snapgene_feature(feature) for feature in data.get('features', [])),
        source_format='snapgene',
        record_count=1,
    )


def _bio_feature(feature):
    qualifiers = feature.qualifiers or {}
    label = qualifiers.get('label') or qualifiers.get('gene') or qualifiers.get('product')
    if isinstance(label, list):
        label = label[0] if label else None
    strand = feature.location.strand
    return Feature(
        name=str(label or feature.type),
        kind=str(feature.type),
        start=int(feature.location.start),
        end=int(feature.location.end),
        strand=int(strand) if strand is not None else 0,
    )


def _snapgene_feature(feature):
    return Feature(
        name=str(feature.get('name') or feature.get('type') or 'feature'),
        kind=str(feature.get('type', 'feature')),
        start=int(feature.get('start', 0)),
        end=int(feature.get('end', 0)),
        strand=_STRANDS.get(str(feature.get('strand', '.')), 0),
    )
