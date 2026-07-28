# Data Processing

This directory contains reproducible `data/interim/` to `data/processed/` pipelines. It is separate from `code/data_build/`, which remains responsible for source download and raw-to-interim construction.

## Current stage

M0, M1, M2, and M3.1-M3.6 in `data/data_merge_checklist.md` are complete. M3.6 adds separate long interfaces for alternative time windows, source-bloc definitions, and exposure definitions while retaining the full 13-connector × 7-sector comparison sample. It does not construct a connector score or ranking and does not include production-side evidence. M4.1 is the next planned stage, but it is not started by the M3.6 build.

## Living collaborator audit and variable contract

The two authoritative editable documents are:

- `docs/data_processing_audit_trail.md`: source-to-processed lineage, transformations, decisions, validations, hashes, and incident history.
- `docs/variable_construction_catalog.md`: variable-level grain, formula, unit, purpose, interpretation boundary, missing-value rule, Stata name/type, and validation contract.

Their collaborator-facing PDFs are `output/pdf/data_processing_audit_trail.pdf` and `output/pdf/variable_construction_catalog.pdf`. Rebuild both from the project root with:

```powershell
python code\data_processing\build_data_processing_audit_pdf.py --project-root . --overwrite
python code\data_processing\build_data_processing_audit_pdf.py --project-root . --source docs\variable_construction_catalog.md --output output\pdf\variable_construction_catalog.pdf --overwrite
```

The renderer writes a build-summary JSON beside each PDF with the Markdown/PDF SHA256 values, page count, font and text checks. Beginning with M3.1, a checklist item is not complete until its inputs, transformations, keys, output, validation, limitations and change-log entry are added to the audit; its variables, formulas, uses and Stata contract are updated in the catalog; and both PDFs are rebuilt and visually checked.

Run the M0.3 input manifest builder from the project root:

```powershell
python code\data_processing\build_input_manifest.py --project-root . --overwrite
```

The registered validation outputs are:

- `data/validation/data_merge_input_manifest.json`
- `data/validation/data_merge_input_manifest.md`

Run the M0.4 input-quality audit after the manifest passes:

```powershell
python code\data_processing\audit_input_quality.py --project-root . --overwrite
```

The registered validation outputs are:

- `data/validation/data_merge_input_quality_audit.json`
- `data/validation/data_merge_input_quality_audit.md`

Validate and freeze the first-stage analysis sample after M0.4 passes:

```powershell
python code\data_processing\validate_analysis_sample.py --project-root . --overwrite
```

The registered outputs are:

- `configs/analysis_sample_v1.yaml`
- `data/validation/analysis_sample_v1_validation.json`
- `data/validation/analysis_sample_v1_validation.md`

Build the M1.1 cross-source country master after M0 passes:

```powershell
python code\data_processing\build_country_master.py --project-root . --overwrite
```

The canonical output and registered validation are:

- `data/processed/concordances/country_crosswalk.parquet`
- `data/validation/country_crosswalk_validation.json`
- `data/validation/country_crosswalk_validation.md`

Build and validate the M1.3 metric-level time rules after the country geography rules pass:

```powershell
python code\data_processing\build_time_rules.py --project-root . --overwrite
```

The canonical output and registered validation are:

- `data/processed/concordances/time_aggregation_rules.parquet`
- `data/validation/time_aggregation_rules_validation.json`
- `data/validation/time_aggregation_rules_validation.md`

The time-rule builder checks configured metrics against actual schemas and observed periods. It distinguishes monthly and quarterly additive flows, annual activity, non-additive BEA stocks, unavailable measures, ICIO benchmark years, confidential Mexico quarters, and the partial 2024 Mexico calendar year.

Build and validate the M1.4 HS revision bridge after the time rules pass:

```powershell
python code\data_processing\build_hs_revision_bridge.py --project-root . --overwrite
```

The builder reads the official UNSD HS2017-to-HS2012 and HS2022-to-HS2012 workbooks without altering them. It writes a one-target canonical conversion, the full unweighted correlation, and a Census `year × source_hs6` crosswalk. The canonical conversion has weight 1 and cannot expand values; multi-target correlations remain unweighted and cannot be used for aggregation until a separate weighting design passes validation.

Build and validate the M1.5 HS-to-sector and BEC crosswalk after the HS revision bridge passes:

```powershell
python code\data_processing\build_product_sector_crosswalk.py --project-root . --overwrite
```

The registered products are:

- `data/processed/concordances/product_sector_crosswalk.parquet`
- `data/validation/product_sector_crosswalk_validation.json`
- `data/validation/product_sector_crosswalk_validation.md`

