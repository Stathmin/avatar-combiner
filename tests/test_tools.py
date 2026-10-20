import pytest

import tools


def test_dna_operations_use_biopython():
    assert tools.complement('ATGC') == 'TACG'
    assert tools.reverse_complement('ATGC') == 'GCAT'
    assert tools.reverse('ATGC') == 'CGTA'
    assert tools.gc_content('ATGC') == 50.0


def test_iupac_letters_are_supported():
    assert tools.complement('RYSWKMBDHVN') == 'YRSWMKVHDBN'
    assert tools.reverse_complement('ATGCryswkmbdhvn') == 'NBDHVKMWSRYGCAT'


def test_invalid_dna_is_rejected():
    with pytest.raises(tools.ToolError):
        tools.normalize_dna('ATXG')
    with pytest.raises(tools.ToolError):
        tools.normalize_primer('ATGCN')


def test_unit_conversion_uses_pint():
    assert tools.convert(25, 'uM', 'nM') == pytest.approx(25000)
    assert tools.convert(1, 'ug', 'ng') == pytest.approx(1000)
    assert tools.convert(1, 'kb', 'bp') == pytest.approx(1000)
    assert tools.convert(100, 'C', 'F') == pytest.approx(212)
    assert tools.convert(0, 'C', 'K') == pytest.approx(273.15)


def test_convert_text_target_and_listing():
    assert tools.convert_text('25 uM', 'nM')[0][0] == 'nM'
    assert tools.convert_text('25 uM', 'nM')[0][1] == pytest.approx(25000)
    assert tools.convert_text('100 C', 'F')[0] == ('F', pytest.approx(212))

    mass = dict(tools.convert_text('1 ug'))
    assert mass['ng'] == pytest.approx(1000)
    assert mass['mg'] == pytest.approx(0.001)


def test_cross_category_conversion_is_rejected():
    with pytest.raises(tools.ToolError):
        tools.convert(1, 'ug', 'nM')


def test_primer_analysis_uses_primer3():
    report = tools.analyze_primer('GTAAAACGACGGCCAGT')

    assert report.sequence == 'GTAAAACGACGGCCAGT'
    assert report.length == 17
    assert report.gc == pytest.approx(52.941, rel=1e-3)
    assert report.tm == pytest.approx(54.695, rel=1e-3)
    assert hasattr(report.hairpin, 'tm')
    assert hasattr(report.homodimer, 'dg')


def test_primer_pair_analysis():
    report = tools.analyze_pair('GTAAAACGACGGCCAGT', 'GCGTACGTAGCTAGCTA')

    assert report.forward.tm == pytest.approx(54.695, rel=1e-3)
    assert report.reverse.tm > 0
    assert hasattr(report.heterodimer, 'dg')
    assert hasattr(report.end_stability, 'dg')
