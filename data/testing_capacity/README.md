# Africa CDC decentralised PCR testing capacity

Per-zone **PCR machine counts** and **planned test throughput** from the Africa CDC Ebola laboratory decentralisation plan for eastern DRC outbreak zones.

------------------------------------------------------------------------

## Files

| File | Description |
|------|-------------|
| `raw/Plan_Decentralisation_Ebola_RDC.xlsx` | Source workbook (decentralisation plan) |
| `processed/africa_cdc__testing_capacity__static_matrix.csv` | Wide snapshot (`nom`, `date`, `PCR_machines`, `PCR_tests`) |
| `processed/testing_capacity__pcr_machines__static.csv` | Contract vector — machines per zone |
| `processed/testing_capacity__pcr_tests__static.csv` | Contract vector — planned tests per zone |
| `metadata.yaml` | Provenance and notes |

**Kind:** vector (per-zone), not an origin–destination matrix. The `*.matrix.csv` filename on the wide export is legacy naming from upstream; QA and GeoJSON use the `testing_capacity__*` contract files.

------------------------------------------------------------------------

## Regenerating outputs

If you update the wide CSV in `processed/`, split it into contract files:

```bash
python data/testing_capacity/process.py
```

Or replace `processed/africa_cdc__testing_capacity__static_matrix.csv` from
`Africa_CDC_lab_capacity/` and re-run the script.

Then from the repo root:

```bash
.venv/bin/python -m tools.qa
.venv/bin/python -m tools.build_geojson   # optional: embed in map product
```

------------------------------------------------------------------------

## Provenance

See `metadata.yaml`. Geometry/join key: canonical `nom` from `data/shapefiles/DRC_Health_zones.shp`.
