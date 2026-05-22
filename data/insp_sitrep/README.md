# INSP situation reports (SitRep MVE) — health-zone outbreak indicators

Daily **case, death, and contact-tracing indicators** by DRC health zone, extracted from Institut National de Santé Publique (INSP) **Situation Reports** on the 2026 Bundibugyo Ebolavirus (BDBV) outbreak (PDF series `SitRep_MVE_*`).

These data complement the WHO weekly external sitreps in `data/epi/` by providing **INSP-internal reporting** at finer temporal resolution (per report date) and additional contact-tracing fields not exported in the WHO contract file.

------------------------------------------------------------------------

## About the source documents

**Publisher:** [Institut National de Santé Publique (INSP)](https://insp.cd/), Democratic Republic of the Congo.

**Series:** SitRep **MVE** (maladie à virus Ebola / outbreak situation reports), numbered `001`, `002`, `004`, `005`, `006` for 2026 in the committed `raw/` folder.

**Extraction method:** Values are **manually coded** from PDF tables and narrative sections. There is no automated PDF parser in this folder yet.

**Relationship to other repo data:**

| Folder | Source | Grain | Role |
|--------|--------|-------|------|
| `data/epi/` | WHO Weekly External Situation Report | Weekly | Official external case/death tables |
| `data/insp_sitrep/` | INSP SitRep MVE PDFs | Daily (per report date) | INSP operational indicators and contact metrics |

------------------------------------------------------------------------

## Files

| File | Description |
|------|-------------|
| `processed/insp_sitrep__*__daily.csv` | Twelve repo-contract tables (see below) |
| `raw/SitRep_MVE_001:2026.pdf` | Situation report 001 |
| `raw/SitRep_MVE_002:2026.pdf` | Situation report 002 |
| `raw/SitRep_MVE_004:2026.pdf` | Situation report 004 (**003** not in repo) |
| `raw/SitRep_MVE_005:2026.pdf` | Situation report 005 |
| `raw/SitRep_MVE_006:2026.pdf` | Situation report 006 |
| `process.R` | Normalise `nom` in all processed CSVs to canonical shapefile names |
| `metadata.yaml` | Provenance, licence, and pipeline notes |

**Coverage:** Health zones **with a row in at least one processed file** (outbreak-affected subset; not all 519 national zones).

**Temporal scope:** Report dates **2026-05-14** through **2026-05-20** in the current commit (grows as new sitreps are added).

------------------------------------------------------------------------

## Processed outputs (filename contract)

Processed files follow the repo grammar documented in `tools/lib/schema.py`:

```text
<dataset>__<metric>__<resolution>.csv
```

For this folder: **`insp_sitrep__<metric>__daily.csv`**.

| Processed file | Metric column | Description |
|----------------|---------------|-------------|
| `insp_sitrep__new_suspected_cases__daily.csv` | `new_suspected_cases` | New suspected cases since previous report |
| `insp_sitrep__cumulative_suspected_cases__daily.csv` | `cumulative_suspected_cases` | Cumulative suspected cases |
| `insp_sitrep__new_confirmed_cases__daily.csv` | `new_confirmed_cases` | New confirmed cases |
| `insp_sitrep__cumulative_confirmed_cases__daily.csv` | `cumulative_confirmed_cases` | Cumulative confirmed cases |
| `insp_sitrep__new_suspected_deaths__daily.csv` | `new_suspected_deaths` | New suspected deaths |
| `insp_sitrep__cumulative_suspected_deaths__daily.csv` | `cumulative_suspected_deaths` | Cumulative suspected deaths |
| `insp_sitrep__cumulative_confirmed_deaths__daily.csv` | `cumulative_confirmed_deaths` | Cumulative confirmed deaths |
| `insp_sitrep__new_contacts_listed__daily.csv` | `new_contacts_listed` | New contacts listed for follow-up |
| `insp_sitrep__cumulative_contacts_traced__daily.csv` | `cumulative_contacts_traced` | Cumulative contacts traced |
| `insp_sitrep__new_contacts_isolated__daily.csv` | `new_contacts_isolated` | New contacts placed in isolation |
| `insp_sitrep__cumulative_contacts_isolated__daily.csv` | `cumulative_contacts_isolated` | Cumulative contacts in isolation |
| `insp_sitrep__contacts_seen__daily.csv` | `contacts_seen` | Contacts seen / followed up (as reported) |

**Zones in current data (canonical `nom`):** Bambu, Bunia, Butembo, Goma, Katwa, Mongbalu, Nyakunde, Rwampara.

------------------------------------------------------------------------

## CSV contract

Each file is a **long-format vector** time series:

| Column | Description |
|--------|-------------|
| `nom` | **Canonical** health-zone name (`Nom` from `data/shapefiles/DRC_Health_zones.shp`, with province suffix where the shapefile requires it, e.g. `Bili (Nord-Ubangi)`). After `process.R`, `nom` must pass repo QA (`tools/lib/schema.py`). |
| `date` | ISO date (`YYYY-MM-DD`) of the situation report (data-as-of date for that extract) |
| `<metric>` | Numeric count for that zone and date, or **`ND`** when not reported / not disclosed in that sitrep |

**Uniqueness:** One row per (`nom`, `date`) within each file.

**Missing values:** The literal string `ND` is used in source tables where a cell is blank or marked not disponible; consumers should treat `ND` as missing for modelling.

**Example (R):**

```r
library(here)

cases <- read.csv(
  here("data/insp_sitrep/processed/insp_sitrep__cumulative_confirmed_cases__daily.csv"),
  na.strings = "ND"
)
cases[cases$date == "2026-05-20", c("nom", "cumulative_confirmed_cases")]
```

Join to other datasets on **`nom`**, or on **`ZSCode`** from the shapefile when names are ambiguous.

------------------------------------------------------------------------

## Method (this repo)

### 1. Manual extraction

1. Add each new `SitRep_MVE_###:2026.pdf` under `raw/`.
2. Transcribe zone-level counts into the appropriate `processed/insp_sitrep__<metric>__daily.csv` files.
3. Use **spellings as they appear in the PDF** in `nom` (e.g. `Mongbwalu`, `Nyankunde`). Excel exports may include a UTF-8 BOM; that is fine before running `process.R`.

### 2. Name normalisation (`process.R`)

`process.R` rewrites `nom` in every `processed/insp_sitrep__*__daily.csv` to match the **same canonical contract** as Python QA and `tools/build_geojson`:

1. Load `data/shapefiles/DRC_Health_zones.shp` and build 519 canonical names (province suffix for duplicate `Nom` values, currently **Bili** and **Lubunga**).
2. Load `data/aliases.csv` and map observed labels to canonical `nom` (shared across datasets; e.g. `Mongbwalu` → `Mongbalu`, `Nyankunde` → `Nyakunde`).
3. Overwrite each processed CSV in place (`row.names = FALSE`, unquoted UTF-8).

The script **stops with an error** if any `nom` cannot be resolved, or if two rows share the same (`nom`, `date`) after mapping. Add a row to `data/aliases.csv` (with `source_dataset: insp_sitrep` in the notes column) before re-running.

### 3. QA and build

From the repository root:

```bash
Rscript data/insp_sitrep/process.R
python -m tools.qa insp_sitrep
```

Then, if applicable: `python -m tools.build_geojson`.

------------------------------------------------------------------------

## Regenerating outputs

After a new sitrep:

1. Commit the PDF under `raw/`.
2. Append rows to the relevant `processed/*.csv` files using PDF zone labels in `nom`.
3. Run name normalisation and QA (commands above).

**R packages:** `sf`, `here` (installed automatically if missing when the script runs).

**Overwrites:** All twelve `processed/insp_sitrep__*__daily.csv` files (only the `nom` column changes unless you added new rows in step 2).

------------------------------------------------------------------------

## Data quality and limitations

| Issue | Detail |
|-------|--------|
| **Manual transcription** | Values depend on human reading of PDF tables; verify against source PDFs before release. |
| **Partial national coverage** | Only zones reported in INSP sitreps appear; absence of a zone is not evidence of zero cases. |
| **`ND` cells** | Not all metrics are published for every zone on every date; do not impute without source confirmation. |
| **Name variants** | Transcribe PDF labels first; unresolved names require new rows in `data/aliases.csv`, then `process.R`. |
| **Missing sitrep 003** | `SitRep_MVE_003:2026.pdf` is not in `raw/`; date series may have gaps between 002 and 004. |
| **Date semantics** | `date` is the sitrep **report date**, not necessarily onset or specimen collection date. |
| **No confirmed-death “new” file** | Only cumulative confirmed deaths are exported; add `new_confirmed_deaths` if sitreps report it consistently. |
| **No PDF automation** | `process.R` does not parse PDFs; it only normalises zone names in existing CSVs. |

------------------------------------------------------------------------

## Provenance

- **Reports:** INSP SitRep MVE series (`raw/SitRep_MVE_*.pdf`).
- **Geometry (for maps):** `data/shapefiles/DRC_Health_zones.shp`.
- **Zone aliases:** `data/aliases.csv`.
- **Metadata:** `metadata.yaml`.
- **Project contact (INSP):** [pierre.akilimali@insp.cd](mailto:pierre.akilimali@insp.cd) (see repository root `README.md`).

For project-wide data conventions, see `data/README.md`.
