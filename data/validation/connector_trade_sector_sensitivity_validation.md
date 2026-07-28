# M3.6 Connector-Sector Sensitivity Validation

- Origin Date: `2026-07-28`
- Verification Status: `VERIFIED`
- Version Label: `connector_trade_sector_sensitivity_rules_v1`

## Result

- Validation status: **PASS**
- All three Parquet files reproduced with byte-identical SHA256: `yes`.
- M3.6 constructs sensitivity inputs only; no connector ranking is constructed.

## Outputs

| Output | Rows × columns | Natural key | SHA256 |
|---|---:|---|---|
| time-window sensitivity | 1092 × 56 | `connector_iso3, analysis_sector, flow_id, window_spec_id` | `1594fadeb348f88e07b2ec8f43ca3708f49f9e06a0b78fafe24ffb6417635aad` |
| source-bloc sensitivity | 182 × 64 | `connector_iso3, analysis_sector, source_bloc_id` | `67fbf760adb01a18d4e0e4f9ddd44eef9f3d2d2496a0a60d358cf8eab77e1eda` |
| exposure-definition sensitivity | 364 × 47 | `connector_iso3, analysis_sector, exposure_definition_id` | `96144e95dd525103b658ed7220a15d2f3c7c7acf79ea3f314314112971dc7cbd` |

## Frozen Inputs

- M3.5 common panel: `91 × 152`; hash/schema/key/version contract PASS.
- M3.1 annual sector panel: `1001 × 70`; hash/schema/key/version contract PASS.
- `time_windows.yaml` and `country_groups.yaml` hashes and frozen members/windows match.
- All 91 connector-sector cells retain the exact 2014-2024 annual grid.

## Alternative Time Windows

- `primary_post`: 2014-2017 versus 2020-2024.
- `exclude_2024`: 2014-2017 versus 2020-2023.
- `shock_only`: 2014-2017 versus 2018-2019.
- Levels are annual means. Included-value coverage is recomputed as a ratio of sums.
- Negative level-change counts by specification and flow: `{'primary_post': {'china_to_connector': 3, 'east_asia_to_connector': 5, 'connector_to_usa': 6, 'china_to_usa': 26}, 'exclude_2024': {'china_to_connector': 3, 'east_asia_to_connector': 5, 'connector_to_usa': 6, 'china_to_usa': 26}, 'shock_only': {'china_to_connector': 13, 'east_asia_to_connector': 12, 'connector_to_usa': 13, 'china_to_usa': 26}}`.
- Zero endpoints / defined log growth / defined annual DH SD: `0 / 1092 / 728`.
- Annual DH SD is intentionally missing for `shock_only`: a two-year comparison window has only one within-window transition, which cannot define a sample SD with `ddof=1`.

## Source-Bloc Definitions

- `china_only`: CHN.
- `extended_east_asia`: CHN, KOR, JPN, TWN; connector self-trade is excluded when applicable.
- Negative input-gain counts: `{'china_only': 3, 'extended_east_asia': 5}`; self-trade-excluded rows: `14`.
- Direction agreement with China-only for input gain / DH growth / input-export-ratio change / product correlation: `{'input_gain': 89, 'input_dh_growth': 89, 'input_to_export_ratio_change': 73, 'product_correlation': 89}`.
- The definitions are nested. East Asia minus China is the contribution of the additional East Asian origins after self-exclusion, not an independent comparison sample.

## Exposure Definitions

- `tariff_overlap`: connector export value share on tariffed products.
- `exposure_weighted_rate`: export-value-weighted continuous product exposure among observed products.
- `positive_exposure_gain_share`: positive export gains on products with exposure above zero.
- `top_quartile_exposure_gain_share`: positive export gains on sector p75-or-higher exposure products.
- Defined measures / pre-post-supported rows: `364 / 182`.
- Negative pre-post changes for tariff overlap / weighted rate: `{'tariff_overlap': 47, 'exposure_weighted_rate': 32}`.
- The four definitions have different estimands and units. M3.6 therefore does not subtract them from each other or convert them into ranks.

## Stata and State Preservation

- Stata aliases complete/unique/max length: time `56 / 13`, source `64 / 11`, exposure `47 / 12`.
- TWN rows in time/source/exposure outputs: `{'time_window': 84, 'source_bloc': 14, 'exposure_definition': 28}`; every row retains the proxy flag.
- Negative changes are retained. No small-base flag, growth value, exposure missing state, or source definition is silently overwritten.

## Interpretation Boundary

These files are M6-ready sensitivity inputs, not evidence that a ranking is stable. Ranking stability can only be assessed after M6 freezes the score, weights, eligibility rules, and tie handling. The source-bloc and exposure measures remain descriptive and do not identify causal rerouting or production relocation.
