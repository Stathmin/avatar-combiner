# Genetics Workspace V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the flat `T` tools screen into a grouped genetics workspace with structure analysis, file import, plate-layout validation, in-silico PCR and XLSX export.

**Architecture:** Five small domain modules sit behind the TUI — `seq_structure` (seqfold), `seq_import` (Biopython + snapgene_reader), `plate_layout` (wellmap), `pcr_tools` (pydna) and `report_xlsx` (pandas + openpyxl). `src/ui.py` gets a grouped hub and five `tool_*` methods that reuse the existing prompt → result-box pattern. Heavy imports stay inside functions so TUI startup stays fast.

**Tech Stack:** Python 3.13, stdlib TUI, seqfold, snapgene_reader, wellmap, pydna, pandas, openpyxl, Biopython, pytest, ruff.

**Spec:** `docs/genetics-workspace-design.md` (design), `docs/genetics-suite-2026.md` (catalog: ideas 12, 13, 15, 29, 92)

## Global Constraints

- Python floor is `>=3.13`; `.python-version` already says `3.13`.
- Allowed runtime deps: `biopython>=1.87`, `pint>=0.24.4`, `primer3-py>=2.3.1`, `seqfold>=0.10.2`, `snapgene_reader>=0.1.23`, `pandas>=2.2`, `openpyxl>=3.1.5`, `wellmap>=3.5.2`, `pydna>=5.5.16`.
- pandas and openpyxl are allowed. Keep the bundle compact with PyInstaller excludes (`pandas.tests`, `pandas.io.clipboard`), not by removing functionality. `matplotlib` and `PIL` stay in the bundle because `wellmap` imports matplotlib eagerly.
- Do not import pandas, wellmap, pydna or openpyxl at module import time from a TUI-loaded module. Import them inside the function that needs them.
- TUI uses only the standard library and existing `Theme` tokens. No Textual, Rich, or new colour values.
- Every user-facing string goes into both `TEXT['en']` and `TEXT['ru']`.
- Ruff: line length 100, rules `E4,E7,E9,F,I`, target `py313`.
- Tests: `/root/.local/bin/uv run pytest -q`; local fallback `.venv/bin/python -m pytest -q`. Lint: `/root/.local/bin/uv run ruff check src tests`.
- Do not modify `src/tools.py` except through existing imports; it stays the general sequence/unit module.
- Commits are conventional, imperative, one per task.

## Review Focus

1. **Short oligos.** `seqfold` returns `dg = -inf` and malformed dot-brackets for `ATGC`. The wrapper must return `dg=None` and an all-dot fold.
2. **Multi-record files.** FASTA/GenBank with several records imports the first and reports the count; no silent single-record illusion.
3. **Corrupt `.dna`.** Random bytes produce one-line `ToolError`, never a traceback.
4. **RNA and IUPAC.** Lowercase/whitespace accepted; `U` rejected for structure and PCR with the existing ACGT message.
5. **Lazy heavy imports.** Importing `ui` must not import pandas, wellmap, pydna or openpyxl. A test asserts this.

---

### Task 0: Python 3.13 and dependencies

**Files:**
- Modify: `pyproject.toml`, `uv.lock`, `.python-version` (verify only)

**Interfaces:**
- Consumes: nothing.
- Produces: importable `seqfold`, `snapgene_reader`, `pandas`, `openpyxl`, `wellmap`, `pydna`.

- [ ] **Step 1: Raise the floor and add deps**

Set in `pyproject.toml`:

```toml
requires-python = ">=3.13"
dependencies = [
    "biopython>=1.87",
    "pint>=0.24.4",
    "primer3-py>=2.3.1",
    "seqfold>=0.10.2",
    "snapgene_reader>=0.1.23",
    "pandas>=2.2",
    "openpyxl>=3.1.5",
    "wellmap>=3.5.2",
    "pydna>=5.5.16",
]
```

And under `[tool.ruff]`: `target-version = "py313"`.

- [ ] **Step 2: Lock and sync**

Run: `/root/.local/bin/uv lock && /root/.local/bin/uv sync`
Expected: lock updated, environment synced, no resolver errors.

- [ ] **Step 3: Verify imports**

Run: `/root/.local/bin/uv run python -c "import seqfold, snapgene_reader, pandas, openpyxl, wellmap, pydna; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock .python-version
git commit -m "Raise Python floor to 3.13 and add genetics dependencies"
```

---

### Task 1: Structure module

**Files:**
- Create: `src/seq_structure.py`
- Test: `tests/test_seq_structure.py`

**Interfaces:**
- Consumes: `tools.normalize_primer`, `seqfold.fold/dg/tm/dot_bracket`.
- Produces: `StructureHit(energy, description)`, `StructureReport(sequence, dg, tm, dot_bracket, hits)`, `analyze_structure(sequence)`.

