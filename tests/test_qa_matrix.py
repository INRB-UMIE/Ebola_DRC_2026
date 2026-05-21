"""Tests for matrix QA: missing (NA) cells allowed, invalid values rejected."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from tools.lib.schema import parse_filename
from tools.qa import qa_matrix


def _write_matrix(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)


@pytest.fixture
def tiny_matrix(tmp_path: Path) -> Path:
    # Bunia and Goma are canonical zone names in the shapefile contract.
    p = tmp_path / "test__dist__static.matrix.csv"
    _write_matrix(
        p,
        [
            ["nom", "Bunia", "Goma"],
            ["Bunia", "0", "120"],
            ["Goma", "NA", "0"],
        ],
    )
    return p


def test_matrix_qa_allows_na_cells(tiny_matrix: Path):
    parsed = parse_filename(tiny_matrix.name)
    assert parsed is not None
    result = qa_matrix("test", tiny_matrix, parsed)
    assert result.status == "warn"
    assert any("missing cells" in r for r in result.reasons)


def test_matrix_qa_passes_without_missing_cells(tmp_path: Path):
    p = tmp_path / "test__dist__static.matrix.csv"
    _write_matrix(
        p,
        [
            ["nom", "Bunia", "Goma"],
            ["Bunia", "0", "120"],
            ["Goma", "80", "0"],
        ],
    )
    parsed = parse_filename(p.name)
    result = qa_matrix("test", p, parsed)
    assert result.status == "pass"
    assert not result.reasons


def test_matrix_qa_rejects_negative_values(tmp_path: Path):
    p = tmp_path / "test__dist__static.matrix.csv"
    _write_matrix(
        p,
        [
            ["nom", "Bunia", "Goma"],
            ["Bunia", "0", "-1"],
            ["Goma", "50", "0"],
        ],
    )
    parsed = parse_filename(p.name)
    result = qa_matrix("test", p, parsed)
    assert result.status == "fail"
    assert any("non-numeric or negative" in r for r in result.reasons)


def test_matrix_qa_rejects_non_numeric_garbage(tmp_path: Path):
    p = tmp_path / "test__dist__static.matrix.csv"
    _write_matrix(
        p,
        [
            ["nom", "Bunia", "Goma"],
            ["Bunia", "0", "n/a"],
            ["Goma", "50", "0"],
        ],
    )
    parsed = parse_filename(p.name)
    result = qa_matrix("test", p, parsed)
    assert result.status == "fail"
