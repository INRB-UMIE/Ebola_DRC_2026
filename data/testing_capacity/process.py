"""Split wide testing-capacity snapshot into contract vector CSVs.

Reads:
  processed/africa_cdc__testing_capacity__static_matrix.csv

Writes:
  processed/testing_capacity__pcr_machines__static.csv
  processed/testing_capacity__pcr_tests__static.csv

Run from repo root:
    python data/testing_capacity/process.py
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.lib.schema import to_canonical  # noqa: E402

HERE = Path(__file__).resolve().parent
WIDE = HERE / "processed" / "africa_cdc__testing_capacity__static_matrix.csv"
OUT_MACHINES = HERE / "processed" / "testing_capacity__pcr_machines__static.csv"
OUT_TESTS = HERE / "processed" / "testing_capacity__pcr_tests__static.csv"

_DDMMYYYY = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")


def _normalize_date(value: str) -> str:
    value = value.strip()
    m = _DDMMYYYY.match(value)
    if m:
        d, mo, y = m.groups()
        return f"{y}-{mo.zfill(2)}-{d.zfill(2)}"
    return value


def main() -> int:
    if not WIDE.exists():
        raise FileNotFoundError(f"Missing wide snapshot: {WIDE}")

    rows: list[dict[str, str]] = []
    unresolved: list[str] = []
    with WIDE.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            raw_nom = r["nom"].strip()
            canonical = to_canonical(raw_nom)
            if canonical is None:
                unresolved.append(raw_nom)
                canonical = raw_nom
            rows.append({
                "nom": canonical,
                "pcr_machines": r.get("PCR_machines", r.get("pcr_machines", "")).strip(),
                "pcr_tests": r.get("PCR_tests", r.get("pcr_tests", "")).strip(),
            })

    if unresolved:
        print(
            "WARNING: unresolved zone names (add to data/aliases.csv):",
            sorted(set(unresolved)),
            file=sys.stderr,
        )

    OUT_MACHINES.parent.mkdir(parents=True, exist_ok=True)
    with OUT_MACHINES.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["nom", "pcr_machines"])
        for r in rows:
            w.writerow([r["nom"], r["pcr_machines"]])

    with OUT_TESTS.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["nom", "pcr_tests"])
        for r in rows:
            w.writerow([r["nom"], r["pcr_tests"]])

    print(f"wrote {OUT_MACHINES.relative_to(REPO_ROOT)} ({len(rows)} zones)")
    print(f"wrote {OUT_TESTS.relative_to(REPO_ROOT)} ({len(rows)} zones)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