- [ ] **Step 1: Write failing tests**

```python
import pytest

import seq_structure
import tools


def test_structured_sequence_reports_energy_and_fold():
    report = seq_structure.analyze_structure('ACGTACGTACGT')

    assert report.sequence == 'ACGTACGTACGT'
    assert report.dot_bracket == '((((....))))'
    assert report.dg == pytest.approx(-1.7, abs=0.3)
    assert report.tm == pytest.approx(43.4, abs=0.3)
    assert len(report.hits) == 4


def test_short_sequence_is_sanitized():
    report = seq_structure.analyze_structure('ATGC')

    assert report.dg is None
    assert report.dot_bracket == '....'


def test_lowercase_and_whitespace_are_normalized():
    report = seq_structure.analyze_structure(' acgt acgt acgt ')

    assert report.sequence == 'ACGTACGTACGT'


def test_rna_and_invalid_bases_are_rejected():
    with pytest.raises(tools.ToolError):
        seq_structure.analyze_structure('ACGUACGU')
    with pytest.raises(tools.ToolError):
        seq_structure.analyze_structure('ACGTX')
    with pytest.raises(tools.ToolError):
        seq_structure.analyze_structure('   ')
```

- [ ] **Step 2: Run tests, expect failure**

Run: `/root/.local/bin/uv run pytest tests/test_seq_structure.py -q`
Expected: `ModuleNotFoundError: No module named 'seq_structure'`

- [ ] **Step 3: Implement `src/seq_structure.py`**

```python
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
```

- [ ] **Step 4: Run tests, expect pass**

Run: `/root/.local/bin/uv run pytest tests/test_seq_structure.py -q`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add src/seq_structure.py tests/test_seq_structure.py
git commit -m "Add oligo structure analysis with seqfold"
```

---

### Task 2: Sequence import module

**Files:**
- Create: `src/seq_import.py`
- Test: `tests/test_seq_import.py`

**Interfaces:**
- Consumes: `Bio.SeqIO`, `snapgene_reader.snapgene_file_to_dict`, `tools.ToolError`.
- Produces: `Feature`, `SequenceRecord`, `supported_extensions()`, `load_sequence(path)`.

- [ ] **Step 1: Write failing tests**

```python
import pytest
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqFeature import SeqFeature, SimpleLocation
from Bio.SeqRecord import SeqRecord

import seq_import
import tools


def write_fasta(path, records):
    path.write_text(
        ''.join(f'>{name}\n{sequence}\n' for name, sequence in records),
        encoding='utf-8',
    )


def test_loads_first_fasta_record_and_counts_the_rest(tmp_path):
    path = tmp_path / 'primers.fa'
    write_fasta(path, [('soy1', 'acgtn'), ('soy2', 'TTTT')])

    record = seq_import.load_sequence(path)

    assert record.name == 'soy1'
    assert record.sequence == 'ACGTN'
    assert record.source_format == 'fasta'
    assert record.topology == 'unknown'
    assert record.record_count == 2
    assert record.features == ()


def test_loads_genbank_with_features(tmp_path):
    path = tmp_path / 'marker.gb'
    record = SeqRecord(Seq('ACGTACGT'), id='soy1', name='soy1')
    record.annotations['topology'] = 'linear'
    record.features.append(
        SeqFeature(
            SimpleLocation(2, 6, strand=1),
            type='gene',
            qualifiers={'label': ['rbcL']},
        )
    )
    SeqIO.write(record, str(path), 'genbank')

    loaded = seq_import.load_sequence(path)

    assert loaded.name == 'soy1'
    assert loaded.sequence == 'ACGTACGT'
    assert loaded.source_format == 'genbank'
    assert loaded.topology == 'linear'
    assert len(loaded.features) == 1
    assert loaded.features[0].name == 'rbcL'
    assert loaded.features[0].start == 2
    assert loaded.features[0].end == 6
    assert loaded.features[0].strand == 1


def test_snapgene_mapping(tmp_path, monkeypatch):
    path = tmp_path / 'plasmid.dna'
    path.write_bytes(b'\t')

    monkeypatch.setattr(
        seq_import,
        'snapgene_file_to_dict',
        lambda _path: {
            'seq': 'acgtacgt',
            'dna': {'topology': 'circular'},
            'features': [
                {'name': 'F1', 'type': 'primer', 'start': 0, 'end': 4, 'strand': '+'}
            ],
        },
    )

    record = seq_import.load_sequence(path)

    assert record.name == 'plasmid'
    assert record.sequence == 'ACGTACGT'
    assert record.source_format == 'snapgene'
    assert record.topology == 'circular'
    assert record.features[0].name == 'F1'
    assert record.features[0].strand == 1


