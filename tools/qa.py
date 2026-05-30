"""QA runner for the DRC open-data pipeline.

Walks every folder under data/ (except shapefiles), validates its metadata.yaml
and any files in processed/ against the schema contract, and writes:

- qa/qa_log.csv         one row per checked artifact (all statuses)
- qa/matrix_log.csv     subset: matrix files that passed QA (consumer catalog)
- qa/reports/<dataset>.md   human-readable per-folder report

CLI:
    python -m tools.qa               # check everything
    python -m tools.qa flowminder    # restrict to listed datasets

Exit code is non-zero if any artifact failed (CI gate).

Vector file contract:
    Required column: 'nom' (canonical or alias-resolvable)
    For resolution != static: one of {date, week_start, month_start, year}
    Uniqueness: nom alone (static) or (nom, date) (time-series)

Matrix file contract (`.matrix.csv`):
    Snapshot (resolution=static):
        Header row: nom, <dest_nom_1>, <dest_nom_2>, ...
        First column = origin nom; remaining columns = destination noms.
    Time-series (any other resolution):
        Header row: date, nom, <dest_nom_1>, <dest_nom_2>, ...
        First column = ISO date; second column = origin nom; remaining = destinations.
    Cells must be non-negative numeric when present. Missing cells (empty or NA)
    are allowed and reported as warnings, not failures — e.g. unroutable OSRM pairs.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from tools.lib.schema import (
    REPO_ROOT,
    REQUIRED_METADATA_FIELDS,
    VALID_RUNTIMES,
    canonical_noms,
    parse_filename,
    to_canonical,
)

DATA_DIR = REPO_ROOT / "data"
QA_DIR = REPO_ROOT / "qa"
QA_LOG = QA_DIR / "qa_log.csv"
MATRIX_LOG = QA_DIR / "matrix_log.csv"
REPORTS_DIR = QA_DIR / "reports"

EXCLUDED_FOLDERS = {"shapefiles"}
DATE_COLUMN_CANDIDATES = ("date", "week_start", "month_start", "year")
# R write.csv() and other exports use these for missing matrix cells.
_MATRIX_MISSING_MARKERS = frozenset({"", "NA", "NaN", "nan", "NULL", "null"})


def _is_matrix_missing(value: str) -> bool:
    return value.strip() in _MATRIX_MISSING_MARKERS


@dataclass
class FileResult:
    dataset: str
    file: str
    type: str  # metadata | structure | vector | matrix
    status: str  # pass | fail | warn
    reasons: list[str] = field(default_factory=list)
    n_rows: int | None = None
    n_zones_covered: int | None = None
    n_cols: int | None = None
    square: bool | None = None
    resolution: str | None = None
    date_range: str | None = None


def qa_metadata(dataset: str, path: Path) -> FileResult:
    try:
        meta = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        return FileResult(dataset, "metadata.yaml", "metadata", "fail", [f"YAML error: {e}"])
    if not isinstance(meta, dict):
        return FileResult(dataset, "metadata.yaml", "metadata", "fail", ["root must be a mapping"])

    reasons: list[str] = []
    missing = [k for k in REQUIRED_METADATA_FIELDS if not meta.get(k)]
    if missing:
        reasons.append(f"missing fields: {missing}")
    runtime = meta.get("runtime")
    if runtime and runtime not in VALID_RUNTIMES:
        reasons.append(f"runtime {runtime!r} not in {list(VALID_RUNTIMES)}")
    retrieved = meta.get("retrieved_on")
    if retrieved and not isinstance(retrieved, dt.date):
        try:
            dt.date.fromisoformat(str(retrieved))
        except ValueError:
            reasons.append(f"retrieved_on {retrieved!r} not ISO date (YYYY-MM-DD)")
    return FileResult(
        dataset, "metadata.yaml", "metadata",
        "fail" if reasons else "pass", reasons,
    )


def _read_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader, []) or []
        rows = list(reader)
    return header, rows


def qa_vector(dataset: str, path: Path, parsed) -> FileResult:
    try:
        header, rows = _read_csv(path)
    except (OSError, csv.Error, UnicodeDecodeError) as e:
        return FileResult(dataset, path.name, "vector", "fail", [f"CSV read error: {e}"])

    reasons: list[str] = []

    # Defensive: empty column headers usually come from R's write.csv writing
    # the row-index column without row.names=FALSE. Surfaced as a warn so the
    # upstream process script gets cleaned up; the build script skips empty
    # headers when attaching values so they don't leak into feature properties.
    empty_header_count = sum(1 for h in header if h == "")
    if empty_header_count:
        reasons.append(
            f"{empty_header_count} empty column header(s); likely R "
            "write.csv without row.names=FALSE (warn)"
        )

    # Defensive: value-column headers that resolve to canonical zone names
    # indicate a matrix posing as a vector (one column per destination zone).
    # Real vector datasets use metric names, never zone names — fail hard so
    # the OD matrix doesn't get embedded per-feature by the build script.
    zone_headers = [h for h in header if h != "nom" and to_canonical(h) is not None]
    if zone_headers:
        return FileResult(
            dataset, path.name, "vector", "fail",
            [f"{len(zone_headers)} value column(s) resolve to canonical zone "
             f"names (sample: {zone_headers[:5]}) — looks like a matrix "
             "misnamed as vector"],
            n_rows=len(rows),
        )

    if "nom" not in header:
        return FileResult(
            dataset, path.name, "vector", "fail",
            [f"missing 'nom' column (got {header[:6]}...)" if header else "empty file"],
            n_rows=len(rows),
        )
    nom_i = header.index("nom")
    date_col = next((c for c in DATE_COLUMN_CANDIDATES if c in header), None)
    date_i = header.index(date_col) if date_col else None
    if parsed.resolution != "static" and date_col is None:
        reasons.append(
            f"resolution {parsed.resolution!r} requires a date column "
            f"(one of {list(DATE_COLUMN_CANDIDATES)})"
        )

    unresolved: list[str] = []
    canonical_seen: set[str] = set()
    keys: list = []
    width_mismatches = 0
    checked_dates: set[str] = set()
    bad_dates: set[str] = set()
    for ri, r in enumerate(rows, start=2):
        if len(r) != len(header):
            width_mismatches += 1
            continue
        canonical = to_canonical(r[nom_i])
        if canonical is None:
            unresolved.append(r[nom_i])
        else:
            canonical_seen.add(canonical)
        keys.append((r[nom_i], r[date_i]) if date_i is not None else r[nom_i])
        if date_i is not None:
            date_value = r[date_i]
            if date_value not in checked_dates:
                checked_dates.add(date_value)
                if date_col == "year":
                    if len(date_value) != 4 or not date_value.isdecimal():
                        bad_dates.add(date_value)
                else:
                    try:
                        if dt.date.fromisoformat(date_value).isoformat() != date_value:
                            bad_dates.add(date_value)
                    except ValueError:
                        bad_dates.add(date_value)
    if width_mismatches:
        reasons.append(f"{width_mismatches} rows with width mismatch (expected {len(header)} fields)")

    if unresolved:
        sample = sorted(set(unresolved))[:5]
        reasons.append(f"{len(unresolved)} rows with unresolved nom (sample: {sample})")

    dup = [k for k, c in Counter(keys).items() if c > 1]
    if dup:
        reasons.append(f"{len(dup)} duplicate keys (sample: {dup[:3]})")
    if bad_dates:
        reasons.append(
            f"{len(bad_dates)} non-ISO {date_col} values "
            f"(sample: {sorted(bad_dates)[:5]})"
        )

    fatal = [r for r in reasons if not r.endswith("(warn)")]
    status = "fail" if fatal else ("warn" if reasons else "pass")
    return FileResult(
        dataset, path.name, "vector", status, reasons,
        n_rows=len(rows), n_zones_covered=len(canonical_seen),
        resolution=parsed.resolution,
    )


def qa_matrix(dataset: str, path: Path, parsed) -> FileResult:
    try:
        header, rows = _read_csv(path)
    except (OSError, csv.Error, UnicodeDecodeError) as e:
        return FileResult(dataset, path.name, "matrix", "fail", [f"CSV read error: {e}"])

    if not header:
        return FileResult(dataset, path.name, "matrix", "fail", ["empty file"])

    reasons: list[str] = []
    static = parsed.resolution == "static"
    if static:
        if header[0] != "nom":
            reasons.append(f"first column header must be 'nom', got {header[0]!r}")
        origin_i, dest_start, date_i = 0, 1, None
    else:
        if header[0] != "date":
            reasons.append(f"first column header must be 'date', got {header[0]!r}")
        if len(header) < 2 or header[1] != "nom":
            got = header[1] if len(header) > 1 else "<missing>"
            reasons.append(f"second column header must be 'nom', got {got!r}")
        origin_i, dest_start, date_i = 1, 2, 0

    dest_headers = header[dest_start:]
    unresolved_dest = [h for h in dest_headers if to_canonical(h) is None]
    if unresolved_dest:
        reasons.append(
            f"{len(unresolved_dest)} destination headers unresolved "
            f"(sample: {unresolved_dest[:5]})"
        )

    unresolved_origin: list[str] = []
    canonical_seen: set[str] = set()
    bad_values = 0
    missing_cells = 0
    dates_seen: set[str] = set()

    for ri, row in enumerate(rows, start=2):
        if len(row) != len(header):
            reasons.append(f"row {ri} has {len(row)} fields, expected {len(header)}")
            continue
        origin = row[origin_i]
        canonical = to_canonical(origin)
        if canonical is None:
            unresolved_origin.append(origin)
        else:
            canonical_seen.add(canonical)
        if date_i is not None:
            dates_seen.add(row[date_i])
        for v in row[dest_start:]:
            if _is_matrix_missing(v):
                missing_cells += 1
                continue
            try:
                fv = float(v)
                if fv < 0:
                    bad_values += 1
            except ValueError:
                bad_values += 1

    if unresolved_origin:
        reasons.append(
            f"{len(unresolved_origin)} origin labels unresolved "
            f"(sample: {sorted(set(unresolved_origin))[:5]})"
        )
    if bad_values:
        reasons.append(f"{bad_values} non-numeric or negative cells")
    if missing_cells:
        reasons.append(f"{missing_cells} missing cells (empty/NA) (warn)")

    fatal = [r for r in reasons if not r.endswith("(warn)")]
    has_warn = any(r.endswith("(warn)") for r in reasons)
    if fatal:
        status = "fail"
    elif has_warn:
        status = "warn"
    else:
        status = "pass"

    # "square" only meaningful for snapshot matrices. Compare unique canonical
    # origins to destinations, not raw row count: a matrix with collapsible
    # duplicate origin labels (e.g. IDP's legacy Bunia row) is still square
    # after canonicalisation.
    square = (len(canonical_seen) == len(dest_headers)) if date_i is None else None
    date_range = None
    if dates_seen:
        ds = sorted(dates_seen)
        date_range = f"{ds[0]}..{ds[-1]}" if ds[0] != ds[-1] else ds[0]

    return FileResult(
        dataset, path.name, "matrix", status, reasons,
        n_rows=len(rows), n_cols=len(dest_headers),
        square=square, resolution=parsed.resolution,
        date_range=date_range, n_zones_covered=len(canonical_seen),
    )


def qa_folder(folder: Path) -> list[FileResult]:
    dataset = folder.name
    results: list[FileResult] = []

    meta_path = folder / "metadata.yaml"
    if not meta_path.exists():
        results.append(FileResult(
            dataset, "metadata.yaml", "metadata", "fail",
            ["metadata.yaml not present"],
        ))
    else:
        results.append(qa_metadata(dataset, meta_path))

    processed = folder / "processed"
    if not processed.exists():
        results.append(FileResult(
            dataset, "processed/", "structure", "warn",
            ["no processed/ directory"],
        ))
        return results

    files = sorted(p for p in processed.iterdir() if p.is_file())
    if not files:
        results.append(FileResult(
            dataset, "processed/", "structure", "warn",
            ["processed/ is empty"],
        ))
        return results

    for f in files:
        parsed = parse_filename(f.name)
        if parsed is None:
            results.append(FileResult(
                dataset, f.name, "structure", "fail",
                ["filename does not match contract <dataset>__<metric>__<resolution>.(csv|matrix.csv)"],
            ))
            continue
        if parsed.kind == "vector":
            results.append(qa_vector(dataset, f, parsed))
        else:
            results.append(qa_matrix(dataset, f, parsed))

    return results


def write_logs(results: list[FileResult]) -> None:
    QA_DIR.mkdir(exist_ok=True)
    REPORTS_DIR.mkdir(exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    with QA_LOG.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "dataset", "file", "type", "status",
            "n_rows", "n_zones_covered", "reasons", "checked_at",
        ])
        for r in results:
            w.writerow([
                r.dataset, r.file, r.type, r.status,
                "" if r.n_rows is None else r.n_rows,
                "" if r.n_zones_covered is None else r.n_zones_covered,
                "; ".join(r.reasons),
                now,
            ])

    with MATRIX_LOG.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "dataset", "file", "resolution", "n_rows", "n_cols",
            "square", "date_range", "n_zones_covered", "checked_at",
        ])
        for r in results:
            if r.type == "matrix" and r.status in ("pass", "warn"):
                w.writerow([
                    r.dataset, r.file, r.resolution, r.n_rows, r.n_cols,
                    "" if r.square is None else r.square,
                    r.date_range or "",
                    r.n_zones_covered, now,
                ])

    by_dataset: dict[str, list[FileResult]] = defaultdict(list)
    for r in results:
        by_dataset[r.dataset].append(r)
    for dataset, rs in by_dataset.items():
        lines = [f"# QA report: {dataset}", "", f"_Checked: {now}_", ""]
        statuses = Counter(r.status for r in rs)
        lines.append(f"**Status counts:** {dict(statuses)}")
        lines.append("")
        for r in rs:
            lines.append(f"## `{r.file}` ({r.type}) — **{r.status}**")
            if r.n_rows is not None:
                lines.append(f"- rows: {r.n_rows}")
            if r.n_cols is not None:
                lines.append(f"- cols: {r.n_cols}")
            if r.n_zones_covered is not None:
                lines.append(f"- zones covered: {r.n_zones_covered} / {len(canonical_noms())}")
            if r.resolution:
                lines.append(f"- resolution: {r.resolution}")
            if r.date_range:
                lines.append(f"- date range: {r.date_range}")
            if r.square is not None:
                lines.append(f"- square: {r.square}")
            if r.reasons:
                lines.append("- reasons:")
                for reason in r.reasons:
                    lines.append(f"  - {reason}")
            lines.append("")
        (REPORTS_DIR / f"{dataset}.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("datasets", nargs="*", help="Restrict to these dataset folders")
    args = ap.parse_args()

    folders = sorted(
        p for p in DATA_DIR.iterdir()
        if p.is_dir()
        and p.name not in EXCLUDED_FOLDERS
        and (not args.datasets or p.name in args.datasets)
    )
    if not folders:
        print("No dataset folders to check.", file=sys.stderr)
        return 0

    all_results: list[FileResult] = []
    for f in folders:
        all_results.extend(qa_folder(f))

    write_logs(all_results)

    statuses = Counter(r.status for r in all_results)
    print(f"QA summary: {dict(statuses)}  (folders checked: {len(folders)})")
    for r in all_results:
        if r.status == "fail":
            print(f"  FAIL  {r.dataset}/{r.file}: {'; '.join(r.reasons)}")
        elif r.status == "warn":
            print(f"  warn  {r.dataset}/{r.file}: {'; '.join(r.reasons)}")
    return 1 if statuses.get("fail", 0) else 0


if __name__ == "__main__":
    sys.exit(main())
