# M3.2 Connector Trade Sector Window Validation

## Material Passport

- Origin Skill: `academic-research-suite/experiment-agent`
- Origin Mode: `run + validate`
- Origin Date: `2026-07-28`
- Verification Status: `VERIFIED`
- Version Label: `connector_trade_sector_window_rules_v1`

## Result

- Validation status: **PASS**
- Long output: `data/processed/harmonized/connector_trade_sector_window.parquet`
- Long rows / columns: `273 / 79`
- Comparison output: `data/processed/harmonized/connector_trade_sector_window_comparison.parquet`
- Comparison rows / columns: `91 / 142`
- Long SHA256: `310da7f289d8760d3ead34215a294be18275c758a2084cfd9f905988b695e704`
- Comparison SHA256: `be5f3a025a81d36d5a9bb1bd137d4bed9325a68ab5f1cb7f4d946a2373fbeb04`

## Required gates

- Frozen input and time-window hashes match: `yes`
- Annual input rows / columns / duplicate keys: `1001 / 70 / 0`
- Long/comparison duplicate keys: `0 / 0`
- Every annual row assigned exactly once: `yes`
- Deterministic long/comparison hashes match: `yes`
- Required numeric missing counts, long/comparison: `0 / 0`
- DH out-of-bounds / infinite growth values: `0 / 0`

## Window completeness

| Window | Expected years | Observed min | Observed max | Incomplete cells |
|---|---:|---:|---:|---:|
| `pre` | 4 | 4 | 4 | 0 |
| `shock` | 2 | 2 | 2 | 0 |
| `post` | 5 | 5 | 5 | 0 |

## Flow reconstruction and growth checks

| Flow | Max mean×years gap USD | Pre zero | Post zero | Log defined | Negative post-pre changes | Max change gap | Max DH gap | Max log gap |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `china_to_connector` | 0.000000 | 0 | 0 | 91 | 3 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| `east_asia_to_connector` | 0.000000 | 0 | 0 | 91 | 5 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| `connector_to_usa` | 0.000000 | 0 | 0 | 91 | 6 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| `china_to_usa` | 0.000000 | 0 | 0 | 91 | 26 | 0.000e+00 | 0.000e+00 | 0.000e+00 |

## Coverage and policy recomputation

- Coverage key mismatches: `0`.
- Policy key mismatches: `0`.
- Zero-denominator / no-HS2017-mapping eligible products retained in each window: `17 / 11`.
- Nonzero pre policy exposure cells / policy growth fields: `0 / 0`.
- Repeated China-to-USA/policy inconsistencies: `0`.
- Repeated coverage inconsistencies: `0`.
- TWN long/comparison rows and false proxy flags: `21 / 7 / 0`.

## Stata interface

- Long aliases: `79`; maximum length `13`; pass `yes`.
- Comparison aliases: `142`; maximum length `13`; pass `yes`.
- Canonical files remain Parquet. No `.dta` is generated before M7.

## Interpretation boundaries

- Window levels are annual means over complete 4/2/5-year windows; unequal-length window sums are not compared.
- Included-value shares are ratios of summed eligible and full-universe values, not averages of annual shares.
- Negative changes and growth are retained. Current data have no pre/post zero flow cells, but zero/defined flags remain part of the schema.
- Policy pre exposure can be zero. No percentage or log growth is computed for policy exposure.
- This module does not define small-base thresholds, abnormal-growth treatment, winsorization, replacement ratios, rankings, production variables, or structural moments.
