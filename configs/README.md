# Configs

This directory contains the tracked definitions used by the data pipeline:

| File | Current role |
|---|---|
| `data_versions.yaml` | Source vintages, coverage, build status, output paths, and interpretation rules. |
| `country_groups.yaml` | Source/destination blocs, connector candidates, and comparison countries. |
| `sector_scope.yaml` | Priority sectors and sector-scope definitions. |
| `time_windows.yaml` | Baseline, policy, and post-policy time windows. |
| `us_census_country_codes.yaml` | Census country-code mappings used by the import pipeline. |
| `analysis_sample_v1.yaml` | Frozen first-stage country, sector, time, frequency, structural-baseline, and Stata-handoff scope used by the data-merge pipeline. |
| `country_concordance_overrides.yaml` | Auditable country-name exceptions, canonical-name overrides, and BEA labels that must be treated as aggregates despite source area-type labels. |
| `time_aggregation_rules.yaml` | Metric-level temporal semantics, valid annual operators, missing-period rules, and the partial-year treatment for Mexico FDI in 2024. |
| `hs_revision_rules.yaml` | Dataset/year-specific HS editions, official UNSD/WCO bridge sources, the canonical HS2012 conversion rule, and restrictions on unweighted many-to-many correlations. |
| `product_sector_rules.yaml` | Official UNSD HS-BEC-ISIC source, HS-to-`analysis_sector` precedence, first-round exclusions, CEPII `271000` treatment, and BEC ambiguity rules. |
| `source_sector_rules.yaml` | OECD ICIO/AMNE, BEA MNE/FDI, and Mexico SCIAN mappings to `analysis_sector`, including aggregate-level exclusions and mixed-sector limitations. |
| `product_treatment_rules.yaml` | Section 301 HS2017-to-analysis-product aggregation, 2017 import weights, gross statutory interpretation, and 2024-review separation. |
| `connector_trade_rules.yaml` | BACI China-to-USA, source-to-connector, and connector-to-USA flow definitions, connector groups, Taiwan proxy, and self-trade rules. |
| `trade_treatment_merge_rules.yaml` | Many-to-one product-year treatment merge into connector-product-year trade and trade-total reconciliation rules. |
| `census_harmonization_rules.yaml` | Year-specific Census HS mapping, additive flow fields, 15-origin scope, quantity unavailability, and monthly/annual outputs. |
| `section301_2024_review_rules.yaml` | Exact HTS8/HTS10 2024 review extension kept separate from the historical HS6 panel. |
| `connector_trade_sector_rules.yaml` | Frozen M3.1 input hashes, keys, eligible sectors, four-flow aggregation/coverage fields, policy formulas, validation tolerances, deterministic rebuild path, and 70 Stata aliases. |
| `connector_trade_sector_window_rules.yaml` | Frozen M3.2 M3.1-input/time-window hashes, 4/2/5-year complete windows, annual-mean and ratio-of-sums formulas, two output keys, growth edge rules, validation tolerances, deterministic rebuild paths, and resolved Stata alias templates. |
| `connector_trade_sector_growth_diagnostic_rules.yaml` | Frozen M3.3 comparison-input hash/schema, four-flow long key, USD 25 million and nearest-rank p10 small-base rules, robust-z/mechanical abnormal flags, p5/p95 winsorized sensitivity, deterministic rebuild paths, expected diagnostic counts, and 64 Stata aliases. |
| `connector_trade_reorganization_indicator_rules.yaml` | Frozen M3.4 M2/M3.2/M3.3 input hashes/schemas, three natural-grain outputs, USD 25 million signed replacement rule, separate China/East Asia source ratios, exposure-missing and positive/p75 overlap rules, HS6 correlation/value-share denominators, deterministic rebuild paths, expected counts, and 56/92/49 Stata aliases. |
| `connector_trade_sector_common_panel_rules.yaml` | Frozen M3.5 M3.4 sector/comovement hashes and schemas, one-to-one connector-sector join, complete 13-connector × 7-sector sample, group/order fields, explicit no-selection flags, deterministic rebuild paths, expected preservation counts, and 152 Stata aliases. |

Country groups and data versions are active inputs. M1 country, time, product, and source-sector concordances plus M3.1 annual aggregation, M3.2 window/growth construction, M3.3 growth diagnostics, M3.4 trade-reorganization indicators, and the M3.5 complete comparison panel are complete. M3.6 sensitivity inputs, connector rankings, and executable counterfactual scenario files remain pending.

The model implementation must avoid hard-coded country indices in MATLAB. Scenario files should define:

- source bloc and destination bloc;
- connector-country candidates;
- sectors included;
- baseline year and shock year;
- trade-cost and MP-cost changes;
- output naming suffix.

The first scenario schema should explicitly separate:

- `scenario_a_trade_only_lower_bound`: connector trade access changes, with MP margin held at `hgamma = 1`;
- `scenario_b_incumbent_mp_baseline`: connector `hgamma` disciplined by AMNE, BEA MNE, or affiliate/ownership moments;
- `scenario_c_total_mp_upper_bound`: connector `hgamma` disciplined by total FDI, affiliate expansion, and production-side expansion. fDi Markets remains an optional later evidence layer and is not part of the current data batch.

Scenario C must be labeled as an upper-bound proxy. It is not a fixed-cost entry model and should not be described as structurally identified entry-margin welfare.
