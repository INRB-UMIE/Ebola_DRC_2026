# INRB MVE app line-list (recorded cases by zone)

Daily **recorded case counts** by health zone from the INRB MVE surveillance app line-list export. Each raw row is one case record; `process.py` harmonises French column headers to English, resolves zones to canonical `nom`, and aggregates by notification date.

**DISCLAIMER:**In its current version, this repsitory contains **no case data**, the files found in `processed/epi_mve_inrb_app__recorded_cases__daily.csv` is a dummy file to represent the processed data schema. The files regularly found in `raw/` and all processing scripts show operations to be performed outside of this repository for data privacy reasons. This data stream is not currently displayed in the [INRB UMIE dashboard](https://inrb-umie.github.io/EBOV2026_Epidemic_Dashboard/).

------------------------------------------------------------------------

## Files

| File | Description |
|------|-------------|
| `raw/mve_inrb_app_test_line_list.csv` | Line-list export (French headers) |
| `raw/mve_inrb_app_schema_column_names.csv` | `column_name_fr` → `column_name_en` mapping |
| `processed/epi_mve_inrb_app__recorded_cases__daily.csv` | Contract output: `nom`, `date`, `recorded_cases` |
| `process.py` | Rename columns, resolve zones, aggregate counts |
| `metadata.yaml` | Provenance and pipeline notes |

**Kind:** vector (daily time series). One row per (`nom`, `date`); `recorded_cases` is the number of line-list rows in that group.

**Spatial grouping:** raw field `ZS` (mapped to `health_zone`) is resolved to canonical `nom` via `data/aliases.csv` and the shapefile. If the zone label is missing or unknown, coordinates (`latitude`, `longitude`) are used for point-in-polygon lookup against `data/shapefiles/DRC_Health_zones.shp`.

**Date field:** `DATE_NOTIF` → `date_of_notification`, parsed to ISO `YYYY-MM-DD` in the output `date` column.

------------------------------------------------------------------------

## Regenerating outputs

After updating the raw line list or schema mapping:

```bash
python data/epi_mve_inrb_app/process.py
```

From the repo root:

```bash
.venv/bin/python -m tools.qa epi_mve_inrb_app
.venv/bin/python -m tools.build_geojson   # optional: embed in map product
```

Rows with empty or unparseable `date_of_notification` are skipped with a warning (they are not counted). Rows that cannot be assigned a canonical zone fail the build with a clear error — add aliases in `data/aliases.csv` or fix coordinates.

------------------------------------------------------------------------

## Provenance

See `metadata.yaml`. Join key: canonical `nom` from `data/shapefiles/DRC_Health_zones.shp`.
