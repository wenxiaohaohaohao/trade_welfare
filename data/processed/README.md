# Processed Data

This directory contains reproducible harmonized outputs built from the validated source-specific files in `data/interim/`. It now contains completed M1 concordances and M2 product-level treatment/trade interfaces, but not yet the sector-level ranking or production-integration panels.

The complete collaborator audit is `docs/data_processing_audit_trail.md`; the variable-level construction contract is `docs/variable_construction_catalog.md`. Their fixed PDF versions are `output/pdf/data_processing_audit_trail.pdf` and `output/pdf/variable_construction_catalog.pdf`. Starting with M3.1, every completed processed-data step must update both Markdown sources and both PDFs before its checklist item is marked complete.

## Completed concordances

- `concordances/country_crosswalk.parquet`: one row per `source_name × source_country_id`. It records the canonical ISO3/ISO2 code, source roles, BEA area metadata, analysis-sample flags, and mutually exclusive `is_country`, `is_aggregate`, `is_residual`, and `is_proxy` classifications. Aggregate and residual rows intentionally have no country ISO3. BACI `S19` maps to `TWN` only with proxy status.
- `concordances/time_aggregation_rules.parquet`: one row per `input_id × metric_name`. It fixes native frequency, temporal semantics, allowed annual operator, missing-period treatment, and prohibited operations. Mexico FDI is full-calendar-year comparable through 2023; 2024 contains Q1-Q2 only and must remain quarterly or be compared H1-to-H1.
- `concordances/hs_to_hs2012_conversion.parquet`: one canonical weight-1 target per HS2012, HS2017, or HS2022 source code. `analysis_hs6` applies the documented CEPII petroleum-code collapse needed to join BACI without expanding values.
- `concordances/hs_revision_correlations.parquet`: full official UNSD correlation pairs, relationship types, partial-scope flags where available, and explicit missing weights for multi-target mappings.
- `concordances/census_hs6_year_to_hs2012.parquet`: one row per Census `year × source_hs6`, with the assigned HS revision, exact legacy fallback where justified, national-special-code exclusions, and unresolved nonstandard codes retained explicitly.
- `concordances/product_sector_crosswalk.parquet`: one row per BACI/CEPII `analysis_hs6`. It contains the official HS2012/ISIC Rev.4 provenance, mutually exclusive `analysis_sector`, first-round exclusion status, and independent BEC Rev.5 end-use fields. Composite BEC uses have no allocation weights; `271000` preserves the five-code CEPII collapse and `999999` remains residual.
- `concordances/source_sector_crosswalk.parquet`: one row per `source_name × source_sector_level × source_sector_code` for OECD ICIO/AMNE, BEA MNE/FDI, and Mexico SCIAN. Direct mappings have weight 1; aggregates, residuals, services, and mixed sectors have null weights and explicit non-join status.

Build and validation files:

- `code/data_processing/build_country_master.py`
- `configs/country_concordance_overrides.yaml`
- `data/validation/country_crosswalk_validation.json`
- `data/validation/country_crosswalk_validation.md`
- `code/data_processing/build_time_rules.py`
- `configs/time_aggregation_rules.yaml`
- `data/validation/time_aggregation_rules_validation.json`
- `data/validation/time_aggregation_rules_validation.md`
- `code/data_processing/build_hs_revision_bridge.py`
- `configs/hs_revision_rules.yaml`
- `data/validation/hs_revision_bridge_validation.json`
- `data/validation/hs_revision_bridge_validation.md`
- `code/data_processing/build_product_sector_crosswalk.py`
- `configs/product_sector_rules.yaml`
- `data/validation/product_sector_crosswalk_validation.json`
- `data/validation/product_sector_crosswalk_validation.md`
- `code/data_processing/build_source_sector_crosswalk.py`
- `configs/source_sector_rules.yaml`
- `data/validation/source_sector_crosswalk_validation.json`
- `data/validation/source_sector_crosswalk_validation.md`
- `code/data_processing/build_concordance_coverage_report.py`
- `data/validation/concordance_coverage.json`
- `data/validation/concordance_coverage.md`

## Completed M2 harmonized outputs

- `harmonized/product_treatment_hs6_year.parquet`: complete 5,202-product by 2014-2024 grid with gross statutory Section 301 treatment. Many-to-one HS2017 mappings use 2017 import weights and preserve list/mapping provenance.
- `harmonized/connector_trade_legs_hs6_year.parquet`: pure BACI trade legs for 13 connectors, 5,202 products, and 11 years, before treatment is joined.
- `harmonized/connector_trade_hs6_year.parquet`: final connector-product-year trade table after a validated many-to-one treatment merge. Treatment and China-to-USA are repeated comparison fields and are not additive across connectors.
- `harmonized/census_imports_hs6_monthly_harmonized.parquet`: sparse 15-origin monthly timing interface after year-specific HS harmonization.
- `harmonized/census_imports_hs6_annual.parquet`: complete 15-origin by product by year Census grid. It is not an all-origin denominator.
- `policy/section301_2024_review_exact_hts.parquet`: 367 exact HTS8/HTS10 review records retained as a separate extension; two rows remain description-scoped and no `analysis_hs6` is assigned.

M2 builders and validation:

- `code/data_processing/build_product_treatment_panel.py`
- `configs/product_treatment_rules.yaml`
- `data/validation/product_treatment_panel_validation.json`
- `data/validation/product_treatment_panel_validation.md`
- `code/data_processing/build_connector_trade_panel.py`
- `configs/connector_trade_rules.yaml`
- `data/validation/connector_trade_panel_validation.json`
- `data/validation/connector_trade_panel_validation.md`
- `code/data_processing/merge_trade_treatment_panel.py`
- `configs/trade_treatment_merge_rules.yaml`
- `data/validation/trade_treatment_merge_validation.json`
- `data/validation/trade_treatment_merge_validation.md`
- `code/data_processing/build_census_harmonized_panels.py`
- `configs/census_harmonization_rules.yaml`
- `data/validation/census_harmonized_panels_validation.json`
- `data/validation/census_harmonized_panels_validation.md`
- `code/data_processing/build_section301_2024_review_extension.py`
- `configs/section301_2024_review_rules.yaml`
- `data/validation/section301_2024_review_extension_validation.json`
- `data/validation/section301_2024_review_extension_validation.md`

The next build stage is M3 sector aggregation and connector variables. Production sources must later use the validated source-sector join eligibility rather than directly matching source labels.

Every processed output must be reproducible from `data/interim/`, documented by a build script, and retain source/provenance fields needed to audit aggregation and suppression.
