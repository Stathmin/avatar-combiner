import tool_reports
import tools


def test_primer_rows_use_shared_keys():
    report = tools.analyze_primer('GTAAAACGACGGCCAGT')
    rows = dict(tool_reports.primer_rows(report))

    assert rows['sequence'] == 'GTAAAACGACGGCCAGT'
    assert rows['length'] == '17 nt'
    assert rows['tm'].endswith('°C')
    assert 'hairpin' in rows and 'homodimer' in rows


def test_dna_rows_are_computed_once():
    rows = dict(tool_reports.dna_rows('ATGC'))

    assert rows['length'] == '4 nt'
    assert rows['complement'] == 'TACG'
    assert rows['reverse_seq'] == 'CGTA'
    assert rows['reverse_complement'] == 'GCAT'


def test_unit_rows_match_cli_format():
    assert tool_reports.unit_rows('25 uM', 'nM') == [('nM', '25000')]
