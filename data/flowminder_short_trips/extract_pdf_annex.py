"""Extract Annex A ranked destination table (PDF pages 8–11) to raw CSV.

Run from repo root:
    python data/flowminder_short_trips/extract_pdf_annex.py
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pdfplumber

HERE = Path(__file__).resolve().parent
PDF = HERE / "raw" / "Population_movements_Ebola_28_May_2026_Flowminder_Final.pdf"
OUT = HERE / "raw" / "short_trips_destination_rankings.csv"

PDF_PAGES = (8, 9, 10, 11)  # 1-based

PROVINCES = sorted(
    [
        "Kongo Central",
        "Kasaï Central",
        "Haut-Katanga",
        "Haut-Uele",
        "Bas-Uele",
        "Nord-Kivu",
        "Sud-Kivu",
        "Tanganyika",
        "Kinshasa",
        "Equateur",
        "Mongala",
        "Maniema",
        "Tshopo",
        "Ituri",
        "Lualaba",
    ],
    key=len,
    reverse=True,
)

LINE_RE = re.compile(
    r"^(?P<rank>\d+)\s+"
    r"(?P<province>.+?)\s+"
    r"(?P<zone>.+?)\s+"
    r"(?P<d7>[\d.]+)\s+"
    r"(?P<d14>[\d.]+)\s+"
    r"(?P<d21>[\d.]+)\s+"
    r"(?P<d28>[\d.]+)\s+"
    r"(?P<d31>[\d.]+)$"
)


def _split_province_zone(mid: str) -> tuple[str, str] | None:
    for prov in PROVINCES:
        if mid.startswith(prov + " "):
            return prov, mid[len(prov) :].strip()
        if mid == prov:
            return prov, ""
    return None


def parse_line(line: str) -> dict[str, str | float | int] | None:
    line = line.strip()
    if not line or not line[0].isdigit():
        return None
    if line.startswith("Annex") or line.startswith("Rank ") or line.startswith("Page "):
        return None
    if line.startswith("Full table:") or "Continued on" in line:
        return None

    m = LINE_RE.match(line)
    if m:
        return {
            "rank": int(m.group("rank")),
            "province": m.group("province"),
            "health_zone": m.group("zone"),
            "d7": float(m.group("d7")),
            "d14": float(m.group("d14")),
            "d21": float(m.group("d21")),
            "d28": float(m.group("d28")),
            "d31": float(m.group("d31")),
        }

    parts = line.split()
    if len(parts) < 7 or not parts[0].isdigit():
        return None
    rank = int(parts[0])
    tail = parts[1:]
    if len(tail) < 6:
        return None
    nums = tail[-5:]
    mid = " ".join(tail[:-5])
    split = _split_province_zone(mid)
    if split is None:
        return None
    province, zone = split
    try:
        values = [float(x) for x in nums]
    except ValueError:
        return None
    return {
        "rank": rank,
        "province": province,
        "health_zone": zone,
        "d7": values[0],
        "d14": values[1],
        "d21": values[2],
        "d28": values[3],
        "d31": values[4],
    }


def extract_rows() -> list[dict[str, str | float | int]]:
    rows: list[dict[str, str | float | int]] = []
    with pdfplumber.open(PDF) as doc:
        for page_no in PDF_PAGES:
            text = doc.pages[page_no - 1].extract_text() or ""
            for line in text.splitlines():
                parsed = parse_line(line)
                if parsed:
                    rows.append(parsed)
    rows.sort(key=lambda r: int(r["rank"]))
    return rows


def main() -> int:
    if not PDF.exists():
        raise FileNotFoundError(f"Missing PDF: {PDF}")

    rows = extract_rows()
    if not rows:
        raise RuntimeError("No table rows extracted from PDF pages 8–11")

    ranks = {int(r["rank"]) for r in rows}
    expected = set(range(1, max(ranks) + 1))
    missing = sorted(expected - ranks)
    if missing:
        raise RuntimeError(f"Missing ranks after extraction (sample): {missing[:15]}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "rank",
        "province",
        "health_zone",
        "d7",
        "d14",
        "d21",
        "d28",
        "d31",
        "date_d7",
        "date_d14",
        "date_d21",
        "date_d28",
        "date_d31",
    ]
    date_cols = {
        "d7": "2026-04-30",
        "d14": "2026-05-07",
        "d21": "2026-05-14",
        "d28": "2026-05-21",
        "d31": "2026-05-24",
    }
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            out = dict(row)
            for key, iso in date_cols.items():
                out[f"date_{key}"] = iso
            w.writerow(out)

    print(f"wrote {OUT} ({len(rows)} destination zones)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
