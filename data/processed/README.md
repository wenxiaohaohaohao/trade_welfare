# Processed Data

This directory contains reproducible harmonized outputs built from the validated source-specific files in `data/interim/`. It now contains completed M1 concordances, M2 product-level treatment/trade interfaces, M3.1-M3.6 trade/reorganization/sensitivity interfaces, M4.1-M4.5 source-specific production and investment interfaces, and the M4.6 cross-source evidence registry plus strict host-country activity subset. It does not yet contain production growth, connector rankings, structural moments, or Stata exports.

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

## Completed M3.5 harmonized output

- `harmonized/connector_trade_sector_common_panel.parquet`: 91 rows and 152 columns at `connector_iso3, analysis_sector`. It one-to-one combines the M3.4 sector indicators and unique product co-movement fields; retains all 13 connectors/comparators across all 7 sectors; adds mutually exclusive sample-role flags, deterministic group/connector/sector order, source-match flags, and explicit no-selection/no-ranking/no-production flags.
- Builder/config: `code/data_processing/build_connector_trade_sector_common_panel.py` and `configs/connector_trade_sector_common_panel_rules.yaml`.
- Validation: `data/validation/connector_trade_sector_common_panel_validation.json` and `.md`, status PASS. All 91 cells match both inputs, group rows are 21/49/21, 26 defined and 65 missing replacement ratios remain unchanged, 152 aliases pass, and the deterministic SHA256 is `36c58c229f3f43e86f7ff7570fc6a1ffe08ccb8fd3259bb5853abece3171f682`.

## Completed M3.6 harmonized outputs

- `harmonized/connector_trade_sector_time_window_sensitivity.parquet`: 1,092 rows and 56 columns at `connector_iso3, analysis_sector, flow_id, window_spec_id`. It compares 2014-2017 with the primary 2020-2024 window, the required 2020-2023 exclude-2024 window, and the 2018-2019 shock-only window for four trade flows. Annual-mean levels, ratio-of-sums coverage, level/DH/log changes, within-comparison-window annual DH SD, positive-growth-year shares, and primary-specification differences are retained.
- `harmonized/connector_trade_sector_source_bloc_sensitivity.parquet`: 182 rows and 64 columns at `connector_iso3, analysis_sector, source_bloc_id`. It presents China-only and extended East Asia in a common schema, explicitly excludes KOR/TWN self-trade where applicable, and reports differences/direction agreement relative to China-only while marking that the definitions are nested.
- `harmonized/connector_trade_sector_exposure_definition_sensitivity.parquet`: 364 rows and 47 columns at `connector_iso3, analysis_sector, exposure_definition_id`. It provides tariff overlap, continuous weighted exposure, positive-exposure gain share, and top-quartile-exposure gain share without treating the four estimands as numerically interchangeable.
- Builder/config: `code/data_processing/build_connector_trade_sector_sensitivity.py` and `configs/connector_trade_sector_sensitivity_rules.yaml`.
- Validation: `data/validation/connector_trade_sector_sensitivity_validation.json` and `.md`, status PASS. All keys are unique, no incomplete window exists, all expected missing/negative/self-trade/proxy states are preserved, 56/64/47 aliases pass, and deterministic SHA256 values are `1594fadeb348f88e07b2ec8f43ca3708f49f9e06a0b78fafe24ffb6417635aad`, `67fbf760adb01a18d4e0e4f9ddd44eef9f3d2d2496a0a60d358cf8eab77e1eda`, and `96144e95dd525103b658ed7220a15d2f3c7c7acf79ea3f314314112971dc7cbd`.

## Completed M4.1 ICIO production-side outputs

- `harmonized/production_icio_source_sector_long.parquet`: 85,050 rows and 54 columns at `source_name, source_country_id, model_sector, year, metric_name`. It retains all 81 ICIO geographies, 50 source sectors, 2017/2018/2022, and seven metrics, including ROW and all excluded/outside-manufacturing source cells.
- `harmonized/production_validation_icio_long.parquet`: 10,080 rows and 43 columns at `country_iso3, analysis_sector, year, source_name, metric_name`. It contains 80 countries, six supported analysis sectors, three observed years, and seven production/accounting metrics.
- Builder/config: `code/data_processing/build_production_icio_long.py` and `configs/production_icio_rules.yaml`.
- Validation: `data/validation/production_icio_validation.json` and `.md`, status PASS. Source negatives, ROW/excluded partitions, metric totals, accounting identities, source files, 54/43 aliases, and both deterministic hashes are validated. SHA256 values are `266ff08c5bd26e00a08cb9f3654b7c83354d02da79cca036d65ccd68d0054110` and `e8bdc6070581f5a1697adba605ef8eac3e7c40a5946779a627ec08ea673315f0`.

