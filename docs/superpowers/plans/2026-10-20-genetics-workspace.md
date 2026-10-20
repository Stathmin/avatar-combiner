# Genetics Workspace V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the flat `T` tools screen into a grouped genetics workspace with local oligo secondary-structure analysis and sequence-file import.

**Architecture:** Two new pure-Python modules hold the domain logic — `src/seq_structure.py` wraps `seqfold`, `src/seq_import.py` wraps Biopython GenBank/FASTA parsing and `snapgene_reader`. `src/ui.py` gets a grouped hub and two new `tool_*` methods that follow the existing prompt → result-box pattern. No network, no pandas, no numpy.

**Tech Stack:** Python 3.9+, stdlib TUI, `seqfold`, `snapgene_reader`, Biopython (`Bio.SeqIO`), pytest, ruff.

**Spec:** `docs/genetics-workspace-design.md` (design), `docs/genetics-suite-2026.md` (idea catalog, entries 13 and 29)

## Global Constraints

- Python floor is `>=3.9` from `pyproject.toml`; new code must run on 3.9.
- The PyInstaller bundle must not include `pandas`, `numpy`, `openpyxl`, `matplotlib`, `Rich` or `Textual`.
- New runtime deps are limited to `seqfold>=0.10.2` (MIT) and `snapgene_reader>=0.1.23` (MIT).
- TUI code uses only the standard library and the existing `Theme` tokens in `src/ui.py`.
- Every user-facing string goes into both `TEXT['en']` and `TEXT['ru']`.
- Ruff: line length 100, rules `E4,E7,E9,F,I`.
- Test command in this environment: `.venv/bin/python -m pytest -q` (`uv` is not on PATH here); on a normal checkout use `uv run pytest -q`.
- Do not add `openpyxl`: the project reads XLSX with its own reader on purpose.
- Do not touch `src/tools.py`; it stays the general sequence/unit module.

## Review Focus

1. **Short oligos.** `seqfold` returns `dg = -inf` and a malformed dot-bracket for inputs like `ATGC`. The wrapper must return `dg=None` and an all-dot fold, not leak `inf` into the UI.
2. **Multi-record files.** A FASTA or GenBank file with several records must import the first record and report the total count; it must not silently look like one record.
3. **Corrupt binary files.** A random `.dna` file must produce `ToolError: cannot read <name>: ...`, never a traceback or a hang.
4. **Sequence normalisation.** Lowercase and whitespace are accepted; `U` (RNA) is rejected with the existing ACGT message for structure analysis.
5. **Unsupported paths.** `.txt`, a directory, or a missing path must produce one-line `ToolError` text suitable for the result box.

---

### Task 0: Dependencies

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`

**Interfaces:**
- Consumes: nothing.
- Produces: importable `seqfold` and `snapgene_reader` for Tasks 1–2.

- [ ] **Step 1: Add the two dependencies**

In `pyproject.toml`, extend `[project].dependencies` to:

```toml
dependencies = [
    "biopython>=1.85",
    "pint>=0.24.4",
    "primer3-py>=2.3.1",
    "seqfold>=0.10.2",
    "snapgene_reader>=0.1.23",
]
```

- [ ] **Step 2: Refresh the lockfile and environment**

Run: `uv lock && uv sync`
Expected: `uv.lock` updated, both packages installed.

If `uv` is unavailable, install them into the existing environment with
`.venv/bin/python -m pip install "seqfold>=0.10.2" "snapgene_reader>=0.1.23"`;
do not hand-edit `uv.lock`.

- [ ] **Step 3: Verify the imports**

Run: `uv run python -c "import seqfold, snapgene_reader; print(seqfold.__name__, snapgene_reader.__name__)"`
Expected: `seqfold snapgene_reader`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "Add seqfold and snapgene_reader dependencies"
```

---

### Task 1: Structure module

**Files:**
- Create: `src/seq_structure.py`
- Test: `tests/test_seq_structure.py`

**Interfaces:**
- Consumes: `tools.normalize_primer(sequence) -> str`, `tools.ToolError`; `seqfold.fold`, `seqfold.dg`, `seqfold.tm`, `seqfold.dot_bracket`.
- Produces:
  - `StructureHit(energy: float, description: str)`
  - `StructureReport(sequence: str, dg: Optional[float], tm: Optional[float], dot_bracket: str, hits: tuple[StructureHit, ...])`
  - `analyze_structure(sequence: str) -> StructureReport`

