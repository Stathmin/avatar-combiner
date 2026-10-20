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


def test_meta_path_is_not_a_condition(tmp_path):
    (tmp_path / 'plate.csv').write_text('', encoding='utf-8')
    path = tmp_path / 'meta.toml'
    write_toml(
        path,
        '[meta]\npath = "plate.csv"\n\n[well.A1]\nsample = "soy1"\n\n[well.B1]\nsample = "soy2"\n',
    )

    report = plate_layout.load_layout(path)

    assert report.wells == 2
    assert report.conditions == ('sample',)


def test_invalid_well_is_wrapped(tmp_path):
    path = tmp_path / 'bad.toml'
    write_toml(path, '[well.ZZ]\nsample = "x"\n')

    with pytest.raises(
        tools.ToolError, match=r"cannot read bad\.toml: .*Cannot parse well 'ZZ'"
    ):
        plate_layout.load_layout(path)


def test_missing_file_is_rejected(tmp_path):
    with pytest.raises(tools.ToolError, match='file not found'):
        plate_layout.load_layout(tmp_path / 'missing.toml')