The crosswalk has one row per BACI/CEPII `analysis_hs6`. It uses official UNSD HS2012-to-BEC Rev.5 and ISIC Rev.4 fields. `analysis_sector` is a one-to-one research sector; BEC end use remains independent. Composite BEC labels and the CEPII `271000` collapse do not receive guessed allocation weights. BACI `999999` remains an explicit residual product.

Build and validate the M1.6 source-sector crosswalk:

```powershell
python code\data_processing\build_source_sector_crosswalk.py --project-root . --overwrite
```

The registered products are:

- `data/processed/concordances/source_sector_crosswalk.parquet`
- `data/validation/source_sector_crosswalk_validation.json`
- `data/validation/source_sector_crosswalk_validation.md`

Run the consolidated M1.7-M1.8 uniqueness, weight, integration, and value-coverage audit after all concordances pass:

```powershell
python code\data_processing\build_concordance_coverage_report.py --project-root . --overwrite
```

The consolidated reports are `data/validation/concordance_coverage.json` and `data/validation/concordance_coverage.md`. Coverage rates use absolute observed values for signed FDI metrics and never replace suppressed, confidential, or source-missing cells with zero.

## M2 product treatment and trade harmonization

Run the validated M2 builders in order:

```powershell
python code\data_processing\build_product_treatment_panel.py --project-root . --overwrite
python code\data_processing\build_connector_trade_panel.py --project-root . --overwrite
python code\data_processing\merge_trade_treatment_panel.py --project-root . --overwrite
python code\data_processing\build_census_harmonized_panels.py --project-root . --overwrite
python code\data_processing\build_section301_2024_review_extension.py --project-root . --overwrite
```

The pure BACI trade-leg output is `connector_trade_legs_hs6_year.parquet`; the merged treatment output is `connector_trade_hs6_year.parquet`. The separate base prevents an in-place merge from obscuring trade-value reconciliation. The Census monthly output remains sparse for event-study use, while the annual output is a complete 15-origin product-year grid. The 2024 review output preserves exact HTS8/HTS10 and has no `analysis_hs6` field.

## M3.1 annual connector-sector aggregation

Run the validated single-module builder from the project root:

```powershell
python code\data_processing\build_connector_trade_sector_panel.py --project-root . --overwrite
```

Registered files:

- config: `configs/connector_trade_sector_rules.yaml`;
- canonical output: `data/processed/harmonized/connector_trade_sector_year.parquet`;
- validation: `data/validation/connector_trade_sector_panel_validation.json` and `.md`.

The output has 1,001 rows at `connector_iso3 × analysis_sector × year`. It sums only the 4,237 canonical eligible products with sector weight 1, reconciles four trade flows to product-level eligible totals, reports the 965 non-eligible products through flow-specific connector-year coverage fields, and recalculates sector policy numerators, denominators, rates, and shares. China-to-USA and policy fields are repeated across connectors; coverage fields are repeated across sectors; explicit flags prohibit treating either as additive. The builder also performs a second build in `tmp/m3_1_determinism/`, requires an identical Parquet SHA256, and removes that project-local temporary output.

M3.1 output SHA256: `95e547267892c4bc883788542f0e59ba284441b42f4ce1d379aea71a2f978c8c`. The 70 frozen Stata aliases pass completeness, uniqueness, and 32-character checks, but `.dta` export remains an M7 task.

## M3.2 trade windows and post-pre growth

Run the validated single-module builder from the project root:

```powershell
python code\data_processing\build_connector_trade_sector_window_panel.py --project-root . --overwrite
```

Registered files:

- config: `configs/connector_trade_sector_window_rules.yaml`;
- long canonical output: `data/processed/harmonized/connector_trade_sector_window.parquet`;
- comparison canonical output: `data/processed/harmonized/connector_trade_sector_window_comparison.parquet`;
- validation: `data/validation/connector_trade_sector_window_validation.json` and `.md`.

The long output has 273 rows at `connector_iso3 × analysis_sector × window_id` and 79 columns. It uses annual means for the complete pre 2014-2017, shock 2018-2019, and post 2020-2024 windows. Included-value coverage is recomputed as the ratio of summed eligible value to summed full-universe value; policy rates and shares are recomputed from annual-mean numerators and transparent 2017 denominators.

The comparison output has 91 rows at `connector_iso3 × analysis_sector` and 142 columns. For each of the four trade flows it contains pre/shock/post levels, post-pre level change, Davis-Haltiwanger growth, positive-base log growth, zero/defined flags, and observed-year counts. It also carries pre/shock/post coverage and policy summaries. It contains no policy growth, small-base decision, capping, winsorization, replacement ratio, or ranking.

