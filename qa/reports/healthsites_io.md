# QA report: healthsites_io

<<<<<<< HEAD
_Checked: 2026-05-21T14:33:08+00:00_
=======
_Checked: 2026-05-21T11:44:06+00:00_
>>>>>>> main

**Status counts:** {'pass': 1, 'warn': 2}

## `metadata.yaml` (metadata) — **pass**

## `healthsites_io__healthsite_count__static.csv` (vector) — **warn**
- rows: 519
- zones covered: 519 / 519
- resolution: static
- reasons:
  - 1 empty column header(s); likely R write.csv without row.names=FALSE (warn)

## `healthsites_io__healthsite_density__static.csv` (vector) — **warn**
- rows: 519
- zones covered: 519 / 519
- resolution: static
- reasons:
  - 1 empty column header(s); likely R write.csv without row.names=FALSE (warn)
