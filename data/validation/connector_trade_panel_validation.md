# Connector Trade Panel Validation

- Generated at UTC: `2026-07-19T12:43:15.948031+00:00`
- Output: `data/processed/harmonized/connector_trade_legs_hs6_year.parquet`
- Validation status: **PASS**
- Output rows: `743886`

## Required checks

- Configured input SHA256 checks: `yes`
- Unique connector-product-year key: `yes`
- Complete connector-product-year grid: `yes`
- Nonnegative BACI trade values: `yes`
- China-to-USA benchmark identical for every connector: `yes`
- Taiwan retains BACI S19 proxy flag: `yes`
- East Asia self-trade exclusion flags pass: `yes`

## Trade-leg reconciliation

| Leg | Source total USD | Output total USD | Gap USD |
|---|---:|---:|---:|
| `china_to_connector` | 8021758704297.00 | 8021758704297.00 | 0.000000 |
| `east_asia_to_connector` | 13242306197894.00 | 13242306197894.00 | 0.000000 |
| `connector_to_usa` | 12370620858085.00 | 12370620858085.00 | 0.000000 |

## Interpretation

The output is a completed grid for all configured connector candidates, BACI/CEPII products, and 2014-2024 years. A missing BACI bilateral product row is recorded as zero value with zero source-row count. The East Asia source leg excludes canonical self-trade for KOR and TWN connector rows. China-to-USA is a common product-year benchmark repeated only to support within-connector comparisons; it must never be summed across connectors. BACI quantity is omitted because its source missingness is not interpretable as zero.
