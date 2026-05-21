"""Build merged GeoJSON + manifest from QA-passing non-matrix outputs.

Outputs:
  build/drc_health_zones.geojson  — shapefile geometry merged with latest
                                     per-zone values from every passing vector file.
                                     Property layout:
                                       feature.properties.nom        canonical Nom
                                       feature.properties.zscode     shapefile ZSCode
                                       feature.properties.province   shapefile PROVINCE
                                       feature.properties.<dataset>.<metric> = {
                                         <value_col_1>: ..., <value_col_2>: ...,
                                         _date: <ISO date>     (time-series only)
                                       }
                                     <dataset> here is the filename's lower_snake_case
                                     token (e.g. "cross_border", "idp"), not the folder
                                     name. See manifest.json for the folder<->token map.
  build/long/<dataset>__<metric>.csv — full long-format copy of each vector file.
  build/manifest.json — what's in the build, per-folder source metadata, build timestamp.

Matrices are deliberately NOT embedded; consumers fetch them as raw CSVs using
qa/matrix_log.csv as the catalog.

Run from repo root:
    python -m tools.build_geojson
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import shapefile  # pyshp
import yaml

from tools.lib.schema import (
    REPO_ROOT,
    SHAPEFILE,
    load_zones,
    parse_filename,
    to_canonical,
)

DATA_DIR = REPO_ROOT / "data"
QA_LOG = REPO_ROOT / "qa" / "qa_log.csv"
BUILD_DIR = REPO_ROOT / "build"
LONG_DIR = BUILD_DIR / "long"
GEOJSON_OUT = BUILD_DIR / "drc_health_zones.geojson"
MANIFEST_OUT = BUILD_DIR / "manifest.json"

DATE_COLUMN_CANDIDATES = ("date", "week_start", "month_start", "year")


def _coerce(value: str):
    """int -> float -> str fallback. Empty -> None."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def _read_qa_log() -> list[dict]:
    with QA_LOG.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _read_metadata(folder: Path) -> dict:
    p = folder / "metadata.yaml"
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def _load_features() -> tuple[list[dict], dict[str, dict]]:
    reader = shapefile.Reader(str(SHAPEFILE))
    zones = load_zones()
    features: list[dict] = []
    by_nom: dict[str, dict] = {}
    for zone, sh in zip(zones, reader.shapes()):
        feat = {
            "type": "Feature",
            "geometry": sh.__geo_interface__,
            "properties": {
                "nom": zone.canonical_nom,
                "zscode": zone.zscode,
                "province": zone.province,
            },
        }
        features.append(feat)
        # Multiple shapefile features can share the same canonical Nom in
        # principle (none currently do after disambiguation), so map by zscode-
        # keyed dict to avoid collision. For attaching dataset values we still
        # key by canonical Nom because dataset outputs use Nom only.
        by_nom[zone.canonical_nom] = feat
    return features, by_nom


def _attach_vector(folder: Path, file_name: str, parsed, features_by_nom: dict[str, dict]) -> int:
    src = folder / "processed" / file_name
    with src.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    date_col = next((c for c in DATE_COLUMN_CANDIDATES if c in fieldnames), None)
    # Skip empty-header columns (R's write.csv row-index artifact) so they
    # don't end up as stray "" keys in feature properties.
    value_cols = [c for c in fieldnames if c and c != "nom" and c != date_col]

    # For time-series: pick latest row per canonical nom.
    latest_per_nom: dict[str, dict] = {}
    for r in rows:
        canonical = to_canonical(r["nom"])
        if canonical is None:
            continue
        if date_col:
            existing = latest_per_nom.get(canonical)
            # Lexical string comparison is safe here because the contract
            # requires ISO 8601 dates (YYYY-MM-DD or YYYY), which sort
            # correctly as strings. Don't relax this without parsing.
            if existing is None or r[date_col] > existing[date_col]:
                latest_per_nom[canonical] = r
        else:
            latest_per_nom[canonical] = r

    dataset_token = parsed.dataset
    metric = parsed.metric
    attached = 0
    for nom, r in latest_per_nom.items():
        feat = features_by_nom.get(nom)
        if feat is None:
            continue
        ds_bucket = feat["properties"].setdefault(dataset_token, {})
        value_obj = {c: _coerce(r[c]) for c in value_cols}
        if date_col:
            value_obj["_date"] = r[date_col]
        ds_bucket[metric] = value_obj
        attached += 1

    # Long-format copy.
    LONG_DIR.mkdir(parents=True, exist_ok=True)
    dst = LONG_DIR / f"{dataset_token}__{metric}.csv"
    dst.write_text(src.read_text(encoding="utf-8-sig"), encoding="utf-8")
    return attached


