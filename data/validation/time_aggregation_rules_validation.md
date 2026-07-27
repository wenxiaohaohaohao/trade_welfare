# Time Aggregation Rules Validation

- Generated at UTC: `2026-07-19T11:28:56.440610+00:00`
- Output: `data/processed/concordances/time_aggregation_rules.parquet`
- SHA256: `94c9b5ee7e7f6bc91fcf67a251a0cb39c2aa64b1303fdce7948280039899bfb4`
- Rule rows: `39`
- Inputs: `8`
- Duplicate input-metric keys: `0`
- Validation status: **PASS**

## Required temporal checks

- Census source contains all 12 requested months in each 2014-2024 year: `yes`
- Census quantity remains structurally unavailable: `yes`
- Mexico complete calendar years: `2006-2023`
- Mexico partial calendar years: `{"2024": [1, 2]}`
- Mexico country-sector-year groups with incomplete quarters: `8059`
- Mexico country-sector-year groups with at least one confidential quarter: `46593`
- BEA position protected as a stock: `yes`
- ICIO restricted to observed 2017/2018/2022 benchmarks: `yes`

## Interpretation

Census additive values may be summed over reported monthly rows while retaining the monthly interface and a months-with-records diagnostic. Mexico FDI may be summed to a calendar-year value only when all four quarters are present and none is confidential; 2024 contains Q1-Q2 only and is not a full-year observation. BEA direct-investment position remains a stock and is never summed across time. ICIO missing years are not imputed.
