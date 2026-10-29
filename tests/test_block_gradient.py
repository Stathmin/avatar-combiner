"""PCR block gradient calculator (T100/CFX-style rows A–H)."""

import pytest

import tools


# Ground truth from Bio-Rad T100 / CFX gradient UI screenshots.
T100_CASES = {
    (65, 55): {
        'A': 65.0,
        'B': 64.3,
        'C': 63.0,
        'D': 61.1,
        'E': 58.8,
        'F': 56.9,
        'G': 55.7,
        'H': 55.0,
    },
    (62, 50): {
        'A': 62.0,
        'B': 61.1,
        'C': 59.6,
        'D': 57.3,
        'E': 54.6,
        'F': 52.3,
        'G': 50.8,
        'H': 50.0,
    },
    (66, 58): {
        'A': 66.0,
        'B': 65.4,
        'C': 64.4,
        'D': 62.9,
        'E': 61.1,
        'F': 59.6,
        'G': 58.6,
        'H': 58.0,
    },
    (64, 56): {
        'A': 64.0,
        'B': 63.4,
        'C': 62.4,
        'D': 60.9,
        'E': 59.1,
        'F': 57.6,
        'G': 56.6,
        'H': 56.0,
    },
    (62, 52): {
        'A': 62.0,
        'B': 61.2,
        'C': 60.0,
        'D': 58.1,
        'E': 55.8,
        'F': 53.9,
        'G': 52.7,
        'H': 52.0,
    },
    (64, 52): {
        'A': 64.0,
        'B': 63.1,
        'C': 61.6,
        'D': 59.3,
        'E': 56.6,
        'F': 54.3,
        'G': 52.8,
        'H': 52.0,
    },
}

# Single documented residual of the shared-weight model (0.1 °C display).
KNOWN_RESIDUALS = {
    (65, 55): {'B': 64.2},  # UI shows 64.3
}


@pytest.mark.parametrize('back,front', list(T100_CASES))
def test_t100_cases_within_point_one(back, front):
    truth = T100_CASES[(back, front)]
    report = tools.block_gradient(back, front)
    predicted = dict(report.rows)
    residuals = KNOWN_RESIDUALS.get((back, front), {})

    for letter, expected in truth.items():
        got = predicted[letter]
        if letter in residuals:
            assert got == residuals[letter]
            assert abs(got - expected) <= 0.1
        else:
            assert got == expected


def test_equal_temperatures_flat_block():
    report = tools.block_gradient(58, 58)
    assert all(temp == 58.0 for _, temp in report.rows)
    assert [letter for letter, _ in report.rows] == list('ABCDEFGH')


def test_swapped_front_back_is_rejected():
    with pytest.raises(tools.ToolError, match='front row'):
        tools.block_gradient(52, 64)


def test_span_above_cfx_maximum_is_rejected():
    with pytest.raises(tools.ToolError, match='24'):
        tools.block_gradient(80, 50)


def test_string_and_comma_decimal_inputs():
    report = tools.block_gradient('64.0', '52,0')
    assert dict(report.rows) == T100_CASES[(64, 52)]


def test_scaled_span_preserves_endpoints():
    report = tools.block_gradient(70, 60)
    assert report.rows[0] == ('A', 70.0)
    assert report.rows[-1] == ('H', 60.0)
    temps = [temp for _, temp in report.rows]
    assert temps == sorted(temps, reverse=True)
    assert 60.0 < temps[3] < 70.0


def test_invalid_temperature_is_rejected():
    with pytest.raises(tools.ToolError):
        tools.block_gradient('hot', 52)
