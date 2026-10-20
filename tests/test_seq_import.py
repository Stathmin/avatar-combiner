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
    record.annotations['molecule_type'] = 'DNA'
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
