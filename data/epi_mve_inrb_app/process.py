"""Process INRB MVE app line list to daily recorded-case counts by zone.

Reads:
  raw/mve_inrb_app_test_line_list.csv
  raw/mve_inrb_app_schema_column_names.csv

Writes:
  processed/epi_mve_inrb_app__recorded_cases__daily.csv

Run from repo root:
  python data/epi_mve_inrb_app/process.py
"""

from __future__ import annotations

import csv
import datetime as dt
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import shapefile  # pyshp  # noqa: E402

from tools.lib.schema import SHAPEFILE, load_zones, to_canonical  # noqa: E402

HERE = Path(__file__).resolve().parent
RAW_LINE_LIST = HERE / "raw" / "mve_inrb_app_test_line_list.csv"
RAW_SCHEMA = HERE / "raw" / "mve_inrb_app_schema_column_names.csv"
OUT_CSV = HERE / "processed" / "epi_mve_inrb_app__recorded_cases__daily.csv"

# Known header typo in the sample raw file.
RAW_HEADER_ALIASES = {
    "PROSTATION": "PROSTRATION",
}


def _parse_date(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        raise ValueError("empty date_of_notification")
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"unsupported date format: {value!r}")


def _parse_float(raw: str | None) -> float | None:
    if raw is None:
        return None
    value = raw.strip().replace(",", ".")
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _load_schema_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    with RAW_SCHEMA.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            fr = (row.get("column_name_fr") or "").strip()
            en = (row.get("column_name_en") or "").strip()
            if fr and en:
                mapping[fr] = en
    if not mapping:
        raise RuntimeError(f"No column mappings read from {RAW_SCHEMA}")
    return mapping


def _rename_row(row: dict[str, str], mapping: dict[str, str]) -> dict[str, str]:
    renamed: dict[str, str] = {}
    for key, value in row.items():
        if key is None:
            continue
        source_key = RAW_HEADER_ALIASES.get(key, key)
        out_key = mapping.get(source_key, source_key.lower())
        # Keep first value when duplicate mapped names appear.
        if out_key not in renamed:
            renamed[out_key] = value
    return renamed


def _point_in_ring(x: float, y: float, ring: list[tuple[float, float]]) -> bool:
    """Even-odd ray casting for one polygon ring."""
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        intersects = ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / ((yj - yi) if (yj - yi) != 0 else 1e-20) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def _shape_contains_lonlat(shp: shapefile.Shape, lon: float, lat: float) -> bool:
    xmin, ymin, xmax, ymax = shp.bbox
    if not (xmin <= lon <= xmax and ymin <= lat <= ymax):
        return False

    # Multi-part polygons: apply even-odd rule across all rings.
    parts = list(shp.parts) + [len(shp.points)]
    inside = False
    for i in range(len(parts) - 1):
        ring = shp.points[parts[i] : parts[i + 1]]
        if len(ring) >= 3 and _point_in_ring(lon, lat, ring):
            inside = not inside
    return inside


def _load_zone_locator() -> list[tuple[str, shapefile.Shape]]:
    reader = shapefile.Reader(str(SHAPEFILE))
    zones = load_zones()
    zone_shapes: list[tuple[str, shapefile.Shape]] = []
    for zone, shp in zip(zones, reader.shapes()):
        zone_shapes.append((zone.canonical_nom, shp))
    return zone_shapes


def _zone_from_point(lat: float, lon: float, zone_shapes: list[tuple[str, shapefile.Shape]]) -> str | None:
    for nom, shp in zone_shapes:
        if _shape_contains_lonlat(shp, lon=lon, lat=lat):
            return nom
    return None


def main() -> int:
    mapping = _load_schema_map()
    zone_shapes = _load_zone_locator()

    counts: dict[tuple[str, str], int] = defaultdict(int)
    unresolved_rows: list[str] = []
    skipped_bad_date: list[str] = []

    with RAW_LINE_LIST.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for line_number, raw_row in enumerate(reader, start=2):
            row = _rename_row(raw_row, mapping)

            try:
                date_iso = _parse_date(row.get("date_of_notification", ""))
            except ValueError:
                skipped_bad_date.append(
                    f"line {line_number}: date_of_notification={row.get('date_of_notification', '')!r}"
                )
                continue
            observed_zone = (row.get("health_zone") or "").strip()
            canonical = to_canonical(observed_zone)

            if canonical is None:
                lat = _parse_float(row.get("latitude"))
                lon = _parse_float(row.get("longitude"))
                if lat is not None and lon is not None:
                    canonical = _zone_from_point(lat, lon, zone_shapes)

            if canonical is None:
                unresolved_rows.append(
                    f"line {line_number}: health_zone={observed_zone!r}, "
                    f"lat={row.get('latitude', '')!r}, lon={row.get('longitude', '')!r}"
                )
                continue

            counts[(canonical, date_iso)] += 1

    if unresolved_rows:
        sample = "\n".join(unresolved_rows[:10])
        raise RuntimeError(
            "Could not resolve health zone for one or more rows. "
            "Add aliases in data/aliases.csv or ensure valid coordinates.\n"
            f"Sample rows:\n{sample}"
        )

    if skipped_bad_date:
        print(
            f"WARNING: skipped {len(skipped_bad_date)} rows with invalid/empty date_of_notification",
            file=sys.stderr,
        )

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["nom", "date", "recorded_cases"])
        for nom, date_iso in sorted(counts.keys(), key=lambda x: (x[1], x[0])):
            writer.writerow([nom, date_iso, counts[(nom, date_iso)]])

    print(f"wrote {OUT_CSV.relative_to(REPO_ROOT)} ({len(counts)} nom-date rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
