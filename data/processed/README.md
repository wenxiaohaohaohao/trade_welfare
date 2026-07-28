# Processed Data

This directory contains reproducible harmonized outputs built from the validated source-specific files in `data/interim/`. It now contains completed M1 concordances, M2 product-level treatment/trade interfaces, the M3.1 annual connector-sector panel, the M3.2 complete-window/growth interfaces, the M3.3 flow-level growth diagnostics, and the M3.4 trade-reorganization interfaces. It does not yet contain M3.5-M3.6 comparison/sensitivity inputs, connector rankings, or production-integration panels.

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

## Completed M3.1 harmonized output

- `harmonized/connector_trade_sector_year.parquet`: 1,001 rows at `connector_iso3, analysis_sector, year`, covering 13 connectors, 7 sectors, and 2014-2024. It contains four annual trade levels and flow-specific diagnostics/coverage, sector Section 301 numerators/denominators/rates/shares, treatment denominator exception counts, TWN proxy status, and explicit repeated/non-additive flags.
- Builder/config: `code/data_processing/build_connector_trade_sector_panel.py` and `configs/connector_trade_sector_rules.yaml`.
- Validation: `data/validation/connector_trade_sector_panel_validation.json` and `.md`, status PASS. Product-to-sector and full-universe reconciliation gaps are zero; the deterministic second-build SHA256 matches `95e547267892c4bc883788542f0e59ba284441b42f4ce1d379aea71a2f978c8c`.

## Completed M3.2 harmonized outputs

- `harmonized/connector_trade_sector_window.parquet`: 273 rows and 79 columns at `connector_iso3, analysis_sector, window_id`. It contains complete 4/2/5-year pre/shock/post annual means, diagnostics, ratio-of-sums coverage, policy summaries, denominator exceptions, and repeated/non-additive flags.
- `harmonized/connector_trade_sector_window_comparison.parquet`: 91 rows and 142 columns at `connector_iso3, analysis_sector`. It contains four flows' pre/shock/post levels, post-pre changes, DH/log growth, zero/defined flags, year counts, and coverage/policy pre/shock/post levels.
- Builder/config: `code/data_processing/build_connector_trade_sector_window_panel.py` and `configs/connector_trade_sector_window_rules.yaml`.
- Validation: `data/validation/connector_trade_sector_window_validation.json` and `.md`, status PASS. Formula/reconciliation gaps are zero; deterministic SHA256 values are `310da7f289d8760d3ead34215a294be18275c758a2084cfd9f905988b695e704` and `be5f3a025a81d36d5a9bb1bd137d4bed9325a68ab5f1cb7f4d946a2373fbeb04`.

## Completed M3.3 harmonized output

- `harmonized/connector_trade_sector_growth_diagnostics.parquet`: 364 rows and 64 columns at `connector_iso3, analysis_sector, flow_id`. It preserves the four flows' M3.2 levels, changes, raw DH/log growth, zero/defined flags, and year counts; adds absolute and sector-relative small-base eligibility; adds advisory robust-z/mechanical abnormal-growth flags; and provides flow-level p5/p95 winsorized DH/log alternatives for sensitivity only.
- Builder/config: `code/data_processing/build_connector_trade_sector_growth_diagnostics.py` and `configs/connector_trade_sector_growth_diagnostic_rules.yaml`.
- Validation: `data/validation/connector_trade_sector_growth_diagnostics_validation.json` and `.md`, status PASS. The key is unique, source/formula checks have zero gap, all 64 Stata aliases pass, and deterministic SHA256 is `fe69d953cd84a2acfc64ddb17b1ee57e3d0e44f7b44cad348f9016aee7e0953d`.

## Completed M3.4 harmonized outputs

- `harmonized/connector_trade_product_reorganization_window.parquet`: 55,081 rows and 56 columns at `connector_iso3, analysis_hs6`. It contains complete 4/5-year pre/post product means, four flow changes, post policy exposure with nullable missing states, and product condition/weight fields used to reproduce the sector diagnostics.
- `harmonized/connector_trade_sector_reorganization_indicators.parquet`: 91 rows and 92 columns at `connector_iso3, analysis_sector`. It contains signed replacement, connector/export growth diagnostics inherited from M3.3, separate China/East Asia input-export ratios, and tariff/exposure-overlap measures with denominator coverage.
- `harmonized/connector_trade_sector_product_comovement.parquet`: 91 rows and 49 columns at `connector_iso3, analysis_sector`. It contains HS6 Pearson/weighted correlations and eligible/active/positive-export-gain shares for two-leg, rerouting, and triple conditions.
- Builder/config: `code/data_processing/build_connector_trade_reorganization_indicators.py` and `configs/connector_trade_reorganization_indicator_rules.yaml`.
- Validation: `data/validation/connector_trade_reorganization_indicators_validation.json` and `.md`, status PASS. All three natural keys are unique, 28 exposure-missing products remain missing, 56/92/49 aliases pass, and deterministic SHA256 values are `1c83dc1070656c903d625b2e85c82ea6e7afa18535105351ccef24a405ed2c34`, `f13c5f8aa0c4402d0b467a06a6b99ba8ddc8389d47ede9ba8c8036275c1d74f2`, and `3095cd39a7355ce6968e0e5c29956841fd9e40bc72238d06aafe8d3ef0c3b0f1`.

The next build stage is M3.5's common connector/comparator panel. Production sources must later use the validated source-sector join eligibility rather than directly matching source labels.

Every processed output must be reproducible from `data/interim/`, documented by a build script, and retain source/provenance fields needed to audit aggregation and suppression.
