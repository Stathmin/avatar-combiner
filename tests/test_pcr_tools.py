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


def test_product_excludes_flanking_sequence():
    report = pcr_tools.simulate_pcr('TTTT' + TEMPLATE + 'GGGG', FORWARD, REVERSE)

    assert report.length == 200
    assert report.sequence == TEMPLATE


def test_no_product_is_a_tool_error():
    with pytest.raises(tools.ToolError, match='no PCR product') as exc_info:
        pcr_tools.simulate_pcr(TEMPLATE, 'A' * 20, 'T' * 20)

    cause = exc_info.value.__cause__
    assert isinstance(cause, ValueError)
    assert 'PCR' in str(cause).splitlines()[0]


def test_circular_must_be_boolean():
    with pytest.raises(tools.ToolError, match='circular must be True or False'):
        pcr_tools.simulate_pcr(TEMPLATE, FORWARD, REVERSE, circular='yes')


def test_rna_template_is_rejected():
    with pytest.raises(tools.ToolError, match=r'unsupported base\(s\): U'):
        pcr_tools.simulate_pcr(TEMPLATE.replace('T', 'U', 1), FORWARD, REVERSE)
