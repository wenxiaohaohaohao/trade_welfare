# M3.1 Connector Trade Sector Panel Validation

## Material Passport

- Origin Skill: `academic-research-suite/experiment-agent`
- Origin Mode: `run + validate`
- Origin Date: `2026-07-28`
- Verification Status: `VERIFIED`
- Version Label: `connector_trade_sector_rules_v1`

## Result

- Validation status: **PASS**
- Output: `data/processed/harmonized/connector_trade_sector_year.parquet`
- Output rows: `1001`
- Natural-key duplicates: `0`
- Connectors / sectors / years: `13 / 7 / 11`
- Eligible / excluded products: `4237 / 965`
- Deterministic Parquet SHA256 match: `yes`

## Required checks

- Configured input SHA256 checks: `yes`
- All products matched the canonical crosswalk: `yes`
- Embedded M2 product fields equal canonical crosswalk: `yes`
- Expected 1,001-row complete sector grid: `yes`
- Zero-denominator / no-HS2017-mapping eligible products retained: `17 / 11`
- TWN proxy rows valid: `yes`
- Required numeric missing count: `0`
- Stata alias map complete/unique/<=32 characters: `yes` (70 aliases; maximum length 14)

## Eligible product counts by sector

| Analysis sector | Eligible HS6 count |
|---|---:|
| `autos` | 64 |
| `electrical_equipment` | 177 |
| `electronics` | 252 |
| `machinery` | 467 |
| `medical_devices` | 32 |
| `other_manufacturing` | 2422 |
| `textiles_apparel` | 823 |

## Trade-flow reconciliation

| Flow | Eligible input USD | Sector output USD | Global gap USD | Max connector-year gap USD | Excluded gap USD | Full-universe gap USD | Share gap |
|---|---:|---:|---:|---:|---:|---:|---:|
| `china_to_connector_value_usd` | 7277654649355.00 | 7277654649355.00 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000e+00 |
| `east_asia_to_connector_value_usd` | 11664115552239.00 | 11664115552239.00 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000e+00 |
| `connector_to_usa_value_usd` | 9871984981362.00 | 9871984981362.00 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000e+00 |
| `china_to_usa_value_usd` | 67908975727203.00 | 67908975727203.00 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000e+00 |

## Policy formula checks

| Field | Maximum absolute formula gap |
|---|---:|
| `sector_tariff_rate_china_weighted` | 0.000e+00 |
| `sector_tariff_exposure` | 0.000e+00 |
| `sector_china_import_share_2017` | 0.000e+00 |
| `tariffed_product_share_count` | 0.000e+00 |
| `tariffed_product_share_china_value` | 0.000e+00 |
| `tariffed_product_share_us_value` | 0.000e+00 |
| `treatment_missing_denominator_product_share` | 0.000e+00 |
| `treatment_zero_denominator_product_share` | 0.000e+00 |
| `treatment_no_hs17_mapping_product_share` | 0.000e+00 |

## Interpretation boundaries

- The output is an annual connector-sector panel only. It does not contain pre/shock/post windows, growth rates, replacement ratios, rankings, production-side variables, or structural moments.
- China-to-USA and policy fields repeat across connectors for comparison and are non-additive across connectors.
- Coverage fields repeat across sectors within connector-year and are non-additive across sectors.
- Section 301 remains gross statutory initial-action exposure without historical exclusions or the separate 2024 review extension.
- `source_row_count=0` product states remain visible through flow-specific zero-source product counts; they are not confused with observed zero-value rows.
