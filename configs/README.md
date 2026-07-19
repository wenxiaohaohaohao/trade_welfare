# Configs

This directory contains the tracked definitions used by the data pipeline:

| File | Current role |
|---|---|
| `data_versions.yaml` | Source vintages, coverage, build status, output paths, and interpretation rules. |
| `country_groups.yaml` | Source/destination blocs, connector candidates, and comparison countries. |
| `sector_scope.yaml` | Priority sectors and sector-scope definitions. |
| `time_windows.yaml` | Baseline, policy, and post-policy time windows. |
| `us_census_country_codes.yaml` | Census country-code mappings used by the import pipeline. |

Country groups and data versions are active inputs. Executable counterfactual scenario files and a final cross-source sector concordance are still pending.

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