- [ ] **Step 1: Write the failing tests**

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

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_seq_structure.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'seq_structure'`

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

Note: `Optional[float]` keeps the module importable on Python 3.9 without
relying on `X | Y` runtime syntax.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_seq_structure.py -q`
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
- Produces:
  - `Feature(name: str, kind: str, start: int, end: int, strand: int)`
  - `SequenceRecord(name: str, sequence: str, topology: str, features: tuple[Feature, ...], source_format: str, record_count: int)`
  - `supported_extensions() -> tuple[str, ...]`
  - `load_sequence(path) -> SequenceRecord`

- [ ] **Step 1: Write the failing tests**

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

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_seq_import.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'seq_import'`

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
    strand = feature.get('strand', '.')
    return Feature(
        name=str(feature.get('name') or feature.get('type') or 'feature'),
        kind=str(feature.get('type', 'feature')),
        start=int(feature.get('start', 0)),
        end=int(feature.get('end', 0)),
        strand=_STRANDS.get(str(strand), 0),
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_seq_import.py -q`
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add src/seq_import.py tests/test_seq_import.py
git commit -m "Add FASTA, GenBank and SnapGene import"
```

---

### Task 3: Genetics hub and UI wiring

**Files:**
- Modify: `src/ui.py`
- Test: `tests/test_ui.py`

**Interfaces:**
- Consumes: `seq_structure.analyze_structure`, `seq_import.load_sequence`.
- Produces: `App.tool_structure()`, `App.tool_import()`, `App.tool_menu_row(items, width)`, new keys `5` and `6` in `handle_tools_key`, new `TEXT` entries listed in the design copy deck plus `import_name`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_ui.py`:

```python
def test_tools_hub_lists_inspect_and_file_groups(tmp_path):
    app = make_app(tmp_path, lang='en')

    text = plain(app.render_tools(100, 30))

    assert 'INSPECT' in text
    assert 'STRUCTURE & FILES' in text
    assert '[5]' in text
    assert '[6]' in text
    assert '[B]' in text


def test_tools_hub_dispatches_new_keys(tmp_path, monkeypatch):
    app = make_app(tmp_path, lang='en')
    calls = []
    monkeypatch.setattr(app, 'tool_structure', lambda: calls.append('structure'))
    monkeypatch.setattr(app, 'tool_import', lambda: calls.append('import'))

    app.handle_tools_key('5')
    app.handle_tools_key('6')

    assert calls == ['structure', 'import']


def test_structure_tool_renders_report(tmp_path, monkeypatch):
    app = make_app(tmp_path, lang='en')
    monkeypatch.setattr(app, 'prompt_text', lambda *args, **kwargs: 'ACGTACGTACGT')

    app.tool_structure()
    text = plain(app.tool_output)

    assert 'kcal/mol' in text
    assert '((((....))))' in text
    assert '12 nt' in text


def test_import_tool_renders_fasta(tmp_path, monkeypatch):
    app = make_app(tmp_path, lang='en')
    path = tmp_path / 'primers.fa'
    path.write_text('>soy1\nACGTACGT\n', encoding='utf-8')
    monkeypatch.setattr(app, 'prompt_text', lambda *args, **kwargs: str(path))

    app.tool_import()
    text = plain(app.tool_output)

    assert 'fasta' in text
    assert '8 nt' in text
    assert 'soy1' in text
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_ui.py -q`
Expected: FAIL on `'INSPECT' not in text` and `AttributeError: 'App' object has no attribute 'tool_structure'`

- [ ] **Step 3: Add imports and text keys**

At the top of `src/ui.py`, next to `import tools as genetics`:

```python
import seq_import
import seq_structure
```

In `TEXT['en']`, add:

```python
'tools': 'Genetics',
'group_inspect': 'INSPECT',
'group_files': 'STRUCTURE & FILES',
'tool_structure': 'Oligo structure',
'tool_import': 'Import sequence file',
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
'tool_footer': '1–4 inspect  ·  5 structure  ·  6 import  ·  B back',
```

In `TEXT['ru']`, add:

```python
'tools': 'Генетика',
'group_inspect': 'ПРОВЕРКА',
'group_files': 'СТРУКТУРА И ФАЙЛЫ',
'tool_structure': 'Структура олиго',
'tool_import': 'Импорт файла',
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
'tool_footer': '1–4 проверка  ·  5 структура  ·  6 импорт  ·  B назад',
```

- [ ] **Step 4: Replace `render_tools` and add the row helper**

