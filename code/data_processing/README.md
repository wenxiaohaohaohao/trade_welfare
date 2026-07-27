# Data Processing

This directory contains reproducible `data/interim/` to `data/processed/` pipelines. It is separate from `code/data_build/`, which remains responsible for source download and raw-to-interim construction.

## Current stage

M0, M1, and M2 in `data/data_merge_checklist.md` are complete. The next active task is M3.1: aggregate the validated connector-product-year trade and treatment panel to `connector_iso3 × analysis_sector × year`.

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
