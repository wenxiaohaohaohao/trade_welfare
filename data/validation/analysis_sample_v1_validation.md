# Analysis Sample V1 Validation

- Generated at UTC: `2026-07-19T12:30:05.345713+00:00`
- Sample version: `analysis_sample_v1`
- Failure count: `0`
- Validation status: **PASS**

## Frozen sample

- Core connectors: `VNM, MEX, CAN`
- Asian comparators: `IND, IDN, MYS, PHL, THA, KOR, TWN`
- Other candidates: `POL, MAR, TUR`
- Priority sectors: `electronics, electrical_equipment, machinery, autos, medical_devices, textiles_apparel`
- Trade window: `2014-2024`
- Pre period: `2014-2017`
- Shock period: `2018-2019`
- Post period: `2020-2024`
- Selected structural baselines: `2017, 2018, 2022`
- Excluded structural candidate: `2019` — No validated 2019 OECD ICIO model baseline exists in the current processed inputs.

## Validation checks

| Check | Passed |
|---|---|
| `country_contract.source_core` | yes |
| `country_contract.source_extended_east_asia` | yes |
| `country_contract.destination_core` | yes |
| `country_contract.core_connectors` | yes |
| `country_contract.asian_comparators` | yes |
| `country_contract.other_candidates` | yes |
| `connector_groups_disjoint` | yes |
| `census_origin_config_matches_frozen_sample` | yes |
| `census_origin_data_matches_frozen_sample` | yes |
| `twn_baci_proxy_matches` | yes |
| `priority_sectors_match` | yes |
| `excluded_sectors_match` | yes |
| `product_sector_config_reference_matches` | yes |
| `product_sector_mapping_version_matches` | yes |
| `product_sector_mapping_validation_passed` | yes |
| `source_sector_config_reference_matches` | yes |
| `source_sector_mapping_version_matches` | yes |
| `source_sector_mapping_validation_passed` | yes |
| `time_contract.pre_period` | yes |
| `time_contract.shock_period` | yes |
| `time_contract.post_period` | yes |
| `time_windows_disjoint` | yes |
| `time_windows_cover_trade_panel` | yes |
| `coverage.baci_hs6_panel.trade_panel` | yes |
| `coverage.us_census_hs6_monthly.trade_panel` | yes |
| `coverage.section301_hs6_exposure.trade_panel` | yes |
| `coverage.oecd_amne_affiliate_activity` | yes |
| `coverage.bea_us_mne_affiliate_country_industry` | yes |
| `coverage.bea_direct_investment_country_industry` | yes |
| `coverage.mexico_fdi_country_sector_quarterly` | yes |
| `selected_structural_baselines_available` | yes |
| `primary_baseline_is_pre_shock_2017` | yes |
| `unsupported_2019_excluded` | yes |
| `fdi_markets_excluded` | yes |
| `upstream_quality_audit_passed` | yes |

## Interpretation

The frozen sample fixes the first-stage country, sector, and time scope. Product-level and source-sector concordances are validated, including explicit unsupported and ambiguous source categories. The 2017 ICIO baseline is primary because it precedes the 2018 Section 301 shock; 2018 is retained as the shock-onset interface and 2022 as a post-shock robustness baseline. The unsupported 2019 ICIO candidate is explicitly excluded rather than imputed.
