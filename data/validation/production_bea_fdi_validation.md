# M4.4 BEA Direct Investment Standardization Validation

- Status: **PASS**
- Generated UTC: `2026-08-10T10:53:58.017818+00:00`
- Config SHA256: `934092fe9b6857fb23fc54f5d28e89441b6772f0f2e454c6849c042431670683`
- Checks: 92
- Failures: 0

## Canonical outputs

| Output | Rows | Columns | SHA256 |
|---|---:|---:|---|
| `data/processed/harmonized/production_bea_fdi_source_industry_long.parquet` | 34,830 | 73 | `e947317c827f975aab78fc9727594094d540e1b4b27a8a6b166eca3fd28d883a` |
| `data/processed/harmonized/production_validation_bea_fdi_long.parquet` | 7,125 | 72 | `8f296d59d58ad08078c9792f862c503f371537ccc84395d5bffdb00e343b6fcf` |

## Interpretation contract

- `position` is an end-period historical-cost stock; `flows` and `income` are separate annual-flow concepts. They must never be added across metrics or mechanically summed across years.
- `us_direct_investment_abroad` treats the foreign country as affiliate host; `foreign_direct_investment_in_us` treats it as foreign investor origin.
- `(D)` remains missing/suppressed. `(*)` remains numeric zero with a small-value flag and is not an exact zero.
- Negative values retain the BEA-reported sign. No absolute-value conversion, clipping, or sign reversal is applied.
- Formal sector `value` is available only when all required source industries are disclosed. `source_disclosed_value_sum` is diagnostic only.
- Transportation equipment is an `autos` robustness proxy with `main_analysis_join_eligible=false`.

## Checks

| Check | Status |
|---|---|
| `input_bea_fdi_sha256` | PASS |
| `input_bea_fdi_shape` | PASS |
| `input_bea_fdi_schema_signature` | PASS |
| `input_bea_fdi_key` | PASS |
| `input_bea_fdi_filtered_rows` | PASS |
| `input_country_crosswalk_sha256` | PASS |
| `input_country_crosswalk_shape` | PASS |
| `input_country_crosswalk_schema_signature` | PASS |
| `input_country_crosswalk_key` | PASS |
| `input_country_crosswalk_filtered_rows` | PASS |
| `input_source_sector_crosswalk_sha256` | PASS |
| `input_source_sector_crosswalk_shape` | PASS |
| `input_source_sector_crosswalk_schema_signature` | PASS |
| `input_source_sector_crosswalk_key` | PASS |
| `input_source_sector_crosswalk_filtered_rows` | PASS |
| `input_time_aggregation_rules_sha256` | PASS |
| `input_time_aggregation_rules_shape` | PASS |
| `input_time_aggregation_rules_schema_signature` | PASS |
| `input_time_aggregation_rules_key` | PASS |
| `input_time_aggregation_rules_filtered_rows` | PASS |
| `input_build_summary_sha256` | PASS |
| `input_raw_manifest_sha256` | PASS |
| `raw_manifest_file_count` | PASS |
| `raw_manifest_files_exist` | PASS |
| `raw_manifest_sizes_match` | PASS |
| `raw_manifest_hashes_match` | PASS |
| `input_years` | PASS |
| `input_no_position_only_2025` | PASS |
| `input_rows_per_year` | PASS |
| `input_direction_rows` | PASS |
| `input_direction_industry_counts` | PASS |
| `geography_source_geography_labels` | PASS |
| `geography_source_area_aggregate_rows` | PASS |
| `geography_country_override_aggregate_rows` | PASS |
| `geography_final_aggregate_rows` | PASS |
| `geography_actual_country_rows` | PASS |
| `geography_actual_country_count` | PASS |
| `geography_country_direction_year_cells` | PASS |
| `source_industry_labels` | PASS |
| `direction_country_counts` | PASS |
| `time_rule_position` | PASS |
| `time_rule_flows` | PASS |
| `time_rule_income` | PASS |
| `source_output_shape` | PASS |
| `source_output_key` | PASS |
| `source_metric_grid` | PASS |
| `source_actual_and_aggregate_rows` | PASS |
| `source_direction_rows` | PASS |
| `source_proxy_rows` | PASS |
| `source_paths_project_relative` | PASS |
| `source_files_match_manifest` | PASS |
| `source_suppressed_missing_identity` | PASS |
| `source_small_values_are_zero` | PASS |
| `source_no_infinite_values` | PASS |
| `source_metric_snapshot_position` | PASS |
| `source_metric_snapshot_flows` | PASS |
| `source_metric_snapshot_income` | PASS |
| `source_identity_position` | PASS |
| `source_identity_flows` | PASS |
| `source_identity_income` | PASS |
| `actual_mapped_source_negative_counts` | PASS |
| `analysis_output_shape` | PASS |
| `analysis_output_key` | PASS |
| `analysis_cell_and_dimension_counts` | PASS |
| `analysis_scope_counts` | PASS |
| `analysis_scope_flags` | PASS |
| `analysis_no_aggregate_or_residual` | PASS |
| `analysis_direction_rows` | PASS |
| `analysis_no_synthetic_sectors` | PASS |
| `analysis_component_counts_complete` | PASS |
| `analysis_component_sets` | PASS |
| `analysis_recomputed_from_source` | PASS |
| `analysis_metric_snapshot_position` | PASS |
| `analysis_metric_snapshot_flows` | PASS |
| `analysis_metric_snapshot_income` | PASS |
| `analysis_strict_negative_counts` | PASS |
| `analysis_no_infinite_values` | PASS |
| `analysis_metrics_not_additive` | PASS |
| `metric_sign_conventions` | PASS |
| `direction_country_roles` | PASS |
| `comparison_country_coverage` | PASS |
| `absent_country_VNM` | PASS |
| `absent_country_MAR` | PASS |
| `twn_direction_and_proxy_coverage` | PASS |
| `mexico_autos_proxy_boundary` | PASS |
| `source_stata_aliases` | PASS |
| `analysis_stata_aliases` | PASS |
| `deterministic_source_long_sha256` | PASS |
| `deterministic_analysis_long_sha256` | PASS |
| `canonical_source_hash_matches_candidate` | PASS |
| `canonical_analysis_hash_matches_candidate` | PASS |
| `temporary_output_cleaned` | PASS |
