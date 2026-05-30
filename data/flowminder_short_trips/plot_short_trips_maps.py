"""Choropleth maps for short-trip proportion matrices (one panel per snapshot date).

Uses the first data row of each processed matrix. Cohort zones (Bunia, Mongbalu,
Rwampara) share one highlight colour; other zones are filled by destination
proportion (graded viridis). Map extent: Ituri, Nord-Kivu, and northern Sud-Kivu.

Run from repo root:
    python data/flowminder_short_trips/plot_short_trips_maps.py
"""

from __future__ import annotations

import csv
import os
import re
import sys
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import matplotlib.pyplot as plt  # noqa: E402
import shapefile  # pyshp  # noqa: E402
from matplotlib.cm import ScalarMappable  # noqa: E402
from matplotlib.colors import Normalize  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Polygon as MplPolygon  # noqa: E402
from shapely.geometry import shape as shapely_shape  # noqa: E402

from tools.lib.schema import SHAPEFILE, load_zones  # noqa: E402

HERE = Path(__file__).resolve().parent
PROCESSED_DIR = HERE / "processed"
OUT_PNG = HERE / "short_trips_outflow_maps.png"

COHORT_ZONES = frozenset({"Bunia", "Mongbalu", "Rwampara"})
COHORT_FILL = "#c0392b"
NO_DATA_FILL = "#f5f5f5"
ZONE_EDGE = "#666666"

# Sud-Kivu zones with centroid north of this latitude (approx. northern outbreak belt).
SUD_KIVU_NORTH_LAT_MIN = -2.35

MAP_PROVINCES = frozenset({"Ituri", "Nord-Kivu"})

SNAPSHOT_LABELS = {
    "20260430": "30 Apr 2026 (D+7)",
    "20260507": "7 May 2026 (D+14)",
    "20260514": "14 May 2026 (D+21)",
    "20260521": "21 May 2026 (D+28)",
    "20260524": "24 May 2026 (D+31)",
}


def _plot_polygon(ax, sh: shapefile.Shape, **kwargs) -> None:
    parts = list(sh.parts) + [len(sh.points)]
    for i in range(len(parts) - 1):
        ring = sh.points[parts[i]: parts[i + 1]]
        if len(ring) >= 3:
            ax.add_patch(MplPolygon(ring, closed=True, **kwargs))


def _in_map_extent(province: str, centroid_y: float) -> bool:
    if province in MAP_PROVINCES:
        return True
    if province == "Sud-Kivu" and centroid_y >= SUD_KIVU_NORTH_LAT_MIN:
        return True
    return False


def _load_map_zones() -> tuple[dict[str, shapefile.Shape], dict[str, str]]:
    """Return shapes and provinces for zones in the map extent."""
    zones = load_zones()
    reader = shapefile.Reader(str(SHAPEFILE))
    shapes: dict[str, shapefile.Shape] = {}
    provinces: dict[str, str] = {}
    for zone, shp, rec in zip(zones, reader.shapes(), reader.records()):
        geom = shapely_shape(shp.__geo_interface__)
        if not geom.is_valid:
            geom = geom.buffer(0)
        cy = geom.centroid.y
        prov = rec["PROVINCE"]
        if not _in_map_extent(prov, cy):
            continue
        shapes[zone.canonical_nom] = shp
        provinces[zone.canonical_nom] = prov
    return shapes, provinces


def _map_bounds(zone_shapes: dict[str, shapefile.Shape]) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for sh in zone_shapes.values():
        xs.extend(p[0] for p in sh.points)
        ys.extend(p[1] for p in sh.points)
    pad = 0.12
    return min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad


def _list_matrix_files() -> list[Path]:
    files = sorted(PROCESSED_DIR.glob("flowminder_short_trips__outflow_*__static.matrix.csv"))
    if not files:
        raise FileNotFoundError(f"No processed matrices in {PROCESSED_DIR}")
    return files


def _date_tag(path: Path) -> str:
    m = re.search(r"outflow_(\d{8})__", path.name)
    if not m:
        raise ValueError(f"Cannot parse date from {path.name}")
    return m.group(1)


def _load_first_row_flows(path: Path) -> dict[str, float]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        row = next(reader)
    flows: dict[str, float] = {}
    for col, val in row.items():
        if col == "nom":
            continue
        try:
            flows[col] = float(val)
        except ValueError:
            continue
    return flows


def _draw_panel(
    ax,
    flows: dict[str, float],
    zone_shapes: dict[str, shapefile.Shape],
    bounds: tuple[float, float, float, float],
    vmax: float,
    title: str,
    cmap,
    norm: Normalize,
) -> None:
    xmin, xmax, ymin, ymax = bounds

    for nom, sh in zone_shapes.items():
        if nom in COHORT_ZONES:
            face = COHORT_FILL
        else:
            value = flows.get(nom, 0.0)
            if value > 0:
                face = cmap(norm(value))
            else:
                face = NO_DATA_FILL
        _plot_polygon(
            ax,
            sh,
            facecolor=face,
            edgecolor=ZONE_EDGE,
            linewidth=0.35,
            zorder=2 if nom in COHORT_ZONES else 1,
        )

    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=10)
    ax.set_xticks([])
    ax.set_yticks([])


def main() -> int:
    matrix_files = _list_matrix_files()
    zone_shapes, _provinces = _load_map_zones()
    bounds = _map_bounds(zone_shapes)

    all_flows = [_load_first_row_flows(p) for p in matrix_files]
    vmax = max(max(f.values()) for f in all_flows)
    cmap = plt.get_cmap("viridis")
    norm = Normalize(vmin=0, vmax=vmax)

    n = len(matrix_files)
    ncols = 3
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(
        nrows,
        ncols,
        figsize=(5.2 * ncols, 5.0 * nrows),
        squeeze=False,
        layout="constrained",
    )

    for idx, path in enumerate(matrix_files):
        ax = axes[idx // ncols][idx % ncols]
        tag = _date_tag(path)
        label = SNAPSHOT_LABELS.get(tag, tag)
        _draw_panel(
            ax,
            all_flows[idx],
            zone_shapes,
            bounds,
            vmax,
            label,
            cmap,
            norm,
        )

    for j in range(n, nrows * ncols):
        axes[j // ncols][j % ncols].axis("off")

    cohort_handle = Line2D(
        [0],
        [0],
        marker="s",
        color="w",
        markerfacecolor=COHORT_FILL,
        markeredgecolor=ZONE_EDGE,
        markersize=8,
        label="Bunia / Mongbalu / Rwampara",
    )
    sm = ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=axes.ravel().tolist(), fraction=0.025, pad=0.02)
    cbar.set_label("Proportion seen at destination (%)")

    fig.legend(
        handles=[cohort_handle],
        loc="lower center",
        ncol=1,
        frameon=True,
        fontsize=9,
    )
    fig.suptitle(
        "Flowminder short-trip destination proportions\n"
        "Cohort: Bunia + Mongbalu + Rwampara (3–23 Apr 2026) · Ituri, Nord-Kivu, north Sud-Kivu",
        fontsize=12,
    )
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {OUT_PNG.relative_to(REPO_ROOT)} ({len(zone_shapes)} health zones in extent)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