def test_corrupt_snapgene_is_wrapped(tmp_path):
    path = tmp_path / 'broken.dna'
    path.write_bytes(b'not a snapgene file')

    with pytest.raises(tools.ToolError, match='cannot read broken.dna'):
        seq_import.load_sequence(path)


def test_unsupported_and_missing_paths(tmp_path):
    text = tmp_path / 'notes.txt'
    text.write_text('hello', encoding='utf-8')

    with pytest.raises(tools.ToolError, match='unsupported file'):
        seq_import.load_sequence(text)
    with pytest.raises(tools.ToolError, match='file not found'):
        seq_import.load_sequence(tmp_path / 'missing.fa')
    with pytest.raises(tools.ToolError, match='file not found'):
        seq_import.load_sequence(tmp_path)
```

- [ ] **Step 2: Run tests, expect failure**

Run: `/root/.local/bin/uv run pytest tests/test_seq_import.py -q`
Expected: `ModuleNotFoundError: No module named 'seq_import'`

- [ ] **Step 3: Implement `src/seq_import.py`**

```python
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
    except Exception as exc:
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
```

- [ ] **Step 4: Run tests, expect pass**

Run: `/root/.local/bin/uv run pytest tests/test_seq_import.py -q`
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add src/seq_import.py tests/test_seq_import.py
git commit -m "Add FASTA, GenBank and SnapGene import"
```

---

### Task 3: Plate layout validation

**Files:**
- Create: `src/plate_layout.py`
- Test: `tests/test_plate_layout.py`

**Interfaces:**
- Consumes: `wellmap.load`, `tools.ToolError`; pandas transitively.
- Produces: `LayoutReport(wells, conditions)`, `load_layout(path)`.

- [ ] **Step 1: Write failing tests**

```python
import pytest

import plate_layout
import tools


def write_toml(path, body):
    path.write_text(body, encoding='utf-8')


def test_loads_two_well_layout(tmp_path):
    path = tmp_path / 'plate.toml'
    write_toml(
        path,
        '[well.A1]\nsample = "soy1"\n\n[well.B1]\nsample = "soy2"\n',
    )

    report = plate_layout.load_layout(path)

    assert report.wells == 2
    assert report.conditions == ('sample',)


def test_invalid_well_is_wrapped(tmp_path):
    path = tmp_path / 'bad.toml'
    write_toml(path, '[well.ZZ]\nsample = "x"\n')

    with pytest.raises(tools.ToolError, match='cannot read bad.toml'):
        plate_layout.load_layout(path)


def test_missing_file_is_rejected(tmp_path):
    with pytest.raises(tools.ToolError, match='file not found'):
        plate_layout.load_layout(tmp_path / 'missing.toml')
```

- [ ] **Step 2: Run tests, expect failure**

Run: `/root/.local/bin/uv run pytest tests/test_plate_layout.py -q`
Expected: `ModuleNotFoundError: No module named 'plate_layout'`

- [ ] **Step 3: Implement `src/plate_layout.py`**

```python
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
```

- [ ] **Step 4: Run tests, expect pass**

Run: `/root/.local/bin/uv run pytest tests/test_plate_layout.py -q`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add src/plate_layout.py tests/test_plate_layout.py
git commit -m "Add wellmap plate layout validation"
```

---

### Task 4: In-silico PCR

**Files:**
- Create: `src/pcr_tools.py`
- Test: `tests/test_pcr_tools.py`

**Interfaces:**
- Consumes: `pydna.amplify.pcr`, `pydna.dseqrecord.Dseqrecord`, `tools.normalize_primer`, `tools.ToolError`.
- Produces: `PcrReport(length, sequence, forward, reverse)`, `simulate_pcr(template, forward, reverse, circular=False)`.

- [ ] **Step 1: Write failing tests**

```python
import pytest
from Bio.Seq import Seq

import pcr_tools
import tools

TEMPLATE = (
    'GCTAAAGACAATTACATAACATACACGTCAGCACGAAACTTGTTGGCCCAGTGTGAATCGCTTAAGGG'
    'TTAAGTAAGTGTGATGCATACGCCTTTACTTGCTGTGTCCACCCCATCGGACTGGCATTTTTATTACA'
    'CTCAGAAACAGAACTCGGGTAATTTTGACAGGTCACGCAGAGGCGCGCCCTCCTGAAGTGCGTG'
)
FORWARD = TEMPLATE[:20]
REVERSE = str(Seq(TEMPLATE[-20:]).reverse_complement())


def test_simulates_a_product():
    report = pcr_tools.simulate_pcr(TEMPLATE, FORWARD, REVERSE)

    assert report.length == 200
    assert report.sequence == TEMPLATE
    assert report.forward == FORWARD
    assert report.reverse == REVERSE