M4.1 does not interpolate 2019, fabricate medical-devices rows, export `.dta`, or create the final cross-source `production_validation_long.parquet`.

## Completed M4.2 AMNE production-side outputs

- `harmonized/production_amne_parent_host_sector_long.parquet`: 7,560,318 rows and 71 columns at `source_name, source_host_country_id, source_parent_country_id, model_sector, year, metric_name`. It preserves six metric rows for every positive bilateral affiliate-output link, including ROW host/parent and excluded source sectors. Direct output, allocated VA/exports/imports, derived parent share, and unavailable employment are explicitly distinguished.
- `harmonized/production_validation_amne_host_sector_long.parquet`: 53,760 rows and 56 columns at `country_iso3, analysis_sector, year, source_name, metric_name`. It contains 80 actual hosts, six supported analysis sectors, 2008-2023, and seven host metrics on a complete zero-inclusive grid.
- Builder/config: `code/data_processing/build_production_amne_long.py` and `configs/production_amne_rules.yaml`.
- Validation: `data/validation/production_amne_validation.json` and `.md`, status PASS. Positive-link identity, zero-link coverage, direct/allocated formulas, 166 negative parent VA rows, unavailable employment, ROW handling, ratio-of-sums shares, bilateral-XVEM gaps, 71/56 aliases, and deterministic hashes are validated. SHA256 values are `6e3d0a77838b9c1d0cbae6445ee9b3f5637114747e51a148162c720d26605bcb` and `b9219fbfe2852f5ca7088bcedf290526479147a57c3b63cc0a693194cc499179`.

M4.2 does not construct growth/MPE-expansion variables, fabricate medical devices, export `.dta`, or create the final cross-source `production_validation_long.parquet`.

## Completed M4.3 BEA MNE production-side outputs

- `harmonized/production_bea_mne_source_industry_long.parquet`: 49,536 rows and 69 columns at `source_name, source_country_id, model_sector, year, metric_name`. It retains all source geographies and industries for six direct BEA metrics, including canonical aggregate overrides, suppression, small-value, negative-value, raw-code, release, and source-file fields.
- `harmonized/production_validation_bea_mne_long.parquet`: 11,910 rows and 66 columns at `country_iso3, analysis_sector, year, source_name, metric_name`. It covers 57 actual countries and 397 observed country-years. Four strict main sectors produce 9,528 rows; a separately flagged Transportation-equipment autos proxy produces 2,382 robustness rows.
- Builder/config: `code/data_processing/build_production_bea_mne_long.py` and `configs/production_bea_mne_rules.yaml`.
- Validation: `data/validation/production_bea_mne_validation.json` and `.md`, status PASS. All 35 raw XLS hashes, input contracts, aggregate filtering, source/analysis keys, strict disclosure formulas, source-to-analysis reconciliation, negative value added, trade directions, 69/66 aliases, and both deterministic hashes are validated. SHA256 values are `016c7b10891e3770c14eeb9cf0f489bd9d80281c91bd1e10e2a883f76205b514` and `21d9998c77e9fa8b458af288a36746567d4ade49c3a50360a0f684b329691ade`.

For multi-industry cells, `value` is available only when all required source industries are disclosed. `source_disclosed_value_sum` is a coverage diagnostic, not a complete total. `(*)` remains 0.0 with a small-value flag; suppressed values remain missing. Autos proxy rows must never enter the main join. M4.4 BEA FDI is documented below.

## Completed M4.4 BEA direct-investment outputs

- `harmonized/production_bea_fdi_source_industry_long.parquet`: 34,830 rows and 73 columns at `source_name, investment_direction, source_country_id, model_sector, year, metric_name`. It retains all source geographies and industries for position, flows, and income, including 3,060 canonical aggregate-geography source rows, signed values, raw codes, suppression, small-value, direction-role, metric-time, source-URL, and project-relative source-file fields.
- `harmonized/production_validation_bea_fdi_long.parquet`: 7,125 rows and 72 columns at `country_iso3, investment_direction, analysis_sector, year, source_name, metric_name`. It contains 60 actual countries and 475 observed country-direction-years without filling missing directions. Four strict main sectors produce 5,700 rows; an isolated Transportation-equipment autos proxy produces 1,425 rows.
- Builder/config: `code/data_processing/build_production_bea_fdi_long.py` and `configs/production_bea_fdi_rules.yaml`.
- Validation: `data/validation/production_bea_fdi_validation.json` and `.md`, status PASS. Six raw files, frozen inputs, country/sector/time mappings, direction roles, source identity, suppression/small/negative snapshots, strict disclosure formulas, zero classifications, 73/72 aliases, and both deterministic hashes are validated. SHA256 values are `e947317c827f975aab78fc9727594094d540e1b4b27a8a6b166eca3fd28d883a` and `8f296d59d58ad08078c9792f862c503f371537ccc84395d5bffdb00e343b6fcf`.

