"""Render a choropleth of refugee/IDP sites per DRC health zone.

Reads:
  data/shapefiles/DRC_Health_zones.shp
  data/refugee_sites/processed/refugee_sites__sites__static.csv
  data/refugee_sites/raw/drc_refugee_sites.geojson   (for point overlay)

Writes:
  data/refugee_sites/map.png

Run from repo root:
    python data/refugee_sites/map.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import matplotlib.pyplot as plt  # noqa: E402
import shapefile  # pyshp  # noqa: E402
from matplotlib.colors import Normalize  # noqa: E402
from matplotlib.patches import Polygon as MplPolygon  # noqa: E402
from shapely.geometry import shape  # noqa: E402

from tools.lib.schema import SHAPEFILE, load_zones  # noqa: E402

HERE = Path(__file__).resolve().parent
PROCESSED_CSV = HERE / "processed" / "refugee_sites__sites__static.csv"
RAW_GEOJSON = HERE / "raw" / "drc_refugee_sites.geojson"
OUT_PNG = HERE / "map.png"


def _load_site_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    with PROCESSED_CSV.open(newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            counts[row["nom"]] = int(row["sites"])
    return counts


def _load_site_points() -> list[tuple[float, float]]:
    with RAW_GEOJSON.open(encoding="utf-8") as f:
        fc = json.load(f)
    points: list[tuple[float, float]] = []
    for feat in fc.get("features", []):
        geom_raw = feat.get("geometry")
        if geom_raw is None:
            continue
        geom = shape(geom_raw)
        if not geom.is_valid:
            geom = geom.buffer(0)
        rep = geom if geom.geom_type == "Point" else geom.centroid
        points.append((rep.x, rep.y))
    return points


def _plot_polygon(ax, sh, facecolor, edgecolor="#888888", linewidth=0.2):
    # pyshp shapes can be multi-part: parts marks where each ring starts.
    parts = list(sh.parts) + [len(sh.points)]
    for i in range(len(parts) - 1):
        ring = sh.points[parts[i]:parts[i + 1]]
        if len(ring) < 3:
            continue
        ax.add_patch(MplPolygon(
            ring, closed=True,
            facecolor=facecolor, edgecolor=edgecolor, linewidth=linewidth,
        ))


def main() -> int:
    counts = _load_site_counts()
    points = _load_site_points()
    zones = load_zones()
    reader = shapefile.Reader(str(SHAPEFILE))
    shapes_ = reader.shapes()

    max_count = max(counts.values()) if counts else 1
    norm = Normalize(vmin=0, vmax=max_count)
    cmap = plt.get_cmap("YlOrRd")

    fig, ax = plt.subplots(figsize=(10, 10))
    for zone, sh in zip(zones, shapes_):
        n = counts.get(zone.canonical_nom, 0)
        face = "#f4f4f4" if n == 0 else cmap(norm(n))
        _plot_polygon(ax, sh, facecolor=face)

    if points:
        xs, ys = zip(*points)
        ax.scatter(
            xs, ys, s=10, c="#003366",
            edgecolors="white", linewidths=0.3, zorder=5,
            label=f"sites with geometry (n={len(points)})",
        )

    ax.set_aspect("equal")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(
        "Refugee / IDP sites per DRC health zone\n"
        f"({sum(counts.values())} sites in {len(counts)} of {len(zones)} zones; "
        "OSM, retrieved 2026-05-20)"
    )

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, shrink=0.6, label="sites per zone")
    cbar.set_ticks(range(0, max_count + 1, max(1, max_count // 5)))

    ax.legend(loc="lower right", fontsize=8, frameon=True)

    # Tight bounds around shapefile.
    all_xs = [p[0] for sh in shapes_ for p in sh.points]
    all_ys = [p[1] for sh in shapes_ for p in sh.points]
    pad = 0.5
    ax.set_xlim(min(all_xs) - pad, max(all_xs) + pad)
    ax.set_ylim(min(all_ys) - pad, max(all_ys) + pad)

    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    print(f"wrote {OUT_PNG.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
