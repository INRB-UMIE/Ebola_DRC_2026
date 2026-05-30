"""Tests for vector QA date validation."""

import csv
from pathlib import Path

from tools import qa
from tools.lib.schema import parse_filename


def _write_vector(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)


def test_vector_qa_rejects_non_iso_dates(tmp_path: Path, monkeypatch):
    p = tmp_path / "test__cases__daily.csv"
    _write_vector(
        p,
        [
            ["date", "nom", "cases"],
            ["2026-05-29", "Bunia", "1"],
            ["05/30/2026", "Goma", "2"],
        ],
    )
    monkeypatch.setattr(
        qa,
        "to_canonical",
        lambda name: name if name in {"Bunia", "Goma"} else None,
    )

    parsed = parse_filename(p.name)
    assert parsed is not None
    result = qa.qa_vector("test", p, parsed)

    assert result.status == "fail"
    assert any("non-ISO date values" in r for r in result.reasons)
