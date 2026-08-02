# M4.1 OECD ICIO Production-Side Validation

- Origin Date: `2026-08-02`
- Verification Status: `VERIFIED`
- Version Label: `production_icio_rules_v1`

## Result

- Validation status: **PASS**.
- Source-sector audit long: `data/processed/harmonized/production_icio_source_sector_long.parquet`; `85050 × 54`; SHA256 `266ff08c5bd26e00a08cb9f3654b7c83354d02da79cca036d65ccd68d0054110`.
- Analysis-sector long: `data/processed/harmonized/production_validation_icio_long.parquet`; `10080 × 43`; SHA256 `e8bdc6070581f5a1697adba605ef8eac3e7c40a5946779a627ec08ea673315f0`.
- Both natural keys are unique; both deterministic second-build hashes match.
- Candidate and determinism temporary directories cleaned: `True` / `True`.

## Frozen Inputs and Mapping

- OECD ICIO input: 12,150 rows, 81 geographies, 50 sectors, years 2017/2018/2022.
- All source codes match canonical country and sector crosswalks many-to-one.
- The audit long retains all 12,150 source cells × 7 metrics, including ROW, first-round exclusions, and outside-manufacturing sectors.
- Main eligibility: `3840` source cells; `8310` source cells remain outside the analysis long and are reconciled.
- Six ICIO-supported analysis sectors are retained; medical devices are not fabricated.

## Output Grid and Metrics

- Analysis grid: `80` countries × `6` sectors × 3 years × `7` metrics = `10080` rows.
- Metrics: gross output, value added, exports, imports, intermediate inputs, taxes less subsidies, and accounting residual.
- Other manufacturing sums 11 source sectors; the other five supported sectors map one-to-one.
- Different metrics are non-additive. No ICIO year is interpolated or imputed.

## Accounting and Exception Preservation

- Maximum absolute source production/sales residuals: `82.0319999999` / `238.605800002` current million USD.
- Source negative counts for value added / taxes less subsidies / production residual / sales residual: `8 / 365 / 206 / 1634`.
- Negative accounting values remain signed and are flagged; none are recoded to zero.
- Eligible plus excluded values reconcile to the full source universe for every metric.
- Source-to-analysis values reconcile within `1e-06` million USD.

## Stata and Interpretation Boundary

- Stata aliases: source long `54`, analysis long `43`; all complete, unique, legal, and at most 32 characters.
- Parquet remains canonical; .dta export remains an M7 task.
- ICIO production values are aggregate validation evidence, not firm-level relocation proof or causal estimates.
- This module does not add AMNE, BEA, FDI, national statistics, rankings, structural moments, or welfare inputs.
