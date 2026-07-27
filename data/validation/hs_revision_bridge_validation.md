# HS Revision Bridge Validation

- Generated at UTC: `2026-07-19T11:53:34.346455+00:00`
- Canonical conversion: `data/processed/concordances/hs_to_hs2012_conversion.parquet`
- Full correlation: `data/processed/concordances/hs_revision_correlations.parquet`
- Census year-code crosswalk: `data/processed/concordances/census_hs6_year_to_hs2012.parquet`
- Conversion rows: `16209`
- Correlation rows: `27726`
- Validation status: **PASS**

## Conversion coverage

| Input | Revision | Unique codes | Unmapped codes | Row coverage | Gross value coverage | Eligible value coverage |
|---|---:|---:|---:|---:|---:|---:|
| `baci_hs17_us_imports_2017` | `HS2017` | 5384 | 0 | 100.000000% | 100.000000% | 100.000000% |
| `section301_hs6_exposure` | `HS2017` | 5028 | 0 | 100.000000% | 100.000000% | 100.000000% |
| `us_census_hs6_monthly_2014_2016` | `HS2012` | 5133 | 13 | 99.723582% | 97.337655% | 99.997742% |
| `us_census_hs6_monthly_2017_2021` | `HS2017` | 5326 | 10 | 99.758385% | 97.192253% | 99.997802% |
| `us_census_hs6_monthly_2022_2024` | `HS2022` | 5496 | 9 | 99.778667% | 97.373247% | 99.996285% |

## Required checks

- Official source SHA256 checks: `yes`
- One canonical conversion per source code: `yes`
- Official conversion weights all equal 1: `yes`
- WCO corrigenda reflected in HS2017-HS2012 pairs: `yes`
- Multi-target correlation rows kept without unvalidated weights: `yes`
- Minimum observed-value coverage at least 95%: `yes`

## Interpretation

The canonical conversion table uses the official UNSD one-target conversion and weight 1, so product values do not expand during revision harmonization. The full UNSD correlations are retained separately for audit and robustness. Multi-target correlation rows deliberately have no numeric mapping weight until a value-based weighting design is constructed and validated. Census HS6 is treated as HS2012 in 2014-2016, HS2017 in 2017-2021, and HS2022 in 2022-2024; HTS10 remains year-specific.