Replace the body of `render_tools` with:

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
            self.theme.paint(self.t['group_files'], 'dim', bold=True),
            self.tool_menu_row(
                [
                    ('5', self.t['tool_structure'], 'accent2'),
                    ('6', self.t['tool_import'], 'accent2'),
                ],
                inner,
            ),
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

- [ ] **Step 5: Add the two tool methods**

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
```

- [ ] **Step 6: Wire the keys**

Extend `handle_tools_key`:

```python
        elif key == '5':
            self.tool_structure()
        elif key == '6':
            self.tool_import()
```

- [ ] **Step 7: Run the UI tests**

Run: `.venv/bin/python -m pytest tests/test_ui.py -q`
Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add src/ui.py tests/test_ui.py
git commit -m "Add genetics hub with structure and import tools"
```

---

### Task 4: Packaging, help and docs

**Files:**
- Modify: `src/build_binary.py`
- Modify: `src/ui.py` (`HELP`)
- Modify: `README.md`

**Interfaces:**
- Consumes: the modules from Tasks 1–2.
- Produces: a Windows build that includes both new modules and their data; help text that names the new keys.

- [ ] **Step 1: Add PyInstaller inputs**

After the existing `tools` entries in `src/build_binary.py`, add:

```python
        '--hidden-import', 'seq_structure',
        '--hidden-import', 'seq_import',
        '--collect-all', 'seqfold',
        '--hidden-import', 'snapgene_reader',
        '--hidden-import', 'xmltodict',
        '--hidden-import', 'html2text',
```

Then remove the `--exclude-module`, `urllib` pair from the same command.
`snapgene_reader` imports `html2text`, which imports `urllib.parse`; keeping the
exclusion produces an exe that crashes the first time the Import tool opens.

- [ ] **Step 2: Update the help text**

In `HELP['en']`, replace the `Tools` row body with:

```python
('Tools', 'Press T. Inspect primers and DNA, analyse oligo structure with seqfold, or import GenBank, SnapGene and FASTA files.'),
```

In `HELP['ru']`, replace the `Инструменты` row body with:

```python
('Инструменты', 'Нажмите T. Проверка праймеров и ДНК, структура олиго через seqfold, импорт GenBank, SnapGene и FASTA.'),
```

- [ ] **Step 3: Update the README tools table**

Add rows after key `4`:

```markdown
| `5` | структура олиго: ΔG, Tm, шпильки (seqfold) |
| `6` | импорт `.gb`, `.gbk`, `.dna`, `.fa`, `.fasta` |
```

And extend the runtime paragraph with: `Файлы GenBank, SnapGene и FASTA
читаются через Biopython и snapgene_reader; структура олиго — через seqfold.`

- [ ] **Step 4: Run the full gate**

Run: `.venv/bin/python -m pytest -q`
Expected: all tests pass.

Run: `.venv/bin/python -m ruff check src tests`
Expected: `All checks passed!`

On Windows, build the exe and open tool `6` with a real `.dna` file. Expected:
the record renders; no `ModuleNotFoundError` for `html2text` or `urllib`.

- [ ] **Step 5: Commit**

```bash
git add src/build_binary.py src/ui.py README.md
git commit -m "Document and package the genetics workspace"
```

---

## Parallel execution split

The two module tasks are the only genuinely disjoint work. Tasks 3–4 touch
shared files and must stay sequential.

| Stream | Worktree | Branch | Owns | Must not touch |
|---|---|---|---|---|
| A | `../avatar-seq-structure` | `feat/seq-structure` | `src/seq_structure.py`, `tests/test_seq_structure.py` | everything else |
| B | `../avatar-seq-import` | `feat/seq-import` | `src/seq_import.py`, `tests/test_seq_import.py` | everything else |
| C | main clone | `main` | `src/ui.py`, `tests/test_ui.py`, `pyproject.toml`, `uv.lock`, `src/build_binary.py`, `README.md` | module files |

Setup, after Task 0 is committed:

```bash
BASE=$(git rev-parse main)
git worktree add ../avatar-seq-structure -b feat/seq-structure "$BASE"
git worktree add ../avatar-seq-import -b feat/seq-import "$BASE"
```

Each agent works only in its worktree, runs its own test file, and verifies
`git branch --show-current` before committing. Merge A, then B, then run the
full suite, then do Task 3 in the main clone, then Task 4. Delete worktrees only
after both branches are merged.

**Recommendation:** for two two-file tasks, sequential execution is simpler and
only slightly slower. Use worktrees only if both modules can proceed at the same
time without waiting on review.
