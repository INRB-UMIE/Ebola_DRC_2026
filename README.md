# Bundibugyo Ebola virus outbreak 2026
<img align="right" src="docs/inrb_logo_2.jpeg" width=250px>

Data for the 2026 Bundibugyo Ebolavirus (BDBV) outbreak.

This work is led by the Institut National de Recherche Biomédicale (INRB) Kinshasa (Dav Ebengo, Placide Mbala-Kingebeni and Tania Bishola) in collaboration with partners across the University of Oxford and Northeastern University; please contact m.davebengo@gmail.com for further information.

Last successful build: **21 May 2026, 10:43:55 (+01:00)** (commit `d8905f5`).

# Data sources

-   **DRC health zones:** [Humanitarian Data Exchange](https://data.humdata.org/dataset/drc-health-data) (MoH zones de santé shapefile)
-   **Epidemiological data:** [Weekly External Situation Report 01, Data as of 18 May 2026](https://iris.who.int/server/api/core/bitstreams/bb1d4668-04e0-4563-b7c4-d1bdefbc9f05/content)
-   **Road travel times:** [OSRM](http://project-osrm.org/) public demo
-   **Cross-border travel:** [Imperial College Report](https://www.imperial.ac.uk/mrc-global-infectious-disease-analysis/research-themes/preparedness-and-response-to-emerging-threats/report-ebola-18-05-2026/)
-   **Conflicts and acts of violence:** [ACLED](https://acleddata.com)
-   **Internal displacements:** International Organisation for Migrants ([IOM](https://dtm.iom.int))
-   **Population size rasters**: [GRID3 v4.4 gridded population](https://data.grid3.org/maps/a3db539c0fae4c05aed92ed67e11fe2b/about)
-   **Health facilities**: [GRID3 COD Health Facilities v8.0](https://data.grid3.org/datasets/GRID3::grid3-cod-health-facilities-v8-0/about)
-   **Health facilities (OSM / crowdsourced):** [Healthsites.io](https://healthsites.io/)
-   **Mobile phone-based internal displacement estimates:** [Flowminder.org](https://www.flowminder.org/resources/publications-reports/drc-reports-publications)

For the latest BDBV genomic data, please visit [Pathoplexus](https://pathoplexus.org/ebola-bdbv/search).

# Current build (2026-05-21)

Snapshot of `build/drc_health_zones.geojson` (519 zones, \~36 MB) and the matrix catalogue, at commit `d8905f5`. Re-run `python -m tools.build_geojson` after pulling to regenerate locally; `build/manifest.json` carries the same information in machine-readable form.

**New in this build:** `healthsites_io` — facility count and density per health zone from Healthsites.io (OpenStreetMap); metadata and both vector outputs passed QA and are embedded in the GeoJSON.

**Embedded in the GeoJSON** — each output appears under `feature.properties.<dataset>.<metric>`:

| Folder | Output | Retrieved | Status |
|----|----|----|----|
| ccvi | `ccvi__socioeconomic_deprivation__static.csv` | 2026-05-20 | active |
| ccvi | `ccvi__socioeconomic_inequality__static.csv` | 2026-05-20 | active |
| cross-border-movements | `cross_border__poe_passengers__static.csv` | 2026-05-18 | active |
| epi | `epi__cases__weekly.csv` | 2026-05-18 | active |
| fao_lccs | `fao_lccs__urban_fraction__static.csv` | 2026-05-20 | active |
| gdp_pc | `gdp_pc__gdp_pc__static.csv` | 2026-05-20 | active |
| healthsites_io | `healthsites_io__healthsite_count__static.csv` | 2026-05-20 | active |
| healthsites_io | `healthsites_io__healthsite_density__static.csv` | 2026-05-20 | active |
| osrm | `osrm__road_distance__static.csv` | 2026-03-17 | active |
| osrm | `osrm__travel_time__static.csv` | 2026-03-17 | active |
| refugee_sites | `refugee_sites__sites__static.csv` | 2026-05-20 | active |
| worldpop | `worldpop__pop_count__static.csv` | 2026-05-20 | active |
| worldpop | `worldpop__pop_density__static.csv` | 2026-05-20 | active |

**Matrix outputs** — not embedded (large, square OD-style); fetched as raw CSV and catalogued in `qa/matrix_log.csv`:

| Folder     | Output                                   | Retrieved  | Status |
|------------|------------------------------------------|------------|--------|
| IDP        | `idp__individuals__static.matrix.csv`    | 2026-01-31 | active |
| IDP        | `idp__individuals__weekly.matrix.csv`    | 2026-01-31 | active |
| IDP        | `idp__individuals__monthly.matrix.csv`   | 2026-01-31 | active |
| flowminder | `flowminder__inflow__static.matrix.csv`  | 2026-05-20 | active |
| flowminder | `flowminder__outflow__static.matrix.csv` | 2026-05-20 | active |

**Not in build**: `ACLED_conflict` — province-grain placeholder, no QA-passing output yet.

# Repository layout

```         
data/
  shapefiles/                source of truth for health-zone boundaries
  aliases.csv                observed_name -> canonical_nom mappings
  <dataset>/                 one folder per source
    raw/                     untouched source files
    process.{py,R}           script that produces files in processed/
    processed/               standardized contract-conformant outputs
    metadata.yaml            source, citation, retrieved_on, license, contact, runtime
    README.md                optional human notes
tools/
  lib/schema.py              canonical Noms, alias resolver, filename contract
  qa.py                      walks data/, validates, writes qa/qa_log.csv & qa/matrix_log.csv
  build_geojson.py           merges passing non-matrix outputs into build/drc_health_zones.geojson
  requirements.txt           pyshp, pyyaml, shapely
qa/
  qa_log.csv                 per-artifact QA results (all statuses)
  matrix_log.csv             catalog of QA-passing matrices
  reports/<dataset>.md       per-folder human-readable report
build/
  drc_health_zones.geojson   shapefile + latest per-zone values
  long/<dataset>__<metric>.csv  full long-format copy of each vector file
  manifest.json              sources + build timestamp
```

# Data contract

**Join key:** the canonical `Nom` from `data/shapefiles/DRC_Health_zones.shp`. The two natural collisions (`Bili`, `Lubunga`) are disambiguated with a province suffix, e.g. `Lubunga (Tshopo)`. Observed spellings that differ are listed in `data/aliases.csv`.

**Processed-file naming:** `<dataset>__<metric>__<resolution>.{csv|matrix.csv}` - `<dataset>` and `<metric>` are lower_snake_case. - `<resolution>` ∈ {`static`, `daily`, `weekly`, `monthly`, `yearly`}. - Suffix is `.matrix.csv` for matrix outputs, `.csv` for vector (one-row-per-zone) outputs.

**Vector files** carry a `nom` column. Non-static resolutions also carry a `date` column (ISO 8601). **Matrix files** layout: snapshot matrices have header `nom, <dest_nom_1>, ...`; time-series matrices have `date, nom, <dest_nom_1>, ...`. Cells are non-negative numeric.

# Contributor flow

0.  One-time setup (anyone cloning):

    ```         
    git lfs install
    python -m venv .venv && .venv/bin/pip install -r tools/requirements.txt
    ```

    LFS is required because binary raw blobs (`*.xlsx`, `*.zip`, `*.pdf`, `*.tif`, etc.) under `data/*/raw/` are stored via Git LFS — see `.gitattributes`.

1.  Create `data/<your_dataset>/` with `raw/`, `metadata.yaml`, and (when you have outputs) `process.{py,R}` + `processed/`.

2.  Make sure your processed filenames match the contract above. Add any name aliases your data uses to `data/aliases.csv`.

3.  Run unit tests + QA locally:

    ```         
    .venv/bin/python -m pytest tests/
    .venv/bin/python -m tools.qa
    ```

4.  Rebuild the merged GeoJSON if you changed any vector data:

    ```         
    .venv/bin/python -m tools.build_geojson
    ```

5.  Open a PR. CI runs `pytest` + `tools.qa` and blocks merge on any failures. Merges to `main` are manual.

# Citation

Please cite the original data providers (links above) and this repository if any code or derived data is reused.

# License and warranty

The repository code is licensed under the terms in LICENSE. We do not claim ownership of or the right to license the third-party data or software tools used. Please pass forward any existing license/warranty/copyright information when redistributing.

*THE DATA AND SOFTWARE ARE PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT.*
