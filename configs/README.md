# Configs

Future project runs should put country groups, connector definitions, sector mappings, and counterfactual scenarios here.

The first implementation should avoid hard-coded country indices in MATLAB. Scenario files should eventually define:

- source bloc and destination bloc;
- connector-country candidates;
- sectors included;
- baseline year and shock year;
- trade-cost and MP-cost changes;
- output naming suffix.

The first scenario schema should explicitly separate:

- `scenario_a_trade_only_lower_bound`: connector trade access changes, with MP margin held at `hgamma = 1`;
- `scenario_b_incumbent_mp_baseline`: connector `hgamma` disciplined by AMNE, BEA MNE, or affiliate/ownership moments;
- `scenario_c_total_mp_upper_bound`: connector `hgamma` disciplined by total FDI, fDi Markets project evidence, affiliate expansion, and production-side expansion.

Scenario C must be labeled as an upper-bound proxy. It is not a fixed-cost entry model and should not be described as structurally identified entry-margin welfare.
