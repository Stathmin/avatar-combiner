import math

import pytest
import seqfold

import seq_structure
import tools


def test_structured_sequence_reports_energy_and_fold():
    report = seq_structure.analyze_structure('ACGTACGTACGT')

    assert report.sequence == 'ACGTACGTACGT'
    assert report.dot_bracket == '((((....))))'
    assert report.dg == pytest.approx(-1.7, abs=0.3)
    assert report.tm == pytest.approx(43.4, abs=0.3)
    assert len(report.hits) >= 1
    assert all(math.isfinite(hit.energy) for hit in report.hits)


def test_short_sequence_is_sanitized():
    report = seq_structure.analyze_structure('ATGC')

    assert report.dg is None
    assert report.tm is None
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


def test_single_base_oligo_raises_tool_error():
    with pytest.raises(tools.ToolError, match='cannot fold sequence'):
        seq_structure.analyze_structure('A')


def test_malformed_dot_bracket_characters_are_sanitized(monkeypatch):
    monkeypatch.setattr(seqfold, 'dot_bracket', lambda sequence, folded: 'x' * len(sequence))

    report = seq_structure.analyze_structure('ACGTACGTACGT')

    assert report.dot_bracket == '.' * len('ACGTACGTACGT')
