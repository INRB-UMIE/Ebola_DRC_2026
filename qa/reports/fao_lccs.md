# QA report: fao_lccs

_Checked: 2026-05-27T22:00:42+00:00_

**Status counts:** {'pass': 1, 'warn': 1}

## `metadata.yaml` (metadata) — **pass**

## `fao_lccs__urban_fraction__static.csv` (vector) — **warn**
- rows: 519
- zones covered: 519 / 519
- resolution: static
- reasons:
  - 1 empty column header(s); likely R write.csv without row.names=FALSE (warn)