Output SHA256 values:

- long: `310da7f289d8760d3ead34215a294be18275c758a2084cfd9f905988b695e704`;
- comparison: `be5f3a025a81d36d5a9bb1bd137d4bed9325a68ab5f1cb7f4d946a2373fbeb04`.

Validation status is PASS. Both outputs were rebuilt a second time in `tmp/m3_2_determinism/`; each SHA256 matched exactly, and both the determinism and candidate directories were removed. The 79 long aliases and 142 comparison aliases are complete, unique, and at most 13 characters. `.dta` export remains an M7 task.

## M3.3 growth diagnostics

Run the validated single-module builder from the project root:

```powershell
python code\data_processing\build_connector_trade_sector_growth_diagnostics.py --project-root . --overwrite
```

Registered files:

- config: `configs/connector_trade_sector_growth_diagnostic_rules.yaml`;
- canonical output: `data/processed/harmonized/connector_trade_sector_growth_diagnostics.parquet`;
- validation: `data/validation/connector_trade_sector_growth_diagnostics_validation.json` and `.md`.

The output has 364 rows and 64 columns at `connector_iso3 × analysis_sector × flow_id`: four flow rows for each of the 91 M3.2 connector-sector comparison cells. It copies and reconciles pre/shock/post levels, post-pre level change, raw DH/log growth, zero/defined flags, and observed-year counts from M3.2.

The frozen small-base rule combines pre zero, an absolute pre annual-mean threshold of USD 25 million, and a nearest-rank 10th-percentile threshold within each connector-specific `flow_id × analysis_sector` group. The repeated China-to-USA benchmark does not receive a connector-relative threshold. Robust-z/MAD and `|DH| >= 1.5` flags are advisory only. Flow-level p5/p95 linear/type-7 winsorized DH/log values are sensitivity variables; they never overwrite raw growth or level change.

Validation status is PASS. The natural key is unique, every connector-sector has four flows, source and formula reconciliation gaps are zero, TWN has 28 proxy rows, and all 64 Stata aliases are unique and at most 11 characters. The output was rebuilt in `tmp/m3_3_determinism/`; its SHA256 matched `fe69d953cd84a2acfc64ddb17b1ee57e3d0e44f7b44cad348f9016aee7e0953d`, and candidate/determinism directories were removed. `.dta` export remains an M7 task.

## M3.4 trade reorganization indicators

Run the validated single-module builder from the project root:

```powershell
python code\data_processing\build_connector_trade_reorganization_indicators.py --project-root . --overwrite
```

Registered files:

- config: `configs/connector_trade_reorganization_indicator_rules.yaml`;
- product output: `data/processed/harmonized/connector_trade_product_reorganization_window.parquet`;
- sector output: `data/processed/harmonized/connector_trade_sector_reorganization_indicators.parquet`;
- co-movement output: `data/processed/harmonized/connector_trade_sector_product_comovement.parquet`;
- validation: `data/validation/connector_trade_reorganization_indicators_validation.json` and `.md`.

The outputs are 55,081 × 56 at `connector_iso3 × analysis_hs6`, 91 × 92 at `connector_iso3 × analysis_sector`, and 91 × 49 at `connector_iso3 × analysis_sector`. Replacement ratios use a signed connector-export gain and are defined only for a China-to-USA decline strictly above USD 25 million. China and extended East Asia input/export ratios remain separate. Product exposure missingness is preserved, and exposure-weighted measures report observed-value coverage. Product correlations and condition shares use explicit active-product and sum-positive-product-gain denominators.

Validation status is PASS. All three keys are unique; 28 exposure-missing products remain missing; replacement, source-ratio, exposure, and co-movement formulas pass independent checks; and 56/92/49 Stata aliases are complete and at most 14 characters. Second-build SHA256 values match `1c83dc1070656c903d625b2e85c82ea6e7afa18535105351ccef24a405ed2c34`, `f13c5f8aa0c4402d0b467a06a6b99ba8ddc8389d47ede9ba8c8036275c1d74f2`, and `3095cd39a7355ce6968e0e5c29956841fd9e40bc72238d06aafe8d3ef0c3b0f1`. Candidate and determinism directories were removed. `.dta` export remains an M7 task.

## M3.5 complete connector-sector comparison panel

Run the validated single-module builder from the project root:

```powershell
python code\data_processing\build_connector_trade_sector_common_panel.py --project-root . --overwrite
```

Registered files:

- config: `configs/connector_trade_sector_common_panel_rules.yaml`;
- output: `data/processed/harmonized/connector_trade_sector_common_panel.parquet`;
- validation: `data/validation/connector_trade_sector_common_panel_validation.json` and `.md`.

