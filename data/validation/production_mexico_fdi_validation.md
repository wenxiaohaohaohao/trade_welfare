# M4.5 Mexico FDI Standardization Validation

- Status: **PASS**
- Generated UTC: `2026-08-10T11:54:54.029891+00:00`
- Config SHA256: `0f49c1bb523c8c21d2bbd2e754f68563274619f5491a284bb723535b7052b00b`
- Checks: 100
- Failures: 0

## Canonical outputs

| Output | Rows | Columns | SHA256 |
|---|---:|---:|---|
| `data/processed/harmonized/production_mexico_fdi_source_sector_period_long.parquet` | 902,608 | 73 | `998b1f3245fe06ade332411421c9933f031081921e0847b14e13fa5707d24542` |
| `data/processed/harmonized/production_validation_mexico_fdi_parent_sector_period_long.parquet` | 28,560 | 68 | `98191b4362b2ff1b7d91733d1f8ba7a25dc24028c97b848fe62f165e12d0b89e` |
| `data/processed/harmonized/production_mexico_fdi_benchmark_period_long.parquet` | 1,867 | 59 | `a65f82ba2960987df8d22bccb883f8eda11db641a3f9528148242341091a4806` |

## Interpretation contract

- All values are signed inward financial FDI flows to Mexico, not output, employment, plant entry, or causal relocation.
- Parent country is the reported source/parent jurisdiction, not necessarily the ultimate owner; host country is always Mexico.
- `C` remains missing. Strict period values require all published source components and required quarters to be present and non-confidential.
- 2024 joint detail is H1 only. Calendar-year rows are retained as explicitly incomplete and missing; national 2024 remains a separate full-year benchmark.
- SCIAN sector, subsector, and industry-group rows are overlapping hierarchy levels and are never summed together.
- Parent-country and sector annual margins are one-dimensional references; they are not outer-joined, allocated, or forced to equal the national total.

## Checks

| Check | Status |
|---|---|
| `input_country_sector_quarterly_sha256` | PASS |
| `input_country_sector_quarterly_shape` | PASS |
| `input_country_sector_quarterly_schema_signature` | PASS |
| `input_country_sector_quarterly_key` | PASS |
| `input_national_quarterly_sha256` | PASS |
| `input_national_quarterly_shape` | PASS |
| `input_national_quarterly_schema_signature` | PASS |
| `input_national_quarterly_key` | PASS |
| `input_national_investment_type_quarterly_sha256` | PASS |
| `input_national_investment_type_quarterly_shape` | PASS |
| `input_national_investment_type_quarterly_schema_signature` | PASS |
| `input_national_investment_type_quarterly_key` | PASS |
| `input_parent_country_annual_sha256` | PASS |
| `input_parent_country_annual_shape` | PASS |
| `input_parent_country_annual_schema_signature` | PASS |
| `input_parent_country_annual_key` | PASS |
| `input_sector_annual_sha256` | PASS |
| `input_sector_annual_shape` | PASS |
| `input_sector_annual_schema_signature` | PASS |
| `input_sector_annual_key` | PASS |
| `input_country_investment_type_quarterly_sha256` | PASS |
| `input_country_investment_type_quarterly_shape` | PASS |
| `input_country_investment_type_quarterly_schema_signature` | PASS |
| `input_country_investment_type_quarterly_key` | PASS |
| `input_state_country_quarterly_sha256` | PASS |
| `input_state_country_quarterly_shape` | PASS |
| `input_state_country_quarterly_schema_signature` | PASS |
| `input_state_country_quarterly_key` | PASS |
| `input_state_investment_type_quarterly_sha256` | PASS |
| `input_state_investment_type_quarterly_shape` | PASS |
| `input_state_investment_type_quarterly_schema_signature` | PASS |
| `input_state_investment_type_quarterly_key` | PASS |
| `input_state_sector_quarterly_sha256` | PASS |
| `input_state_sector_quarterly_shape` | PASS |
| `input_state_sector_quarterly_schema_signature` | PASS |
| `input_state_sector_quarterly_key` | PASS |
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
| `build_summary_source_count` | PASS |
| `raw_sources_exist_size_hash` | PASS |
| `build_summary_output_hashes_match_inputs` | PASS |
| `detail_country_crosswalk_join` | PASS |
| `detail_sector_crosswalk_join` | PASS |
| `detail_embedded_country_iso_matches_crosswalk` | PASS |
| `input_usd_scaling_identity` | PASS |
| `detail_confidential_missing_identity` | PASS |
| `detail_quarter_structure_universe` | PASS |
| `detail_calendar_coverage` | PASS |
| `detail_quality_snapshot` | PASS |
| `detail_sector_level_snapshot` | PASS |
| `eligible_detail_snapshot` | PASS |
| `eligible_analysis_sector_code_counts` | PASS |
| `parent_sector_published_support_count` | PASS |
| `output_source_period_long_shape` | PASS |
| `output_source_period_long_key` | PASS |
| `output_source_period_long_stata_aliases` | PASS |
| `output_parent_sector_period_long_shape` | PASS |
| `output_parent_sector_period_long_key` | PASS |
| `output_parent_sector_period_long_stata_aliases` | PASS |
| `output_benchmark_period_long_shape` | PASS |
| `output_benchmark_period_long_key` | PASS |
| `output_benchmark_period_long_stata_aliases` | PASS |
| `source_period_row_counts` | PASS |
| `source_period_available_counts` | PASS |
| `source_2024_annual_explicit_unavailable` | PASS |
| `source_quarter_identity` | PASS |
| `source_calendar_year_independent_recompute` | PASS |
| `source_h1_independent_recompute` | PASS |
| `parent_sector_period_row_counts` | PASS |
| `parent_sector_period_available_counts` | PASS |
| `parent_2024_annual_explicit_unavailable` | PASS |
| `parent_sector_value_and_scope_logic` | PASS |
| `parent_quarter_independent_recompute` | PASS |
| `parent_calendar_year_independent_recompute` | PASS |
| `parent_h1_independent_recompute` | PASS |
| `benchmark_scope_row_counts` | PASS |
| `national_2024_values` | PASS |
| `benchmark_unknown_and_unmapped_isolation` | PASS |
| `national_and_margin_reconciliation` | PASS |
| `deterministic_source_period_long_sha256` | PASS |
| `deterministic_parent_sector_period_long_sha256` | PASS |
| `deterministic_benchmark_period_long_sha256` | PASS |
| `canonical_source_period_long_hash_matches_candidate` | PASS |
| `canonical_parent_sector_period_long_hash_matches_candidate` | PASS |
| `canonical_benchmark_period_long_hash_matches_candidate` | PASS |
| `temporary_output_cleaned` | PASS |
