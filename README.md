# Bundibugyo Ebola virus outbreak 2026

Data for the 2026 Bundibugyo Ebolavirus (BDBV) outbreak.

![Logos for Project Lead Organizations: Institute National de Recherche Biomedicale (INRB), One Health Institute for Africa (INOHA), Institut National de Santé Publique (INSP), and Unité de Modélisation et Intelligence Epidémique (UMIE)](https://scarpino.github.io/files/drc_logos.png)

This work is led by the Institut National de Recherche Biomédicale (INRB) Kinshasa/One Health Institute for Africa (INOHA) Kinshasa (Dav Ebengo, Placide Mbala-Kingebeni and Tania Bishola), and the Institut National de Santé Publique (INSP) (Pierre Akilimali, Adelard Lofungola) in collaboration with partners across the University of Oxford and Northeastern University; please contact [dav.ebengo\@umie-inrb.org](mailto:dav.ebengo@umie-inrb.org) or [pierre.akilimali\@insp.cd](mailto:pierre.akilimali@insp.cd) for further information.

Last successful build: **26 May 2026, 09:59:00 (UTC)** — `build/` on `main` at commit [`683a564`](https://github.com/kraemer-lab/Ebola_DRC_2026/commit/683a564fe31b812f284f0cecee8abf7e85faa146) (data snapshot [`683a564`](https://github.com/kraemer-lab/Ebola_DRC_2026/commit/683a564), see `build/manifest.json`).

# Data sources

-   **DRC health zones:** [Humanitarian Data Exchange](https://data.humdata.org/dataset/drc-health-data) (MoH zones de santé shapefile)
-   **Epidemiological data (Processed Linelists, INSP):** Following establishment of an epi data collection pipeline by INSP and INRB, aggregated linelist data will be housed in (`data/epi/`) - ETA for this by Friday 29th
-   **Epidemiological & operational data (INSP):** [Institut National de Santé Publique (INSP)](https://insp.cd/) SitRep MVE PDF series (`data/insp_sitrep/`, currently through **SitRep 010**) — daily case, death, and contact-tracing indicators by health zone **manually transcribed from the sitreps**
-   **Road travel times:** [OSRM](http://project-osrm.org/) public demo (`data/osrm/`, matrix outputs)
-   **Cross-border travel:** [Imperial College Report](https://www.imperial.ac.uk/mrc-global-infectious-disease-analysis/research-themes/preparedness-and-response-to-emerging-threats/report-ebola-18-05-2026/)
-   **Conflicts and acts of violence:** [ACLED](https://acleddata.com)
-   **Internal relocations:** International Organisation for Migrants ([IOM](https://dtm.iom.int))
-   **Population size rasters:** [GRID3 v4.4 gridded population](https://data.grid3.org/maps/a3db539c0fae4c05aed92ed67e11fe2b/about)
-   **Health facilities (GRID3):** [GRID3 COD Health Facilities v8.0](https://data.grid3.org/datasets/GRID3::grid3-cod-health-facilities-v8-0/about) (`data/grid3_healthsites/`)
-   **Health facilities (OSM / crowdsourced):** [Healthsites.io](https://healthsites.io/) (`data/healthsites_io/`)
-   **Mobile phone-based internal relocation estimates:** [Flowminder.org](https://www.flowminder.org/resources/publications-reports/drc-reports-publications)

For the latest BDBV genomic data, please visit [Pathoplexus](https://pathoplexus.org/ebola-bdbv/search).

## Pending data sources

We are tracking pending data sources over on the [issues tab](https://github.com/kraemer-lab/Ebola_DRC_2026/issues). If you want to request a specific publicly available dataset, raise an issue (although raising an issue does not guarantee that we will incorporate a dataset).

# Current build (2026-05-26)

Snapshot of `build/drc_health_zones.geojson` (519 zones, **25** embedded vector layers, \~26 MB) and the matrix catalogue. **26 May 2026, 09:47:13 (UTC)** — `build/` on `main` at commit [`ad7f46c`](https://github.com/kraemer-lab/Ebola_DRC_2026/commit/ad7f46cac54a35f219d4c7939a5e4f12862dcc1f) (data snapshot [`ad7f46c`](https://github.com/kraemer-lab/Ebola_DRC_2026/commit/ad7f46c), see `build/manifest.json`). Re-run `python -m tools.build_geojson` after pulling to regenerate locally; `build/manifest.json` carries the same information in machine-readable form.

<!-- whats-new:start -->

-   INSP Sitrep data through report 010

-   First release officially hosted by INRB

<!-- whats-new:end -->

**Embedded in the GeoJSON** — each per-zone vector output appears under `feature.properties.<dataset>.<metric>` (matrices are excluded; see below). Daily series use the latest `date` per zone in the build snapshot:

| Folder | Output | Retrieved | Status |
|------------------|------------------|------------------|------------------|
| ccvi | `ccvi__socioeconomic_deprivation__static.csv` | 2026-05-20 | active |
| ccvi | `ccvi__socioeconomic_inequality__static.csv` | 2026-05-20 | active |
| cross-border-movements | `cross_border__poe_passengers__static.csv` | 2026-05-18 | active |
| epi | `epi__cases__weekly.csv` | 2026-05-18 | active |
| fao_lccs | `fao_lccs__urban_fraction__static.csv` | 2026-05-20 | active |
| gdp_pc | `gdp_pc__gdp_pc__static.csv` | 2026-05-20 | active |
| grid3_healthsites | `grid3_healthsites__healthsite_count__static.csv` | 2026-05-20 | active |
| grid3_healthsites | `grid3_healthsites__healthsite_density__static.csv` | 2026-05-20 | active |
| healthsites_io | `healthsites_io__healthsite_count__static.csv` | 2026-05-20 | active |
| healthsites_io | `healthsites_io__healthsite_density__static.csv` | 2026-05-20 | active |
| insp_sitrep | `insp_sitrep__contacts_seen__daily.csv` | 2026-05-20 | active |
| insp_sitrep | `insp_sitrep__cumulative_confirmed_cases__daily.csv` | 2026-05-20 | active |
| insp_sitrep | `insp_sitrep__cumulative_confirmed_deaths__daily.csv` | 2026-05-20 | active |
| insp_sitrep | `insp_sitrep__cumulative_contacts_isolated__daily.csv` | 2026-05-20 | active |
| insp_sitrep | `insp_sitrep__cumulative_contacts_traced__daily.csv` | 2026-05-20 | active |
| insp_sitrep | `insp_sitrep__cumulative_suspected_cases__daily.csv` | 2026-05-20 | active |
| insp_sitrep | `insp_sitrep__cumulative_suspected_deaths__daily.csv` | 2026-05-20 | active |
| insp_sitrep | `insp_sitrep__new_confirmed_cases__daily.csv` | 2026-05-20 | active |
| insp_sitrep | `insp_sitrep__new_contacts_isolated__daily.csv` | 2026-05-20 | active |
| insp_sitrep | `insp_sitrep__new_contacts_listed__daily.csv` | 2026-05-20 | active |
| insp_sitrep | `insp_sitrep__new_suspected_cases__daily.csv` | 2026-05-20 | active |
| insp_sitrep | `insp_sitrep__new_suspected_deaths__daily.csv` | 2026-05-20 | active |
| refugee_sites | `refugee_sites__sites__static.csv` | 2026-05-20 | active |
| worldpop | `worldpop__pop_count__static.csv` | 2026-05-20 | active |
| worldpop | `worldpop__pop_density__static.csv` | 2026-05-20 | active |

**Matrix outputs** — large origin–destination tables (519×519 for national sources). Not merged into `build/drc_health_zones.geojson`; use the files under `data/<dataset>/processed/` or the catalogue in `qa/matrix_log.csv`.

| Folder     | Output                                   | Retrieved  | Status |
|------------|------------------------------------------|------------|--------|
| osrm       | `osrm__travel_time__static.matrix.csv`   | 2026-03-17 | active |
| osrm       | `osrm__road_distance__static.matrix.csv` | 2026-03-17 | active |
| IDP        | `idp__individuals__static.matrix.csv`    | 2026-01-31 | active |
| IDP        | `idp__individuals__weekly.matrix.csv`    | 2026-01-31 | active |
| IDP        | `idp__individuals__monthly.matrix.csv`   | 2026-01-31 | active |
| flowminder | `flowminder__inflow__static.matrix.csv`  | 2026-05-20 | active |
| flowminder | `flowminder__outflow__static.matrix.csv` | 2026-05-20 | active |

**Notes:** \``grid3_healthsites` and `healthsites_io` both supply facility count/density — GRID3 is the MoH/partner master list. OSRM matrices may contain `NA` for unroutable pairs (QA warn). Dataset index: [`data/README.md`](data/README.md).

**Not in build**: `ACLED_conflict` — province-grain placeholder, no QA-passing output yet.

## Past releases

<!-- past-releases:start -->

| Tag | Date | Summary | Download |
|----------------|----------------|-------------------|----------------------|
| [`build-2026-05-26-ad7f46c`](https://github.com/INRB-UMIE/Ebola_DRC_2026/releases/tag/build-2026-05-26-ad7f46c) | 2026-05-26 | First INRB release on 26 May 2026, includes SitRep 010 | [release](https://github.com/INRB-UMIE/Ebola_DRC_2026/releases/tag/build-2026-05-26-ad7f46c) |
| [`build-2026-05-22-12db0c2`](https://github.com/kraemer-lab/Ebola_DRC_2026/releases/tag/build-2026-05-22-12db0c2) | 2026-05-22 | 25 vector layers; INSP through SitRep 007 + GRID3 health facilities | [release](https://github.com/kraemer-lab/Ebola_DRC_2026/releases/tag/build-2026-05-22-12db0c2) |
| [`build-2026-05-22-9694d10`](https://github.com/kraemer-lab/Ebola_DRC_2026/releases/tag/build-2026-05-22-9694d10) | 2026-05-22 | First GitHub release (11 vector layers; pre-INSP / pre-GRID3) | [release](https://github.com/kraemer-lab/Ebola_DRC_2026/releases/tag/build-2026-05-22-9694d10) |

<!-- past-releases:end -->

# Repository layout

```         
data/
  README.md                  index of all dataset folders
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

**Vector files** carry a `nom` column. Non-static resolutions also carry a `date` column (ISO 8601).

**Matrix files** (`.matrix.csv`): snapshot matrices have header `nom, <dest_nom_1>, ...`; time-series matrices have `date, nom, <dest_nom_1>, ...`. Present cells must be non-negative numeric; missing values may be empty or `NA` (e.g. unroutable OSRM pairs).

# Contributor flow

0.  One-time setup (anyone cloning):

    ```         
    git lfs install
    python -m venv .venv && .venv/bin/pip install -r tools/requirements.txt
    ```

    LFS is required because binary raw blobs (`*.xlsx`, `*.zip`, `*.pdf`, `*.tif`, etc.) under `data/*/raw/` are stored via Git LFS — see `.gitattributes`.

    Additionally, maintainers who will cut releases need:

    -   `gh` CLI installed and authenticated (`gh auth login`).
    -   `$EDITOR` environment variable set (used by `tools.release` for the description prompt).

1.  Create `data/<your_dataset>/` with `raw/`, `metadata.yaml`, and (when you have outputs) `process.{py,R}` + `processed/`.

2.  Make sure your processed filenames match the contract above. Add any name aliases your data uses to `data/aliases.csv`.

3.  Sync with main using `git merge origin/main`. This is important, as if anyone else has made changes (e.g. adding a dataset), their QA reports will reflect a different timestamp to what your current branch expects on main, resulting in a lot of conflicts after you run the QA tests in the next step.

4.  Run unit tests + QA locally:

    ```         
    .venv/bin/python -m pytest tests/
    .venv/bin/python -m tools.qa
    ```

5.  Rebuild the merged GeoJSON if you changed any vector data:

    ```         
    .venv/bin/python -m tools.build_geojson
    ```

    On success, `build_geojson` also updates the **Last successful build** line (and `# Current build` date) in `README.md` from `build/manifest.json`. Pass `--skip-readme` to leave the README unchanged.

6.  Open a PR. CI runs `pytest` + `tools.qa` and blocks merge on any failures.

7.  Merges to `main` are manual, and will be carried out by an admin or maintainer after they review your PR.

8.  Publishing a release (maintainer task). After a merge to `main` introduces changes worth a new public snapshot:

    ```         
    .venv/bin/python -m tools.release
    ```

    This will:

    -   archive the current `build/` (plus QA logs and the previous build's description) as a GitHub Release tagged `build-YYYY-MM-DD-<sha>`
    -   rebuild from current data
    -   open `$EDITOR` to capture a "what's new" description for the new build
    -   update `README.md` (current-build pointers + Past releases log)

    Then `git add build/ qa/*.csv qa/reports/ README.md && git commit && git push` to land the new build alongside its description.

    Use `tools.build_geojson` (not `tools.release`) for normal local iteration — `tools.release` is only for cutting versioned snapshots.

# Citation

Please cite the original data providers (links above) and this repository if any code or derived data is reused.

# License and warranty

The repository code is licensed under the terms in LICENSE. We do not claim ownership of or the right to license the third-party data or software tools used. Please pass forward any existing license/warranty/copyright information when redistributing.

*THE DATA AND SOFTWARE ARE PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT.*
