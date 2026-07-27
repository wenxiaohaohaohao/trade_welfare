# Trade-Treatment Merge Validation

- Generated at UTC: `2026-07-19T12:45:10.660430+00:00`
- Output: `data/processed/harmonized/connector_trade_hs6_year.parquet`
- Validation status: **PASS**
- Output rows: `743886`

## Required checks

- Configured input SHA256 checks: `yes`
- Unique connector-product-year output key: `yes`
- All trade rows matched treatment: `yes`
- Product/sector fields identical across inputs: `yes`
- Treatment constant across connectors within product-year: `yes`
- Treatment provenance complete: `yes`

## Trade-value reconciliation

| Field | Input total USD | Output total USD | Gap USD |
|---|---:|---:|---:|
| `china_to_usa_value_usd` | 69463714130434.00 | 69463714130434.00 | 0.000000 |
| `china_to_connector_value_usd` | 8021758704297.00 | 8021758704297.00 | 0.000000 |
| `east_asia_to_connector_value_usd` | 13242306197894.00 | 13242306197894.00 | 0.000000 |
| `connector_to_usa_value_usd` | 12370620858085.00 | 12370620858085.00 | 0.000000 |

## Interpretation

The merge is many-to-one from connector-product-year trade rows to product-year treatment. No trade value changes during the join. Treatment and the China-to-USA benchmark are repeated across connector rows for comparison only; they are non-additive across connectors. Section 301 remains gross statutory initial-action exposure, without historical exclusions or 2024 review changes.