The output is 91 × 152 at `connector_iso3 × analysis_sector`. It performs a one-to-one join of the 91-row M3.4 sector indicator and product co-movement tables, validates all common fields, retains all 3 core connectors, 7 Asian comparators, and 3 other candidates over all 7 sectors, and adds explicit sample-role, ordering, source-match, and no-selection fields. It does not construct a score or delete low-ranked, missing-ratio, or otherwise inconvenient observations.

Validation status is PASS. All 91 keys match on both inputs; the group row counts are 21/49/21; all 13 × 7 cells are retained; 26 defined and 65 missing replacement ratios remain unchanged; all four product correlations remain defined for 91 cells; TWN retains seven proxy rows; and all 152 Stata aliases are unique and at most 14 characters. The canonical and second-build SHA256 are both `36c58c229f3f43e86f7ff7570fc6a1ffe08ccb8fd3259bb5853abece3171f682`. Candidate and determinism directories were removed. `.dta` export remains an M7 task.

## M3.6 sensitivity inputs

Run the validated single-module builder from the project root:

```powershell
python code\data_processing\build_connector_trade_sector_sensitivity.py --project-root . --overwrite
```

Registered files:

- config: `configs/connector_trade_sector_sensitivity_rules.yaml`;
- time-window output: `data/processed/harmonized/connector_trade_sector_time_window_sensitivity.parquet`;
- source-bloc output: `data/processed/harmonized/connector_trade_sector_source_bloc_sensitivity.parquet`;
- exposure-definition output: `data/processed/harmonized/connector_trade_sector_exposure_definition_sensitivity.parquet`;
- validation: `data/validation/connector_trade_sector_sensitivity_validation.json` and `.md`.

The time-window table is 1,092 × 56 at `connector_iso3 × analysis_sector × flow_id × window_spec_id`. It compares the 2014-2017 annual-mean baseline with 2020-2024 (`primary_post`), 2020-2023 (`exclude_2024`), and 2018-2019 (`shock_only`) for all four trade flows. It retains level changes, DH/log growth, coverage, within-comparison-window annual DH volatility, positive-growth-year shares, and differences from the primary specification. The two-year shock window has one annual transition, so its sample SD is missing by design.

The source-bloc table is 182 × 64 at `connector_iso3 × analysis_sector × source_bloc_id`. It keeps China-only and extended East Asia separate, reports level/growth/input-export-ratio/product-co-movement fields in a common schema, and records differences and direction agreement relative to China-only. Extended East Asia contains China; its difference from China-only is the incremental KOR/JPN/TWN component after excluding connector self-trade, not an independent sample.

The exposure-definition table is 364 × 47 at `connector_iso3 × analysis_sector × exposure_definition_id`. It retains tariffed-product export overlap, continuous export-weighted exposure, positive-exposure gain share, and sector-top-quartile-exposure gain share. Pre/post fields are missing by design for the two gain-share definitions. Because these definitions have different estimands and units, the builder does not subtract them from one another or turn them into ranks.

Validation status is PASS. All three keys are unique; every time-window pair is complete; all 1,092 log-growth values are defined; the expected negative-change, source-direction, self-trade, exposure-missing, and TWN-proxy states are preserved; and 56/64/47 Stata aliases are complete, unique, and at most 13 characters. Canonical and second-build SHA256 values match exactly:

- time window: `1594fadeb348f88e07b2ec8f43ca3708f49f9e06a0b78fafe24ffb6417635aad`;
- source bloc: `67fbf760adb01a18d4e0e4f9ddd44eef9f3d2d2496a0a60d358cf8eab77e1eda`;
- exposure definition: `96144e95dd525103b658ed7220a15d2f3c7c7acf79ea3f314314112971dc7cbd`.

Candidate and determinism directories were removed. `.dta` export remains an M7 task.

## Stata handoff contract

The final collaborator package will include Stata-compatible `.dta` copies of analysis-ready processed data, a variable dictionary, and a batch-verifiable `.do` entry script. The Stata export stage will enforce:

- variable names no longer than 32 characters;
- deterministic variable order and storage types;
- explicit variable and value labels where appropriate;
- documented keys that pass `isid` in Stata;
- preserved missing, suppressed, confidential, aggregate, and allocated flags;
- a project-local `STATATMP` path on the F drive;
- a verification log with an explicit success marker.

Parquet remains the lossless canonical processed format. `.dta` files are collaborator-facing exports and must reconcile to the canonical Parquet row counts, keys, and numeric summaries.
