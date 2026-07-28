# M3.5 Connector-Sector Common Panel Validation

- Origin Date: `2026-07-28`
- Verification Status: `VERIFIED`
- Version Label: `connector_trade_sector_common_panel_rules_v1`

## Result

- Validation status: **PASS**
- Output: `data/processed/harmonized/connector_trade_sector_common_panel.parquet`; `91 × 152`; SHA256 `36c58c229f3f43e86f7ff7570fc6a1ffe08ccb8fd3259bb5853abece3171f682`.
- Natural key: `connector_iso3, analysis_sector`; duplicate rows: `0`.
- Deterministic rebuild SHA256 match: `yes`.

## Frozen Inputs and Join

- Sector reorganization input: `91 × 92`; hash/schema/key contract `pass`.
- Product co-movement input: `91 × 49`; hash/schema/key contract `pass`.
- One-to-one join status: `{'both': 91, 'left_only': 0, 'right_only': 0}`; exact shared-field mismatches: `0`.
- Unique co-movement fields appended without transformation: `37`.

## Complete Sample and No-Selection Contract

- Connector groups: core `3`, Asian comparators `7`, other candidates `3`; rows by group `21 / 49 / 21`.
- All 13 connectors retain all 7 sectors; total cells: `91`.
- `comparison_sample_included`, sector-source match, and co-movement-source match are true for every row.
- Outcome-based selection, top-rank filtering, complete-case filtering, ranking construction, production integration, and M3.6 sensitivity construction are all false for every row.

## Preserved States

- Replacement ratio defined / missing / positive-gain candidate: `26 / 65 / 22`.
- China/East Asia ordinary and weighted product correlations remain defined for all 91 cells; all low-n counts remain zero.
- TWN rows: `7`; proxy flag retained on every TWN row.
- Stata aliases: `152` complete and unique; maximum length `14`.

## Interpretation Boundary

This file is a complete comparison panel, not a ranked or selected winner sample. It combines two M3.4 tables at their shared connector-sector grain and does not create M3.6 sensitivity variables, production-side evidence, structural moments, or causal rerouting estimates.
