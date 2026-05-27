# QA report: grid3_healthsites

_Checked: 2026-05-27T14:33:33+00:00_

**Status counts:** {'pass': 1, 'warn': 2}

## `metadata.yaml` (metadata) — **pass**

## `grid3_healthsites__healthsite_count__static.csv` (vector) — **warn**
- rows: 519
- zones covered: 519 / 519
- resolution: static
- reasons:
  - 1 empty column header(s); likely R write.csv without row.names=FALSE (warn)

## `grid3_healthsites__healthsite_density__static.csv` (vector) — **warn**
- rows: 519
- zones covered: 519 / 519
- resolution: static
- reasons:
  - 1 empty column header(s); likely R write.csv without row.names=FALSE (warn)
