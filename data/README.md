# Data directory

All outbreak-related sources in this repository are harmonised to the same **519 MoH health zones** (`shapefiles/DRC_Health_zones.shp`). Each source lives in its own folder; processing scripts turn `raw/` inputs into contract-shaped files in `processed/`. The merged map product is `build/drc_health_zones.geojson` (see the [root README](../README.md) for the current build snapshot and citation links).

## How folders are organised

Every dataset folder follows the same layout:

```
<dataset>/
  raw/              # untouched downloads (many files tracked with Git LFS)
  processed/        # outputs ready for QA and GeoJSON build
  metadata.yaml     # source, citation, license, retrieved_on, contact
  process.{py,R}    # optional; regenerates processed/
  README.md         # optional notes (provenance, quirks, plots)
  README_FR.md      # optional French translation; link from README.md header
```

**Join key:** canonical zone name `nom`, matching the shapefile attribute `Nom`. Spellings that differ from the shapefile are listed in [`aliases.csv`](aliases.csv) (including disambiguation of duplicate names such as `Bili` and `Lubunga` with a province suffix).

**Filenames:** `<dataset>__<metric>__<resolution>.csv` for per-zone tables, or `.matrix.csv` for origin–destination tables between zones. Full rules are in the root README *Data contract* section.

**Vectors vs matrices:** vector files have one row per zone (plus `date` for daily/weekly series). Matrix files are zone×zone tables (OSRM, IOM IDP, Flowminder); they are QA-catalogued but not embedded in the GeoJSON.

## Datasets

| Folder | Kind | In GeoJSON build | Notes |
|--------|------|------------------|-------|
| [`shapefiles/`](shapefiles/) | geometry | (base layer) | Source of truth for boundaries and `Nom` |
| [`epi/`](epi/) | vector | yes | WHO weekly external sitrep |
| [`insp_sitrep/`](insp_sitrep/) | vector (daily) | yes | INSP SitRep MVE 001–012 (003 missing); 28 metrics; zone + national totals |
| [`cross-border-movements/`](cross-border-movements/) | vector | yes | Imperial College POE passenger estimates |
| [`worldpop/`](worldpop/) | vector | yes | GRID3/Kummu-style population count & density |
| [`gdp_pc/`](gdp_pc/) | vector | yes | GDP per capita (PPP) |
| [`ccvi/`](ccvi/) | vector | yes | Climate Conflict Vulnerability Index |
| [`fao_lccs/`](fao_lccs/) | vector | yes | Urban land-cover fraction ([FR](fao_lccs/README_FR.md)) |
| [`grid3_healthsites/`](grid3_healthsites/) | vector | yes | GRID3 COD health facilities v8.0 |
| [`healthsites_io/`](healthsites_io/) | vector | yes | OSM / Healthsites.io subset |
| [`refugee_sites/`](refugee_sites/) | vector | yes | UNHCR refugee sites per zone |
| [`osrm/`](osrm/) | matrix | no | Car travel time & road distance (OSRM) |
| [`IDP/`](IDP/) | matrix | no | IOM DTM displacement flows (Ituri round) |
| [`flowminder/`](flowminder/) | matrix | no | Phone-based inflow/outflow estimates |
| [`ACLED_conflict/`](ACLED_conflict/) | — | no | Placeholder; province-level raw data only |

Folders with a **README** go deeper on provenance and processing. `metadata.yaml` is the machine-readable record used by `tools.qa` and `tools.build_geojson`.

**Bilingual docs:** GitHub only auto-renders `README.md` in a folder. Where `README_FR.md` exists (e.g. `fao_lccs/`), a **Language / Langue** line at the top of both files links between English and French — there is no built-in toggle on github.com.

## Working with this tree

From the repo root (after `git lfs install` and a venv with `tools/requirements.txt`):

```bash
.venv/bin/python -m tools.qa              # validate all processed outputs
.venv/bin/python -m tools.build_geojson   # refresh build/drc_health_zones.geojson
```

To add or refresh a source: update `raw/`, run that folder’s `process.py` or `process.R`, check `metadata.yaml`, run QA, then rebuild. Contributor steps are in the [root README](../README.md#contributor-flow).

## Root-level files

| File | Role |
|------|------|
| [`aliases.csv`](aliases.csv) | Maps observed zone labels → canonical `nom` |
| [`shapefiles/`](shapefiles/) | `DRC_Health_zones.*` — do not rename zones here without updating aliases and reprocessing dependents |
