"""Build short-trip outflow proportion matrices from Annex A extract.

Inputs:
  raw/short_trips_destination_rankings.csv  (from extract_pdf_annex.py)

Outputs (static snapshot matrices, one per observation date):
  processed/flowminder_short_trips__outflow_20260430__static.matrix.csv  (D+7 / 30 Apr)
  processed/flowminder_short_trips__outflow_20260507__static.matrix.csv  (D+14 / 7 May)
  processed/flowminder_short_trips__outflow_20260514__static.matrix.csv  (D+21 / 14 May)
  processed/flowminder_short_trips__outflow_20260521__static.matrix.csv  (D+28 / 21 May)
  processed/flowminder_short_trips__outflow_20260524__static.matrix.csv  (D+31 / 24 May)

Each file has three origin rows (Bunia, Mongbalu, Rwampara) and destination columns taken
from the ranked health-zone list. Values are the cohort proportion (%) for that date;
the three origin rows carry identical values (combined Bunia + Mongbwalu + Rwampara cohort).

Run from repo root:
    python data/flowminder_short_trips/extract_pdf_annex.py
    python data/flowminder_short_trips/process.py
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
ALIASES_CSV = DATA_DIR / "aliases.csv"
FLOWMINDER_OUTFLOW = DATA_DIR / "flowminder" / "processed" / "flowminder__outflow__static.matrix.csv"

HERE = Path(__file__).resolve().parent
RAW_CSV = HERE / "raw" / "short_trips_destination_rankings.csv"
PROCESSED = HERE / "processed"
LOG_CSV = HERE / "zone_resolution_log.csv"

ORIGINS = ("Bunia", "Mongbalu", "Rwampara")

SNAPSHOTS: tuple[tuple[str, str, str], ...] = (
    ("d7", "date_d7", "20260430"),
    ("d14", "date_d14", "20260507"),
    ("d21", "date_d21", "20260514"),
    ("d28", "date_d28", "20260521"),
    ("d31", "date_d31", "20260524"),
)

# Mirrors data/flowminder/process.py (verified against shapefile Nom).
DISAMBIGUATION: dict[str, str] = {
    "Lubunga": "Lubunga (Tshopo)",
    "Bili": "Bili (Bas-Uele)",
}
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
    "Mongbwalu": "Mongbalu",
    "Makiso Kisangani": "Makiso-Kisangani",
    "Nia Nia": "Nia-Nia",
    "Kasa Vubu": "Kasa-Vubu",
    "Mont Ngafula 1": "Mont Ngafula I",
    "Mont Ngafula 2": "Mont Ngafula II",
    "Masina 1": "Masina I",
    "Masina 2": "Masina II",
    "Kalamu 1": "Kalamu I",
    "Kalamu 2": "Kalamu II",
    "Maluku 1": "Maluku I",
    "Maluku 2": "Maluku II",
    "Ngiri Ngiri": "Ngiri-Ngiri",
}
LOCAL_FIXUPS: dict[str, str] = {**DISAMBIGUATION, **TYPO_FIXUPS}
_ROMAN_RE = re.compile(r"^(.*) ([12])$")


def _load_canonical_noms() -> frozenset[str]:
    if not FLOWMINDER_OUTFLOW.exists():
        raise FileNotFoundError(
            f"Need canonical zone list from {FLOWMINDER_OUTFLOW} "
            "(run data/flowminder/process.py first)."
        )
    names: set[str] = set()
    with FLOWMINDER_OUTFLOW.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        names.update(h for h in header if h != "nom")
        for row in reader:
            if row:
                names.add(row[0])
    return frozenset(names)


def _load_alias_index(canon: frozenset[str]) -> dict[str, str]:
    index: dict[str, str] = {}
    if not ALIASES_CSV.exists():
        return index
    with ALIASES_CSV.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            observed = (row.get("observed_name") or "").strip()
            canonical = (row.get("canonical_nom") or "").strip()
            if observed and canonical and canonical in canon:
                index[observed] = canonical
    return index


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


def _resolve(label: str, canon: frozenset[str], aliases: dict[str, str]) -> str | None:
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
        if candidate in canon:
            return candidate
        if candidate in aliases:
            return aliases[candidate]
    return None


def _read_extract(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _build_snapshot(
    rows: list[dict[str, str]],
    value_col: str,
    canon: frozenset[str],
    aliases: dict[str, str],
) -> tuple[list[str], dict[str, float], list[dict[str, str]]]:
    dest_order: list[str] = []
    dest_values: dict[str, float] = {}
    log: list[dict[str, str]] = []
    seen: set[str] = set()

    for row in rows:
        raw_zone = (row.get("health_zone") or "").strip()
        label = f"{row.get('province', '').strip()} {raw_zone}".strip()
        canonical = _resolve(raw_zone, canon, aliases)
        if canonical is None:
            log.append(
                {
                    "raw_label": raw_zone,
                    "province": row.get("province", ""),
                    "action": "dropped",
                    "reason": "no shapefile Nom or alias match",
                }
            )
            continue
        if canonical in seen:
            log.append(
                {
                    "raw_label": raw_zone,
                    "province": row.get("province", ""),
                    "action": "merged",
                    "reason": f"duplicate canonical {canonical!r}",
                }
            )
            continue
        seen.add(canonical)
        dest_order.append(canonical)
        dest_values[canonical] = float(row[value_col])

    return dest_order, dest_values, log


def _write_matrix(
    dest_order: list[str],
    dest_values: dict[str, float],
    out_path: Path,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["nom"] + dest_order)
        for origin in ORIGINS:
            w.writerow([origin] + [dest_values[d] for d in dest_order])


def _assert_canonical(path: Path, canon: frozenset[str]) -> None:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        bad = [h for h in header if h != "nom" and h not in canon]
        for row in reader:
            if row and row[0] not in canon:
                bad.append(row[0])
    if bad:
        sample = ", ".join(sorted(set(bad))[:10])
        raise ValueError(f"{path.name}: non-canonical zone names: {sample}")


def main() -> int:
    if not RAW_CSV.exists():
        raise FileNotFoundError(
            f"Missing {RAW_CSV.name}; run extract_pdf_annex.py first."
        )

    canon = _load_canonical_noms()
    aliases = _load_alias_index(canon)
    rows = _read_extract(RAW_CSV)
    all_logs: list[dict[str, str]] = []

    for value_col, _date_col, date_tag in SNAPSHOTS:
        dest_order, dest_values, log = _build_snapshot(rows, value_col, canon, aliases)
        if not dest_order:
            raise RuntimeError(f"No destinations resolved for snapshot {date_tag}")
        out = PROCESSED / f"flowminder_short_trips__outflow_{date_tag}__static.matrix.csv"
        _write_matrix(dest_order, dest_values, out)
        _assert_canonical(out, canon)
        all_logs.extend({**entry, "snapshot": date_tag} for entry in log)
        print(
            f"wrote {out.relative_to(REPO_ROOT)} "
            f"({len(ORIGINS)} origins × {len(dest_order)} destinations)"
        )

    if all_logs:
        with LOG_CSV.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f,
                fieldnames=["snapshot", "raw_label", "province", "action", "reason"],
            )
            w.writeheader()
            w.writerows(all_logs)
        print(f"wrote {LOG_CSV.relative_to(REPO_ROOT)} ({len(all_logs)} events)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
