# BEA U.S. MNE Affiliate Country-Industry Panel Usage Note

## Source

- Source family: BEA Activities of U.S. Multinational Enterprises, Majority-Owned Foreign Affiliates.
- Main release page: https://www.bea.gov/news/2025/activities-us-multinational-enterprises-2023
- Download table page: https://www.bea.gov/international/di1usdop
- Release/vintage used by the build: annual comprehensive tables for 2017-2023, with 2023 preliminary from the 2025-08 release.
- Build script: `code/data_build/build_bea_us_mne_affiliate_country_industry.py`

## Output

The reproducible output is:

`data/interim/mne/bea_us_mne_affiliate_country_industry.parquet`

Current complete-field coverage is 2017-2023. If the project later needs years before 2017, download and validate those older BEA annual files as a separate extension rather than mixing them into this completed Batch 5 build.

Minimum fields:

- `year`
- `affiliate_country`
- `industry`
- `employment`
- `sales`
- `value_added`
- `capital_expenditures`
- `goods_exports_to_us`
- `goods_imports_from_us`

## Field Definitions

| Output field | BEA table | Unit | Interpretation |
|---|---|---|---|
| `employment` | II.G 1 | Thousands of employees | Employment of majority-owned foreign affiliates by affiliate country and industry. |
| `sales` | II.D 3 | Millions of dollars | Sales by affiliates by affiliate country and industry. |
| `value_added` | II.F 3 | Millions of dollars | Value added of affiliates by affiliate country and industry. |
| `capital_expenditures` | II.C 4 | Millions of dollars | Expenditures for property, plant, and equipment by affiliates; used as the capital-expenditure measure. |
| `goods_exports_to_us` | II.H 11 | Millions of dollars | U.S. imports of goods shipped by affiliates; affiliate-side interpretation is goods exported to the United States. |
| `goods_imports_from_us` | II.H 3 | Millions of dollars | U.S. exports of goods shipped to affiliates; affiliate-side interpretation is goods imported from the United States. |

## Data Rules

- `(D)` is BEA disclosure suppression. Employment tables can also use size-range codes `A/F/G/H/I/J/K/L/M` for suppressed cells. These are stored as missing in the numeric field and marked by `*_suppressed = true`.
- `(*)` is a rounded small value. It is stored as `0.0` and marked by `*_small_value = true`.
- Other nonnumeric BEA codes are preserved in `*_raw_code`; the numeric field is missing.
- BEA tables contain aggregate geography rows such as `All countries`, `Europe`, and `Asia and Pacific`. Use `bea_area_type` before country-only analysis.

## Research Use

This panel is suitable for checking whether U.S. MNE majority-owned foreign affiliate activity expands in connector countries such as Mexico, Canada, and Vietnam. It supports Scenario B as incumbent affiliate activity evidence and can support Scenario C only when combined with broader production, FDI-flow, or project-level evidence. It does not identify firm-level relocation by itself.
