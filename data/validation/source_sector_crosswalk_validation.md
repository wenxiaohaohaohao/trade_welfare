# Source-Sector Crosswalk Validation

- Generated at UTC: `2026-07-19T12:28:09.395676+00:00`
- Output: `data/processed/concordances/source_sector_crosswalk.parquet`
- Validation status: **PASS**
- Crosswalk rows: `517`

## Source code coverage

| Source | Observed codes | Crosswalk codes | Explicit-status coverage |
|---|---:|---:|---:|
| `oecd_icio` | 50 | 50 | 100.000000% |
| `oecd_amne` | 39 | 39 | 100.000000% |
| `bea_mne` | 16 | 16 | 100.000000% |
| `bea_fdi` | 20 | 20 | 100.000000% |
| `mexico_fdi` | 392 | 392 | 100.000000% |

## Required safeguards

- Unique source-level-code keys: `yes`
- Eligible mappings have weight 1; all others have null weight: `yes`
- Ambiguous mappings have no numeric weight: `yes`
- Mexico sector/subsector aggregates excluded from the main join: `yes`
- BEA transportation equipment retained only as an autos proxy: `yes`
- Mexico SCIAN 3345 retained as an unweighted mixed sector: `yes`

## Priority-sector support

| Source | Directly supported priority sectors |
|---|---|
| `oecd_icio` | electronics, electrical_equipment, machinery, autos, textiles_apparel |
| `oecd_amne` | electronics, electrical_equipment, machinery, autos, textiles_apparel |
| `bea_mne` | electronics, electrical_equipment, machinery |
| `bea_fdi` | electronics, electrical_equipment, machinery |
| `mexico_fdi` | electronics, electrical_equipment, machinery, autos, medical_devices, textiles_apparel |

## Interpretation

This crosswalk records what each published source can support at its actual industry granularity. It does not split coarse sectors with equal weights. OECD C26 and BEA computer/electronics cannot separately identify all medical devices. BEA transportation equipment is broader than autos and is therefore only a documented proxy. Mexico uses industry-group rows for the main join; its coexisting sector and subsector aggregates are isolated to prevent double counting.
