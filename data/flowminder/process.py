"""Rewrite the raw Flowminder OD matrices into contract-compliant snapshot matrices.

Reads raw/mobilite_od_matrix_{inflow,outflow}_mar2026.csv and writes
processed/flowminder__{inflow,outflow}__static.matrix.csv with:
  - first column header 'origin' renamed to 'nom'
  - cell labels alias-resolved to canonical Nom (via tools/lib/schema.to_canonical)
  - the bare 'Lubunga' label disambiguated to 'Lubunga (Tshopo)' (flowminder coverage
    is Ituri / Nord-Kivu / Haut-Uele / western Tshopo, per README.md)

Run from repo root:
    python -m data.flowminder.process
or directly:
    python data/flowminder/process.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.lib.schema import to_canonical  # noqa: E402

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
PROCESSED = HERE / "processed"

# Flowminder coverage area means 'Lubunga' here refers to the Tshopo zone, not
# the Kasaï-Central one. Disambiguate locally; we deliberately do NOT add this
# to data/aliases.csv because it would mislabel a future Kasaï-Central dataset.
LOCAL_FIXUPS = {"Lubunga": "Lubunga (Tshopo)"}


def _resolve(label: str) -> str:
    fixed = LOCAL_FIXUPS.get(label.strip(), label.strip())
    canonical = to_canonical(fixed)
    if canonical is None:
        raise ValueError(f"flowminder: unresolved name {label!r} (after fixups: {fixed!r})")
    return canonical


def rewrite(direction: str) -> Path:
    src = RAW / f"mobilite_od_matrix_{direction}_mar2026_flowminder.csv"
    dst = PROCESSED / f"flowminder__{direction}__static.matrix.csv"
    with src.open(newline="", encoding="utf-8-sig") as f_in:
        reader = csv.reader(f_in)
        header = next(reader)
        rows = list(reader)
    if header[0] != "origin":
        raise ValueError(f"flowminder: expected first header 'origin', got {header[0]!r}")
    new_header = ["nom"] + [_resolve(h) for h in header[1:]]
    new_rows = [[_resolve(r[0])] + r[1:] for r in rows]
    dst.parent.mkdir(exist_ok=True)
    with dst.open("w", newline="", encoding="utf-8") as f_out:
        w = csv.writer(f_out)
        w.writerow(new_header)
        w.writerows(new_rows)
    return dst


def main() -> int:
    for direction in ("inflow", "outflow"):
        out = rewrite(direction)
        print(f"wrote {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