def test_no_product_is_a_tool_error():
    with pytest.raises(tools.ToolError, match='no PCR product'):
        pcr_tools.simulate_pcr(TEMPLATE, 'A' * 20, 'T' * 20)


def test_rna_template_is_rejected():
    with pytest.raises(tools.ToolError):
        pcr_tools.simulate_pcr(TEMPLATE.replace('T', 'U', 1), FORWARD, REVERSE)
```

- [ ] **Step 2: Run tests, expect failure**

Run: `/root/.local/bin/uv run pytest tests/test_pcr_tools.py -q`
Expected: `ModuleNotFoundError: No module named 'pcr_tools'`

- [ ] **Step 3: Implement `src/pcr_tools.py`**

```python
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
    """Return the product of a PCR on a template."""
    template = normalize_primer(template)
    forward = normalize_primer(forward)
    reverse = normalize_primer(reverse)

    try:
        from pydna.amplify import pcr
        from pydna.dseqrecord import Dseqrecord

        amplicon = pcr(forward, reverse, Dseqrecord(template, circular=circular))
    except Exception as exc:
        raise ToolError(f'no PCR product: {exc}') from exc

    return PcrReport(
        length=len(amplicon),
        sequence=str(amplicon.seq).upper(),
        forward=forward,
        reverse=reverse,
    )
```

- [ ] **Step 4: Run tests, expect pass**

Run: `/root/.local/bin/uv run pytest tests/test_pcr_tools.py -q`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add src/pcr_tools.py tests/test_pcr_tools.py
git commit -m "Add in-silico PCR with pydna"
```

---

### Task 5: XLSX export

**Files:**
- Create: `src/report_xlsx.py`
- Test: `tests/test_report_xlsx.py`

**Interfaces:**
- Consumes: `pandas.read_csv`, `pandas.ExcelWriter`, `openpyxl.load_workbook`, `tools.ToolError`.
- Produces: `SHEETS`, `export_workbook(result_dir) -> Path`.

- [ ] **Step 1: Write failing tests**

```python
import pytest
from openpyxl import load_workbook

import report_xlsx
import tools


def test_exports_result_folder(tmp_path):
    result_dir = tmp_path / 'Результат 1'
    result_dir.mkdir()
    (result_dir / 'combined_384_plate.csv').write_text(
        'A,B\n1,2\n', encoding='utf-8'
    )
    (result_dir / 'metadata.csv').write_text(
        'sample,value\nsoy1,10\n', encoding='utf-8'
    )

    output = report_xlsx.export_workbook(result_dir)

    assert output.name == 'combined_384_plate.xlsx'
    assert output.is_file()
    workbook = load_workbook(output)
    assert workbook.sheetnames == ['combined', 'metadata']
    assert workbook['combined']['A1'].value == 'A'
    assert workbook['combined']['B2'].value == 2
    assert workbook['combined'].freeze_panes == 'A2'
    assert workbook['combined']['A1'].font.bold is True


def test_missing_folder_is_rejected(tmp_path):
    with pytest.raises(tools.ToolError, match='folder not found'):
        report_xlsx.export_workbook(tmp_path / 'missing')


def test_folder_without_csv_is_rejected(tmp_path):
    result_dir = tmp_path / 'empty'
    result_dir.mkdir()

    with pytest.raises(tools.ToolError, match='no CSV files'):
        report_xlsx.export_workbook(result_dir)
```

- [ ] **Step 2: Run tests, expect failure**

Run: `/root/.local/bin/uv run pytest tests/test_report_xlsx.py -q`
Expected: `ModuleNotFoundError: No module named 'report_xlsx'`

- [ ] **Step 3: Implement `src/report_xlsx.py`**

```python
"""Export pipeline CSV results to one formatted XLSX workbook.

pandas and openpyxl are imported inside export_workbook so the TUI does not pay
their import cost at startup.
"""

from __future__ import annotations

from pathlib import Path

from tools import ToolError

SHEETS = (
    ('combined', 'combined_384_plate.csv'),
    ('pivot', 'combined_384_plate_pivot.csv'),
    ('metadata', 'metadata.csv'),
    ('plate1', 'plate1.csv'),
    ('plate2', 'plate2.csv'),
    ('plate3', 'plate3.csv'),
    ('plate4', 'plate4.csv'),
)


def export_workbook(result_dir):
    """Write available CSV files from a result folder into one XLSX."""
    result_dir = Path(result_dir)
    if not result_dir.is_dir():
        raise ToolError(f'folder not found: {result_dir}')

    available = [
        (sheet, result_dir / filename)
        for sheet, filename in SHEETS
        if (result_dir / filename).is_file()
    ]
    if not available:
        raise ToolError(f'no CSV files in {result_dir}')

    import pandas as pd
    from openpyxl import load_workbook
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter

    output = result_dir / 'combined_384_plate.xlsx'
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet, path in available:
            pd.read_csv(path).to_excel(writer, sheet_name=sheet, index=False)

    workbook = load_workbook(output)
    for sheet in workbook.worksheets:
        sheet.freeze_panes = 'A2'
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        for column in sheet.columns:
            width = max(len(str(cell.value or '')) for cell in column) + 2
            sheet.column_dimensions[get_column_letter(column[0].column)].width = min(width, 40)
    workbook.save(output)

    return output
```

