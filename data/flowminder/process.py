"""Rewrite the raw Flowminder OD matrices into contract-compliant snapshot matrices.

Convention
----------
Processed row/column labels MUST match the canonical health-zone names defined by
``data/shapefiles/DRC_Health_zones.shp`` (field ``Nom``), using the same rules as
``tools.lib.schema``:

  - unique ``Nom`` values are used as-is (e.g. ``Bunia``, ``Goma``);
  - duplicate ``Nom`` across provinces are disambiguated as ``Nom (Province)``
    (e.g. ``Bili (Bas-Uele)``, ``Lubunga (Tshopo)``).

Resolution order for each raw Flowminder label:

  1. ``data/aliases.csv`` (via ``to_canonical``) — shared repo aliases
  2. Structural variants — roman numerals (``Kalamu 1`` → ``Kalamu I``) and
     spaces → hyphens (``Kasa Vubu`` → ``Kasa-Vubu``)
  3. ``LOCAL_FIXUPS`` below — Flowminder HDX typos / province disambiguation,
     each target verified against the shapefile at import time

Labels that still do not resolve are dropped; see ``zone_resolution_log.csv``.

Inputs (``raw/``):
  mobilite_od_matrix_{inflow,outflow}_mar2026_flowminder.csv

Outputs (``processed/``):
  flowminder__{inflow,outflow}__static.matrix.csv  (first column header ``nom``)

Run from the data repository root:
    python -m data.flowminder.process
or:
    python data/flowminder/process.py
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SHAPEFILE = REPO_ROOT / "data" / "shapefiles" / "DRC_Health_zones"
sys.path.insert(0, str(REPO_ROOT))

from tools.lib.schema import canonical_noms, to_canonical  # noqa: E402

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
PROCESSED = HERE / "processed"

# Province disambiguation for bare labels that collide in the shapefile.
DISAMBIGUATION: dict[str, str] = {
    "Lubunga": "Lubunga (Tshopo)",
    "Bili": "Bili (Bas-Uele)",
}

# HDX / Flowminder spelling variants verified against DRC_Health_zones.shp Nom.
TYPO_FIXUPS: dict[str, str] = {
    "Banzow Moke": "Banjow Moke",
    "Bena Tshadi": "Bena Tshiadi",
    "Bogosenubea": "Bogosenubia",
    "Busanga": "Bosanga",
    "Djalo Ndjeka": "Djalo Djeka",
    "Kabeya Kamwanga": "Kabeya Kamuanga",
    "Kimbao": "Kimbau",
    "Malemba Nkulu": "Malemba",
    "Mampoko": "Lolanga Mampoko",
    "Massa": "Masa",
    "Muanda": "Moanda",
    "Mweneditu": "Mwene Ditu",
    "Ruashi": "Rwashi",
}

LOCAL_FIXUPS: dict[str, str] = {**DISAMBIGUATION, **TYPO_FIXUPS}

_ROMAN_RE = re.compile(r"^(.*) ([12])$")


def _validate_fixup_targets() -> None:
    canon = canonical_noms()
    for observed, target in LOCAL_FIXUPS.items():
        if target not in canon:
            raise ValueError(
                f"flowminder LOCAL_FIXUPS[{observed!r}] -> {target!r} "
                f"is not a canonical shapefile Nom (see {SHAPEFILE})"
            )


def _structural_variants(label: str) -> list[str]:
    out: list[str] = []
    m = _ROMAN_RE.match(label)
    if m:
        base, digit = m.group(1), m.group(2)
        roman = "I" if digit == "1" else "II"
        out.append(f"{base} {roman}")
        out.append(f"{base}-{roman}")
    if " " in label:
        out.append(label.replace(" ", "-"))
    return out


def _resolve(label: str) -> str | None:
    stripped = label.strip()
    if not stripped:
        return None

    candidates = [stripped]
    if stripped in LOCAL_FIXUPS:
        candidates.insert(0, LOCAL_FIXUPS[stripped])
    candidates.extend(_structural_variants(stripped))

    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        canonical = to_canonical(candidate)
        if canonical is not None:
            return canonical
    return None


def _parse_flow(value: str) -> float:
    try:
        return float(value)
    except ValueError:
        return 0.0


def rewrite(direction: str) -> tuple[Path, list[dict[str, str]]]:
    src = RAW / f"mobilite_od_matrix_{direction}_mar2026_flowminder.csv"
    dst = PROCESSED / f"flowminder__{direction}__static.matrix.csv"
    log: list[dict[str, str]] = []

    with src.open(newline="", encoding="utf-8-sig") as f_in:
        reader = csv.reader(f_in)
        header = next(reader)
        rows = list(reader)

    if header[0] != "origin":
        raise ValueError(f"flowminder: expected first header 'origin', got {header[0]!r}")

    dest_raw = header[1:]
    dest_canon: list[str | None] = []
    dest_order: list[str] = []
    dest_seen: set[str] = set()
    for raw in dest_raw:
        canon = _resolve(raw)
        dest_canon.append(canon)
        if canon is None:
            log.append(
                {
                    "direction": direction,
                    "raw_label": raw,
                    "role": "destination",
                    "action": "dropped",
                    "reason": "no shapefile Nom or alias match",
                }
            )
            continue
        if canon in dest_seen:
            log.append(
                {
                    "direction": direction,
                    "raw_label": raw,
                    "role": "destination",
                    "action": "merged",
                    "reason": f"duplicate of {canon!r}",
                }
            )
            continue
        dest_seen.add(canon)
        dest_order.append(canon)

    agg: dict[str, dict[str, float]] = {}
    for row in rows:
        if len(row) != len(header):
            raise ValueError(f"flowminder: row width {len(row)} != header {len(header)}")
        origin_raw = row[0]
        origin_canon = _resolve(origin_raw)
        if origin_canon is None:
            log.append(
                {
                    "direction": direction,
                    "raw_label": origin_raw,
                    "role": "origin",
                    "action": "dropped",
                    "reason": "no shapefile Nom or alias match",
                }
            )
            continue
        if origin_canon not in agg:
            agg[origin_canon] = {d: 0.0 for d in dest_order}
        for raw_dest, canon, value in zip(dest_raw, dest_canon, row[1:]):
            if canon is None or canon not in agg[origin_canon]:
                continue
            agg[origin_canon][canon] += _parse_flow(value)

    origin_order = sorted(agg.keys())
    dst.parent.mkdir(exist_ok=True)
    with dst.open("w", newline="", encoding="utf-8") as f_out:
        w = csv.writer(f_out)
        w.writerow(["nom"] + dest_order)
        for origin in origin_order:
            w.writerow([origin] + [agg[origin][d] for d in dest_order])

    _assert_shapefile_convention(dst)
    return dst, log


def _assert_shapefile_convention(path: Path) -> None:
    """Every nom in a processed matrix must be a canonical shapefile label."""
    canon = canonical_noms()
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        bad = [label for label in header if label != "nom" and label not in canon]
        for row in reader:
            if row and row[0] not in canon:
                bad.append(row[0])
    if bad:
        sample = ", ".join(sorted(set(bad))[:10])
        raise ValueError(
            f"flowminder: {path.name} contains non-canonical zone names: {sample}"
        )


def write_resolution_log(logs: list[dict[str, str]]) -> Path:
    path = HERE / "zone_resolution_log.csv"
    fields = ["direction", "raw_label", "role", "action", "reason"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(logs)
    return path


def main() -> int:
    _validate_fixup_targets()
    all_logs: list[dict[str, str]] = []
    for direction in ("inflow", "outflow"):
        out, log = rewrite(direction)
        all_logs.extend(log)
        print(f"wrote {out.relative_to(REPO_ROOT)} ({out.stat().st_size} bytes)")
    if all_logs:
        log_path = write_resolution_log(all_logs)
        print(f"wrote {log_path.relative_to(REPO_ROOT)} ({len(all_logs)} resolution events)")
    else:
        print("all raw labels resolved to shapefile canonical Nom")
    return 0


if __name__ == "__main__":
    sys.exit(main())
