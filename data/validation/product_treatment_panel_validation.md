# Product Treatment Panel Validation

- Generated at UTC: `2026-07-19T12:36:18.582471+00:00`
- Output: `data/processed/harmonized/product_treatment_hs6_year.parquet`
- Validation status: **PASS**
- Output rows: `57222`

## Required checks

- Configured input SHA256 checks: `yes`
- Unique `analysis_hs6 × year`: `yes`
- Complete product-year grid: `yes`
- All treatment rates and shares within [0, 1]: `yes`
- Pre-2018 treatment is zero: `yes`
- Weighted imports and exposure numerator reconcile: `yes`
- Gross statutory interpretation flags are fixed: `yes`

## Source and mapping coverage

- Section 301 source rows: `55308` across `5028` HS2017 codes.
- Complete BACI HS2017 weight universe: `5384` codes.
- BACI weight codes absent from the legal exposure panel: `356`; these receive explicit not-listed rate zero before aggregation.
- Analysis products receiving multiple HS2017 source codes: `108`; their rates use documented import weights.

## Tariffed analysis products by year

| Year | Tariffed analysis HS6 |
|---:|---:|
| 2014 | 0 |
| 2015 | 0 |
| 2016 | 0 |
| 2017 | 0 |
| 2018 | 3574 |
| 2019 | 4865 |
| 2020 | 4865 |
| 2021 | 4865 |
| 2022 | 4865 |
| 2023 | 4865 |
| 2024 | 4865 |

## Interpretation

The panel measures gross statutory initial-action exposure, not realized duties. Historical exclusions are not applied, and the 2024 four-year-review changes remain a separate extension. When several HS2017 codes map to one HS2012/CEPII product, the aggregate China share is recomputed from import values and the tariff rate is China-import weighted; this preserves the exposure numerator and prevents many-to-one value inflation. Products without a 2017 import denominator retain missing share/exposure rather than a fabricated zero share.