def _current_short_sha() -> str:
    """Return `git rev-parse --short HEAD`. Empty string if not in a git tree."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(REPO_ROOT),
            stderr=subprocess.DEVNULL,
        )
        return out.decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _build_manifest(qa_rows: list[dict], attached_counts: dict[tuple[str, str], int]) -> dict:
    # Include every folder that passed metadata QA so placeholders are visible
    # in the index, even when they have no outputs yet.
    by_folder: dict[str, list[dict]] = defaultdict(list)
    folders_with_passing_meta: set[str] = set()
    for row in qa_rows:
        if row["status"] == "fail":
            continue
        if row["type"] == "metadata" and row["status"] == "pass":
            folders_with_passing_meta.add(row["dataset"])
        elif row["type"] in ("vector", "matrix"):
            by_folder[row["dataset"]].append(row)
    for folder_name in folders_with_passing_meta:
        by_folder.setdefault(folder_name, [])

    datasets: list[dict] = []
    for folder_name in sorted(by_folder):
        folder = DATA_DIR / folder_name
        meta = _read_metadata(folder)
        outputs: list[dict] = []
        for row in sorted(by_folder[folder_name], key=lambda r: r["file"]):
            parsed = parse_filename(row["file"])
            if parsed is None:
                continue
            entry = {
                "file": row["file"],
                "type": row["type"],
                "dataset_token": parsed.dataset,
                "metric": parsed.metric,
                "resolution": parsed.resolution,
            }
            if row["type"] == "vector":
                entry["in_geojson"] = True
                entry["zones_with_values"] = attached_counts.get(
                    (folder_name, row["file"]), 0
                )
                entry["long_csv"] = f"build/long/{parsed.dataset}__{parsed.metric}.csv"
            else:
                entry["in_geojson"] = False
                entry["matrix_log"] = "qa/matrix_log.csv"
            outputs.append(entry)
        datasets.append({
            "folder": folder_name,
            "source": meta.get("source"),
            "citation": meta.get("citation"),
            "source_url": meta.get("source_url"),
            "retrieved_on": str(meta.get("retrieved_on")) if meta.get("retrieved_on") else None,
            "license": meta.get("license"),
            "contact": meta.get("contact"),
            "status": meta.get("status", "active"),
            "outputs": outputs,
        })
    return {
        "shapefile": "data/shapefiles/DRC_Health_zones.shp",
        "n_features": len(load_zones()),
        "built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "commit": _current_short_sha(),
        "datasets": datasets,
    }


def main() -> int:
    if not QA_LOG.exists():
        print(f"qa log not found at {QA_LOG}; run tools/qa.py first.", file=sys.stderr)
        return 2

    qa_rows = _read_qa_log()
    features, features_by_nom = _load_features()

    attached_counts: dict[tuple[str, str], int] = {}
    for row in qa_rows:
        if row["status"] == "fail" or row["type"] != "vector":
            continue
        parsed = parse_filename(row["file"])
        if parsed is None:
            continue
        folder = DATA_DIR / row["dataset"]
        count = _attach_vector(folder, row["file"], parsed, features_by_nom)
        attached_counts[(row["dataset"], row["file"])] = count
        print(f"attached {row['file']}: {count} zones")

    BUILD_DIR.mkdir(exist_ok=True)
    geo = {"type": "FeatureCollection", "features": features}
    GEOJSON_OUT.write_text(json.dumps(geo), encoding="utf-8")

    manifest = _build_manifest(qa_rows, attached_counts)
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")

    print(
        f"wrote {GEOJSON_OUT.relative_to(REPO_ROOT)} "
        f"({len(features)} features, {GEOJSON_OUT.stat().st_size // 1024} KB)"
    )
    print(f"wrote {MANIFEST_OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
