"""Aggregate OSM refugee/IDP site geometries to DRC health zones (count per zone).

Reads:
  raw/drc_refugee_sites.geojson    88 OSM features (nodes/ways/relations) tagged
                                   as refugee_site / refugee_shelter / IDP camp.

Writes:
  processed/refugee_sites__sites__static.csv   nom, sites
  fallback_points.csv                          name, lat, lon, assigned_nom
                                               — features whose representative
                                               point fell outside every polygon
                                               and were snapped to the nearest
                                               zone. Diagnostic only, not a
                                               contract artifact.
  skipped_features.csv                         osm_type, osm_id, name
                                               — features dropped because their
                                               geometry is null in the upstream
                                               extraction (all OSM relations as
                                               of 2026-05-20). Diagnostic only.

The raw GeoJSON mixes Point (OSM nodes) and Polygon (OSM ways). For polygons we
use the centroid as the representative point for point-in-polygon against the
DRC health-zone shapefile. The companion raw CSV is not used: it lacks lat/lon
for the same 21 relation-type features whose geometries are also null here.

Run from repo root:
    python data/refugee_sites/process.py
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import shapefile  # pyshp  # noqa: E402
from shapely.geometry import Point, shape  # noqa: E402
from shapely.strtree import STRtree  # noqa: E402

from tools.lib.schema import SHAPEFILE, load_zones  # noqa: E402

HERE = Path(__file__).resolve().parent
RAW_GEOJSON = HERE / "raw" / "drc_refugee_sites.geojson"
OUT_CSV = HERE / "processed" / "refugee_sites__sites__static.csv"
FALLBACK_CSV = HERE / "fallback_points.csv"
SKIPPED_CSV = HERE / "skipped_features.csv"


def _load_zone_geometries() -> list[tuple[str, "shape"]]:
    reader = shapefile.Reader(str(SHAPEFILE))
    zones = load_zones()
    geoms: list[tuple[str, "shape"]] = []
    for zone, sh in zip(zones, reader.shapes()):
        geom = shape(sh.__geo_interface__)
        if not geom.is_valid:
            geom = geom.buffer(0)
        geoms.append((zone.canonical_nom, geom))
    return geoms


def _zone_for_point(
    point: Point,
    geoms: list[tuple[str, "shape"]],
    tree: STRtree,
) -> tuple[str, bool]:
    """Return (canonical_nom, used_fallback).

    used_fallback is True when no polygon contained the point and we picked the
    nearest one instead — useful for spotting points that drift outside DRC.
    """
    candidate_idxs = tree.query(point)
    for idx in candidate_idxs:
        nom, geom = geoms[idx]
        if geom.covers(point):
            return nom, False
    nearest_idxs = tree.query_nearest(point, exclusive=False)
    best_nom = None
    best_dist = float("inf")
    for idx in nearest_idxs:
        nom, geom = geoms[idx]
        dist = point.distance(geom)
        if dist < best_dist:
            best_dist = dist
            best_nom = nom
    if best_nom is None:
        raise RuntimeError(f"No zone found near {point}")
    return best_nom, True


def _load_points() -> tuple[list[tuple[float, float, str]], list[tuple[str, str, str]]]:
    """Return (usable_points, skipped_features).

    usable_points    : (lat, lon, name) for features with a non-null geometry.
                       Polygons are reduced to their centroid.
    skipped_features : (osm_type, osm_id, name) for features whose geometry is
                       null in the upstream extraction.
    """
    with RAW_GEOJSON.open(encoding="utf-8") as f:
        fc = json.load(f)
    usable: list[tuple[float, float, str]] = []
    skipped: list[tuple[str, str, str]] = []
    for feat in fc.get("features", []):
        props = feat.get("properties") or {}
        name = (props.get("name") or "").strip()
        geom_raw = feat.get("geometry")
        if geom_raw is None:
            skipped.append((
                str(props.get("osm_type") or ""),
                str(props.get("osm_id") or ""),
                name,
            ))
            continue
        geom = shape(geom_raw)
        if not geom.is_valid:
            geom = geom.buffer(0)
        rep = geom if geom.geom_type == "Point" else geom.centroid
        usable.append((rep.y, rep.x, name))
    return usable, skipped


def main() -> int:
    geoms = _load_zone_geometries()
    tree = STRtree([g for _, g in geoms])

    per_zone: Counter[str] = Counter()
    fallback_points: list[tuple[str, float, float, str]] = []
    usable, skipped = _load_points()
    for lat, lon, name in usable:
        nom, used_fallback = _zone_for_point(Point(lon, lat), geoms, tree)
        per_zone[nom] += 1
        if used_fallback:
            fallback_points.append((name, lat, lon, nom))

    OUT_CSV.parent.mkdir(exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["nom", "sites"])
        for nom in sorted(per_zone):
            w.writerow([nom, per_zone[nom]])
    print(f"wrote {OUT_CSV.relative_to(REPO_ROOT)} ({len(per_zone)} zones)")

    with FALLBACK_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "lat", "lon", "assigned_nom"])
        for name, lat, lon, nom in fallback_points:
            w.writerow([name, lat, lon, nom])
    print(
        f"wrote {FALLBACK_CSV.relative_to(REPO_ROOT)} "
        f"({len(fallback_points)} fallback point(s))"
    )

    with SKIPPED_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["osm_type", "osm_id", "name"])
        for osm_type, osm_id, name in skipped:
            w.writerow([osm_type, osm_id, name])
    print(
        f"wrote {SKIPPED_CSV.relative_to(REPO_ROOT)} "
        f"({len(skipped)} feature(s) with null geometry)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