- [ ] **Step 4: Run tests, expect pass**

Run: `/root/.local/bin/uv run pytest tests/test_report_xlsx.py -q`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add src/report_xlsx.py tests/test_report_xlsx.py
git commit -m "Add formatted XLSX export for results"
```

---

### Task 6: Genetics hub and UI wiring

**Files:**
- Modify: `src/ui.py`, `tests/test_ui.py`

**Interfaces:**
- Consumes: all five modules from Tasks 1–5.
- Produces: `App.tool_structure`, `App.tool_import`, `App.tool_layout`, `App.tool_pcr`, `App.tool_xlsx`, `App.tool_menu_row`; keys `5`–`9`.

- [ ] **Step 1: Write failing tests**

Append to `tests/test_ui.py`:

```python
def test_tools_hub_lists_all_groups(tmp_path):
    app = make_app(tmp_path, lang='en')

    text = plain(app.render_tools(100, 30))

    assert 'INSPECT' in text
    assert 'STRUCTURE' in text
    assert 'FILES' in text
    for key in ('[5]', '[6]', '[7]', '[8]', '[9]'):
        assert key in text


def test_tools_hub_dispatches_new_keys(tmp_path, monkeypatch):
    app = make_app(tmp_path, lang='en')
    calls = []
    for name in ('tool_structure', 'tool_import', 'tool_layout', 'tool_pcr', 'tool_xlsx'):
        monkeypatch.setattr(app, name, lambda name=name: calls.append(name))

    for key in '56789':
        app.handle_tools_key(key)

    assert calls == [
        'tool_structure',
        'tool_import',
        'tool_layout',
        'tool_pcr',
        'tool_xlsx',
    ]


def test_structure_tool_renders_report(tmp_path, monkeypatch):
    app = make_app(tmp_path, lang='en')
    monkeypatch.setattr(app, 'prompt_text', lambda *args, **kwargs: 'ACGTACGTACGT')

    app.tool_structure()
    text = plain(app.tool_output)

    assert 'kcal/mol' in text
    assert '((((....))))' in text
    assert '12 nt' in text


def test_layout_tool_renders_wells(tmp_path, monkeypatch):
    app = make_app(tmp_path, lang='en')
    path = tmp_path / 'plate.toml'
    path.write_text('[well.A1]\nsample = "soy1"\n', encoding='utf-8')
    monkeypatch.setattr(app, 'prompt_text', lambda *args, **kwargs: str(path))

    app.tool_layout()
    text = plain(app.tool_output)

    assert '1' in text
    assert 'sample' in text


def test_pcr_tool_renders_product(tmp_path, monkeypatch):
    app = make_app(tmp_path, lang='en')
    monkeypatch.setattr(app, 'prompt_text', lambda *args, **kwargs: 'ACGT')
    monkeypatch.setattr(
        pcr_tools,
        'simulate_pcr',
        lambda *args: pcr_tools.PcrReport(200, 'ACGT', 'ACGT', 'ACGT'),
    )

    app.tool_pcr()
    text = plain(app.tool_output)

    assert '200 nt' in text


def test_xlsx_tool_writes_workbook(tmp_path, monkeypatch):
    app = make_app(tmp_path, lang='en')
    result_dir = tmp_path / 'Результат 1'
    result_dir.mkdir()
    (result_dir / 'combined_384_plate.csv').write_text('A\n1\n', encoding='utf-8')
    monkeypatch.setattr(app, 'prompt_text', lambda *args, **kwargs: str(result_dir))

    app.tool_xlsx()

    assert (result_dir / 'combined_384_plate.xlsx').is_file()
