# QA report: osrm

_Checked: 2026-05-27T14:33:33+00:00_

**Status counts:** {'pass': 1, 'warn': 2}

## `metadata.yaml` (metadata) — **pass**

## `osrm__road_distance__static.matrix.csv` (matrix) — **warn**
- rows: 519
- cols: 519
- zones covered: 519 / 519
- resolution: static
- square: True
- reasons:
  - 1036 missing cells (empty/NA) (warn)

## `osrm__travel_time__static.matrix.csv` (matrix) — **warn**
- rows: 519
- cols: 519
- zones covered: 519 / 519
- resolution: static
- square: True
- reasons:
  - 1036 missing cells (empty/NA) (warn)
