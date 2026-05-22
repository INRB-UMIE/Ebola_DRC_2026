# QA report: worldpop

_Checked: 2026-05-22T18:27:11+00:00_

**Status counts:** {'pass': 1, 'warn': 2}

## `metadata.yaml` (metadata) — **pass**

## `worldpop__pop_count__static.csv` (vector) — **warn**
- rows: 519
- zones covered: 519 / 519
- resolution: static
- reasons:
  - 1 empty column header(s); likely R write.csv without row.names=FALSE (warn)

## `worldpop__pop_density__static.csv` (vector) — **warn**
- rows: 519
- zones covered: 519 / 519
- resolution: static
- reasons:
  - 1 empty column header(s); likely R write.csv without row.names=FALSE (warn)
