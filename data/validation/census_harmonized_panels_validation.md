# Census Harmonized Monthly and Annual Panel Validation

- Generated at UTC: `2026-07-19T12:50:15.033547+00:00`
- Monthly output: `data/processed/harmonized/census_imports_hs6_monthly_harmonized.parquet`
- Annual output: `data/processed/harmonized/census_imports_hs6_annual.parquet`
- Validation status: **PASS**

## Required checks

- Configured input SHA256 checks: `yes`
- All source rows receive an explicit bridge status: `yes`
- Unique monthly analysis key: `yes`
- Complete annual configured-origin grid: `yes`
- Every configured origin-year has 12 source months: `yes`
- Quantity placeholder identified and disabled: `yes`

## Mapping and value coverage

- Gross mapped import-value coverage: `97.286356%`.
- Eligible import-value coverage after excluding national chapters 98/99: `99.997284%`.
- Excluded national-special import value: `$522585907029.00`.
- Unresolved nonstandard-code import value: `$509271053.00`.

## Flow reconciliation

| Field | Eligible input | Monthly output | Annual output | Monthly gap | Annual gap |
|---|---:|---:|---:|---:|---:|
| `import_value_usd` | 18753387143026.00 | 18753387143026.00 | 18753387143026.00 | 0.000000 | 0.000000 |
| `customs_value` | 18690555782881.00 | 18690555782881.00 | 18690555782881.00 | 0.000000 | 0.000000 |
| `duties` | 510620797089.00 | 510620797089.00 | 510620797089.00 | 0.000000 | 0.000000 |
| `dutiable_value_usd` | 5851081711633.00 | 5851081711633.00 | 5851081711633.00 | 0.000000 | 0.000000 |

## Interpretation

The monthly table is the sparse event-study interface after year-specific HS harmonization. The annual table completes the 15 configured origins, 5,202 analysis products, and 2014-2024 years; missing sparse product rows are recorded as zero reported imports only because the source origin-month files are complete. This batch is not an all-origin U.S. import denominator. National chapters 98/99 and unresolved nonstandard HS6 codes remain outside the internationally comparable output and are reported in coverage diagnostics. Quantity is structurally unavailable: raw zeros with unit `-` are placeholders, not economic zero quantities.
