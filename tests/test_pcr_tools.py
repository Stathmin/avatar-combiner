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