```

Add `import pcr_tools` next to the existing imports at the top of `tests/test_ui.py`.

- [ ] **Step 2: Run tests, expect failure**

Run: `/root/.local/bin/uv run pytest tests/test_ui.py -q`
Expected: failures on `INSPECT`, `tool_structure`, and missing keys.

- [ ] **Step 3: Add imports and TEXT keys**

At the top of `src/ui.py`, next to `import tools as genetics`:

```python
import pcr_tools
import plate_layout
import report_xlsx
import seq_import
import seq_structure
```

Add to `TEXT['en']`:

```python
'tools': 'Genetics',
'group_inspect': 'INSPECT',
'group_structure': 'STRUCTURE',
'group_files': 'FILES',
'tool_structure': 'Oligo structure',
'tool_import': 'Import sequence file',
'tool_layout': 'Validate plate layout',
'tool_pcr': 'In-silico PCR',
'tool_xlsx': 'Export result to XLSX',
'structure_hint': 'ACGT only. Hairpins and self-dimers.',
'structure_dg': 'ΔG',
'structure_fold': 'Fold',
'structure_none': 'no stable structure',
'import_name': 'Name',
'import_path': 'File path',
'import_format': 'Format',
'import_topology': 'Topology',
'import_records': 'Records',
'import_features': 'Features',
'import_hint': '.gb .gbk .dna .fa .fasta',
'layout_hint': 'Path to a wellmap .toml',
'layout_wells': 'Wells',
'layout_conditions': 'Conditions',
'pcr_template': 'Template',
'pcr_forward': 'Forward',
'pcr_reverse': 'Reverse',
'pcr_product': 'Product',
'xlsx_hint': 'Path to a «Результат N» folder',
'xlsx_done': 'Saved',
'tool_footer': '1–4 inspect  ·  5–8 analyse  ·  6–9 files  ·  B back',
```

Add to `TEXT['ru']`:

```python
'tools': 'Генетика',
'group_inspect': 'ПРОВЕРКА',
'group_structure': 'СТРУКТУРА',
'group_files': 'ФАЙЛЫ',
'tool_structure': 'Структура олиго',
'tool_import': 'Импорт файла',
'tool_layout': 'Проверить раскладку',
'tool_pcr': 'ПЦР in silico',
'tool_xlsx': 'Экспорт в XLSX',
'structure_hint': 'Только ACGT. Шпильки и самодимеры.',
'structure_dg': 'ΔG',
'structure_fold': 'Складка',
'structure_none': 'нет устойчивой структуры',
'import_name': 'Название',
'import_path': 'Путь к файлу',
'import_format': 'Формат',
'import_topology': 'Топология',
'import_records': 'Записей',
'import_features': 'Признаки',
'import_hint': '.gb .gbk .dna .fa .fasta',
'layout_hint': 'Путь к .toml wellmap',
'layout_wells': 'Лунок',
'layout_conditions': 'Условия',
'pcr_template': 'Матрица',
'pcr_forward': 'Прямой',
'pcr_reverse': 'Обратный',
'pcr_product': 'Продукт',
'xlsx_hint': 'Путь к папке «Результат N»',
'xlsx_done': 'Сохранено',
'tool_footer': '1–4 проверка  ·  5–8 анализ  ·  6–9 файлы  ·  B назад',
```

- [ ] **Step 4: Replace `render_tools`**

```python
    def render_tools(self, width, height):
        lines = self.header(width)
        lines.append('')
        inner = width - 4
        actions = [
            self.theme.paint(self.t['group_inspect'], 'dim', bold=True),
            self.tool_menu_row(
                [('1', self.t['tool_tm'], 'accent'), ('2', self.t['tool_pair'], 'accent')],
                inner,
            ),
            self.tool_menu_row(
                [('3', self.t['tool_dna'], 'accent'), ('4', self.t['tool_units'], 'accent')],
                inner,
            ),
            '',
            self.theme.paint(self.t['group_structure'], 'dim', bold=True),
            self.tool_menu_row(
                [
                    ('5', self.t['tool_structure'], 'accent2'),
                    ('8', self.t['tool_pcr'], 'accent2'),
                ],
                inner,
            ),
            '',
            self.theme.paint(self.t['group_files'], 'dim', bold=True),
            self.tool_menu_row(
                [
                    ('6', self.t['tool_import'], 'accent2'),
                    ('7', self.t['tool_layout'], 'accent2'),
                ],
                inner,
            ),
            self.tool_menu_row([('9', self.t['tool_xlsx'], 'accent2')], inner),
            '',
            self.theme.paint('[B]', 'muted', bold=True) + ' ' + self.t['back'],
        ]
        lines.extend(box(self.t['tools'], actions, width, self.theme))

        if self.tool_output:
            lines.append('')
            lines.extend(box(self.t['tool_result'], self.tool_output, width, self.theme))

        lines.append('')
        lines.extend(self.footer_lines(width, self.t['tool_footer']))
        return lines

    def tool_menu_row(self, items, width):
        column = max(20, (width - 2) // 2)
        cells = [
            self.menu_item((key, '', label, role), column)
            for key, label, role in items
        ]
        return pad(cells[0], column) + '  ' + (cells[1] if len(cells) > 1 else '')
```

- [ ] **Step 5: Add the five tool methods**

Insert after `tool_units`:

```python
    def tool_structure(self):
        self.tool_output = []
        sequence = self.prompt_text(self.t['tool_structure'], self.t['structure_hint'])
        if sequence is None:
            return
        try:
            report = seq_structure.analyze_structure(sequence)
        except Exception as exc:
            self.set_tool_error(exc)
            return

        dg = self.t['none'] if report.dg is None else f'{report.dg:.2f} kcal/mol'
        tm = self.t['none'] if report.tm is None else f'{report.tm:.1f} °C'
        self.tool_output = [
            self.tool_line(self.t['sequence'], report.sequence),
            self.tool_line(self.t['length'], f'{len(report.sequence)} nt'),
            self.tool_line(self.t['structure_dg'], dg),
            self.tool_line(self.t['tm'], tm),
        ]
        self.tool_output.extend(
            self.tool_sequence_lines(self.t['structure_fold'], report.dot_bracket)
        )
        if not report.hits:
            self.tool_output.append(self.theme.paint(self.t['structure_none'], 'dim'))

    def tool_import(self):
        self.tool_output = []
        path = self.prompt_text(self.t['import_path'], self.t['import_hint'])
        if path is None:
            return
        try:
            record = seq_import.load_sequence(path)
        except Exception as exc:
            self.set_tool_error(exc)
            return

        self.tool_output = [
            self.tool_line(self.t['import_name'], record.name),
            self.tool_line(self.t['import_format'], record.source_format),
            self.tool_line(self.t['length'], f'{len(record.sequence)} nt'),
            self.tool_line(self.t['import_topology'], record.topology),
            self.tool_line(self.t['import_records'], str(record.record_count)),
            self.tool_line(self.t['import_features'], str(len(record.features))),
        ]
        self.tool_output.extend(
            self.tool_sequence_lines(self.t['sequence'], record.sequence[:60])
        )

    def tool_layout(self):
        self.tool_output = []
        path = self.prompt_text(self.t['tool_layout'], self.t['layout_hint'])
        if path is None:
            return
        try:
            report = plate_layout.load_layout(path)
        except Exception as exc:
            self.set_tool_error(exc)
            return

        self.tool_output = [
            self.tool_line(self.t['layout_wells'], str(report.wells)),
            self.tool_line(
                self.t['layout_conditions'],
                ', '.join(report.conditions) or self.t['none'],
            ),
        ]

    def tool_pcr(self):
        self.tool_output = []
        values = []
        for title in (self.t['pcr_template'], self.t['pcr_forward'], self.t['pcr_reverse']):
            value = self.prompt_text(title, self.t['primer_hint'])
            if value is None:
                return
            values.append(value)
        try:
            report = pcr_tools.simulate_pcr(*values)
        except Exception as exc:
            self.set_tool_error(exc)
            return

        self.tool_output = [
            self.tool_line(self.t['pcr_product'], f'{report.length} nt'),
        ]
        self.tool_output.extend(
            self.tool_sequence_lines(self.t['sequence'], report.sequence[:60])
        )

    def tool_xlsx(self):
        self.tool_output = []
        path = self.prompt_text(self.t['tool_xlsx'], self.t['xlsx_hint'])
        if path is None:
            return
        try:
            output = report_xlsx.export_workbook(path)
        except Exception as exc:
            self.set_tool_error(exc)
            return

        self.tool_output = [
            self.tool_line(self.t['xlsx_done'], str(output)),
        ]
```

- [ ] **Step 6: Wire the keys**

Extend `handle_tools_key`:

```python
        elif key == '5':
            self.tool_structure()
        elif key == '6':
            self.tool_import()
        elif key == '7':
            self.tool_layout()
        elif key == '8':
            self.tool_pcr()
        elif key == '9':
            self.tool_xlsx()
```

- [ ] **Step 7: Add the lazy-import guard test**

```python
def test_ui_does_not_import_heavy_modules_at_startup():
    import subprocess
    import sys

    code = (
        'import sys, ui; '
        "print(any(m in sys.modules for m in "
        "['pandas', 'wellmap', 'pydna', 'openpyxl']))"
    )
    output = subprocess.run(
        [sys.executable, '-c', code],
        cwd='src',
        capture_output=True,
        text=True,
        check=True,
    )
    assert output.stdout.strip() == 'False'
```

- [ ] **Step 8: Run tests**

Run: `/root/.local/bin/uv run pytest tests/test_ui.py -q`
Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add src/ui.py tests/test_ui.py
git commit -m "Add grouped genetics hub with five tools"
```

---

### Task 7: Packaging, help and docs

**Files:**
- Modify: `src/build_binary.py`, `src/ui.py` (`HELP`), `README.md`

**Interfaces:**
- Consumes: Tasks 1–6.
- Produces: Windows build incl. new modules; compact pandas; updated docs.

- [ ] **Step 1: Update PyInstaller inputs**

In `src/build_binary.py` add after the existing `tools` entries:

```python
        '--hidden-import', 'seq_structure',
        '--hidden-import', 'seq_import',
        '--hidden-import', 'plate_layout',
        '--hidden-import', 'pcr_tools',
        '--hidden-import', 'report_xlsx',
        '--collect-all', 'seqfold',
        '--hidden-import', 'snapgene_reader',
        '--hidden-import', 'xmltodict',
        '--hidden-import', 'html2text',
        '--hidden-import', 'wellmap',
        '--hidden-import', 'pydna',
        '--hidden-import', 'openpyxl',
        '--collect-all', 'pydna',
        '--collect-all', 'wellmap',
        '--collect-all', 'pydivsufsort',
        '--collect-all', 'seguid',
        '--collect-all', 'sgffp',
```

Remove the exclusion pairs for `matplotlib`, `numpy`, `pandas`, `PIL` and `urllib`.
`wellmap` imports matplotlib eagerly, matplotlib needs Pillow, and
`snapgene_reader` -> `html2text` imports `urllib.parse`. Keep `tkinter`,
`pytest`, `ruff`, `pip`, `setuptools`, `pkg_resources`, `unittest`.
Also remove `Bio.SeqIO`, `Bio.SeqRecord` and `Bio.restriction` from the
exclusion list: pydna imports them for PCR. Keep the other Bio excludes.

Add compact pandas excludes:

```python
        '--exclude-module', 'pandas.tests',
        '--exclude-module', 'pandas.io.clipboard',
```

- [ ] **Step 2: Update HELP**

Replace the `Tools` row in `HELP['en']` with:

```python
('Tools', 'Press T. Inspect primers and DNA, analyse oligo structure and in-silico PCR, validate wellmap layouts, import GenBank, SnapGene and FASTA files, and export results to XLSX.'),
```

Replace `Инструменты` in `HELP['ru']` with:

```python
('Инструменты', 'Нажмите T. Проверка праймеров и ДНК, структура олиго и ПЦР in silico, проверка раскладки wellmap, импорт GenBank, SnapGene и FASTA, экспорт результатов в XLSX.'),
```

- [ ] **Step 3: Update README**

Extend the tools table with keys 5–9 and replace the runtime paragraph with:

```
Рантайм: Bio.Seq и SeqIO для последовательностей, Pint для единиц,
Primer3-py для термодинамики, seqfold для структуры олиго, pydna для ПЦР
in silico, wellmap для раскладок, pandas и openpyxl для таблиц и XLSX.
В сборке исключены только тесты pandas; matplotlib входит в сборку, потому
что его импортирует wellmap.
```

Update the Python requirement line to `Python 3.13+`.

- [ ] **Step 4: Run the full gate**

Run: `/root/.local/bin/uv run pytest -q`
Expected: all tests pass.

Run: `/root/.local/bin/uv run ruff check src tests`
Expected: `All checks passed!`

- [ ] **Step 5: Commit**

```bash
git add src/build_binary.py src/ui.py README.md
git commit -m "Package and document the genetics workspace"
```

---

## Parallel execution split

SDD executes one implementer at a time. The table below is the ownership map for
a future parallel run; no two streams share a file.

| Stream | Worktree | Branch | Owns | Must not touch |
|---|---|---|---|---|
| A | `../avatar-seq-structure` | `feat/seq-structure` | `src/seq_structure.py`, `tests/test_seq_structure.py` | everything else |
| B | `../avatar-seq-import` | `feat/seq-import` | `src/seq_import.py`, `tests/test_seq_import.py` | everything else |
| C | `../avatar-plate-layout` | `feat/plate-layout` | `src/plate_layout.py`, `tests/test_plate_layout.py` | everything else |
| D | `../avatar-pcr` | `feat/pcr` | `src/pcr_tools.py`, `tests/test_pcr_tools.py` | everything else |
| E | `../avatar-xlsx` | `feat/xlsx` | `src/report_xlsx.py`, `tests/test_report_xlsx.py` | everything else |
| F | main worktree | `feat/genetics-workspace` | `src/ui.py`, `tests/test_ui.py`, `pyproject.toml`, `uv.lock`, `src/build_binary.py`, `README.md` | module files |

Merge order: A, B, C, D, E, then F. Run the full suite after each merge. For
this plan, SDD runs them sequentially in one worktree; the split exists so the
work can be parallelised later without rediscovering file boundaries.
