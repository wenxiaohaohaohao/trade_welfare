# M3.4 Trade Reorganization Indicators Validation

## Material Passport

- Origin Skill: `academic-research-suite/experiment-agent`
- Origin Mode: `run + validate`
- Origin Date: `2026-07-28`
- Verification Status: `VERIFIED`
- Version Label: `connector_trade_reorganization_indicator_rules_v1`

## Result

- Validation status: **PASS**
- Product window output: `data/processed/harmonized/connector_trade_product_reorganization_window.parquet`; `55081 × 56`; SHA256 `1c83dc1070656c903d625b2e85c82ea6e7afa18535105351ccef24a405ed2c34`.
- Sector indicator output: `data/processed/harmonized/connector_trade_sector_reorganization_indicators.parquet`; `91 × 92`; SHA256 `f13c5f8aa0c4402d0b467a06a6b99ba8ddc8389d47ede9ba8c8036275c1d74f2`.
- Product co-movement output: `data/processed/harmonized/connector_trade_sector_product_comovement.parquet`; `91 × 49`; SHA256 `3095cd39a7355ce6968e0e5c29956841fd9e40bc72238d06aafe8d3ef0c3b0f1`.

## Frozen input and structural gates

- Frozen hashes and schemas: `pass`.
- Output duplicate keys (product / sector / co-movement): `0 / 0 / 0`.
- Eligible products and sectors: `4237 / 7`.
- Product windows observed years (pre min/max; post min/max): `4/4; 5/5`.
- Maximum product-to-sector value reconciliation gap: `0.000015258789` USD.
- Deterministic hashes all match: `yes`.

## Replacement indicator

- Denominator: `max(China→USA pre − post, 0)`.
- The ratio is defined only when that decline is strictly greater than USD 25 million.
- Numerator: signed connector→USA post-minus-pre gain. Negative gains remain negative; no epsilon and no cap are used.
- Defined ratios / positive-gain candidates / defined denominators with negative gains: `26 / 22 / 4`.
- Undefined ratios retained as missing: `65`.

## Source-input and export relationships

- China and extended East Asia are kept as separate source concepts.
- Each source-input/export ratio uses connector→USA exports in the same window as denominator and is defined only for a strictly positive denominator.
- China pre/post defined counts: `91 / 91`.
- East Asia pre/post defined counts: `91 / 91`.

## Section 301 exposure overlap

- Products with missing post exposure: `28`; tariffed products among them: `14`.
- Fractional post tariff-status products: `0`.
- Missing exposure is preserved as missing and excluded from exposure-weighted denominators; it is never converted to zero.
- Both positive exposure and the within-sector p75 of positive exposure are reported. These definitions are not substituted for tariffed status.
- Sector share values outside [0,1]: `0`.

## Product-level co-movement

| Source | Correlation defined | Weighted defined | Low n | Minimum active products | Minimum positive-weight products |
|---|---:|---:|---:|---:|---:|
| `china` | 91 | 91 | 0 | 31 | 30 |
| `east_asia` | 91 | 91 | 0 | 32 | 31 |

- Pearson correlations are computed across active HS6 products within each connector-sector cell.
- Weighted correlations use pre-period source input plus connector export value as weights.
- Positive-leg, rerouting, and triple-condition shares retain separate eligible-product, active-product, and positive-export-gain denominators.
- Correlations outside [-1,1] / shares outside [0,1]: `0 / 0`.

## Stata and edge-case interface

- Product / sector / co-movement aliases: `56 / 92 / 49`; all complete, unique, and no longer than 32 characters.
- TWN product / sector / co-movement rows: `4237 / 7 / 7`; all retain the proxy flag.
- China→USA and policy fields repeat across connectors for comparison and are explicitly marked non-additive.
- Canonical format remains Parquet. Stata `.dta` export remains deferred to M7.

## Interpretation boundaries

- `replacement_ratio` is a descriptive reorganization indicator, not a causal estimate.
- M3.3 small-base and abnormal-growth flags are carried forward unchanged and remain advisory.
- Exposure-overlap and co-movement measures are descriptive diagnostics. They do not prove supply-chain rerouting.
- This module does not construct connector ranking, production-side variables, structural moments, or counterfactual inputs.
