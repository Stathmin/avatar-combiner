import json
import shutil
from pathlib import Path

import pytest

import run_pipeline

SRC = Path(__file__).resolve().parents[1] / "src"
OUTPUT_FILES = (
    "plate1.csv",
    "plate2.csv",
    "plate3.csv",
    "plate4.csv",
    "metadata.csv",
    "combined_384_plate.csv",
    "combined_384_plate_pivot.csv",
    "combined_384_plate_ids.txt",
)


def prepare_input(tmp_path):
    shutil.copy(SRC / "планшеты соя пробелы.xlsx", tmp_path / "планшеты соя пробелы.xlsx")


def test_first_run_uses_result_one(tmp_path):
    result_dir = run_pipeline.create_result_dir(tmp_path)

    assert result_dir == tmp_path / "Результат 1"
    assert result_dir.is_dir()


def test_next_run_increments_result_number(tmp_path):
    for folder in ("Результат 1", "Результат 3", "Другое"):
        (tmp_path / folder).mkdir()

    assert run_pipeline.create_result_dir(tmp_path).name == "Результат 4"


@pytest.mark.parametrize("run_number", [1, 2])
def test_pipeline_keeps_outputs_out_of_program_root(tmp_path, run_number):
    prepare_input(tmp_path)

    for _ in range(run_number):
        run_pipeline.run(tmp_path)

    result_dir = tmp_path / f"Результат {run_number}"
    for name in OUTPUT_FILES:
        assert (result_dir / name).is_file()

    ids = (result_dir / "combined_384_plate_ids.txt").read_text(encoding="utf-8").splitlines()
    assert len(ids) == 384

    manifest = json.loads((result_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"]
    assert len(manifest["sheets"]) == 4
    assert manifest["excel_path"].endswith(".xlsx")
    assert manifest["data_range"]["start_row"] == 3

    for name in OUTPUT_FILES:
        assert not (tmp_path / name).exists()