Position, flows, and income remain separate metrics and cannot be added to a `total_fdi`. Outward and inward rows have different foreign-country roles and flow sign conventions. Suppressed values are missing; `(*)` is zero with a small-value flag; negative values retain the BEA sign. The analysis table distinguishes exact zero, small-value zero, and signed cancellation-to-zero. Autos proxy rows must never enter the main join.

## Completed M4.5 Mexico FDI outputs

- `harmonized/production_mexico_fdi_source_sector_period_long.parquet`: 902,608 rows and 73 columns at the published parent-country × SCIAN source grain for quarter, calendar year, and H1. It preserves all SCIAN hierarchy levels, 86,123 quarterly confidential cells, 19,980 quarterly residual-country rows, signed values, source files, and explicit 2024 incomplete annual rows.
- `harmonized/production_validation_mexico_fdi_parent_sector_period_long.parquet`: 28,560 rows and 68 columns at parent/residual-country × seven direct analysis sectors × period. It contains 18,870 quarterly, 4,845 annual, and 4,845 H1 rows over 255 published support cells. Strict values are available for 11,410/2,099/2,566 rows respectively; suppressed components remain missing and disclosed sums remain diagnostic.
- `harmonized/production_mexico_fdi_benchmark_period_long.parquet`: 1,867 rows and 59 columns containing 156 national totals, 1,191 parent-country annual margins, and 520 two-digit sector annual margins. These scopes are explicit and non-additive.
- Builder/config: `code/data_processing/build_production_mexico_fdi_long.py` and `configs/production_mexico_fdi_rules.yaml`.
- Validation: `data/validation/production_mexico_fdi_validation.json` and `.md`, status PASS with 100 checks. All nine raw/interim identities, keys, mappings, time scopes, strict/disclosed formulas, national benchmark, margin gaps, aliases, and three deterministic hashes are validated. SHA256 values are `998b1f3245fe06ade332411421c9933f031081921e0847b14e13fa5707d24542`, `98191b4362b2ff1b7d91733d1f8ba7a25dc24028c97b848fe62f165e12d0b89e`, and `a65f82ba2960987df8d22bccb883f8eda11db641a3f9528148242341091a4806`.

Mexico FDI is a signed inward financial flow, not production, employment, plant entry, or causal relocation. Parent is the reported source jurisdiction rather than a host-country key or guaranteed ultimate owner. `C` is never set to zero, national Q3-Q4 is never allocated to 2024 joint detail, and SCIAN hierarchy levels are never added together.

## Completed M4.6 cross-source production evidence outputs

- `harmonized/production_validation_long.parquet`: 113,302 × 83 complete evidence registry. Key: `source_table, source_observation_id`. It is a one-to-one standardized union of ICIO analysis, AMNE host-sector, BEA MNE analysis, BEA FDI analysis, Mexico parent-sector-period, and Mexico benchmark-period rows.
- `harmonized/production_validation_main_host_sector_year_long.parquet`: 73,368 × 83 strict activity subset. Key: `country_iso3, analysis_sector, year, source_name, metric_name`. It contains ICIO, AMNE, and BEA MNE main sectors only.

The complete registry uses five exhaustive `join_role` classes, retains separate country/host/parent/origin/destination roles, and never converts financial evidence or proxy sectors into production. Missing, suppressed, confidential, partial-disclosure, signed, zero, incomplete-period, allocation, metric, unit, and provenance states remain explicit. All rows are non-additive across sources. Validation is 137/137 PASS; deterministic SHA256 values are `4b27154fe00c75b44f23724f7940799363be4212b72c83757a5a389111a6c69a` and `2ca54343f0d5bef9c42532a1c79c0d4864f32764f35f4d5a7751170b6c44a27d`. M4.7 remains pending and must not fabricate ICIO observations outside 2017, 2018, and 2022.

Every processed output must be reproducible from `data/interim/`, documented by a build script, and retain source/provenance fields needed to audit aggregation and suppression.
