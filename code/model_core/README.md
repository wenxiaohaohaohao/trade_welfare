# Model Core

This folder will host reusable MATLAB model functions after migration from `reference/EL_replication/EL_replication`.

Migration rule:

- copy only general model functions after documenting changes;
- remove hard-coded country indices;
- require country, sector, and scenario configuration inputs;
- preserve welfare decomposition labels and meanings.

The first model runner should report direct fragmentation plus three connector scenarios:

- Scenario A: trade-only connector lower bound, with connector `hgamma = 1`;
- Scenario B: incumbent MP-intensive baseline, with `hgamma` disciplined by AMNE/BEA affiliate activity;
- Scenario C: total MP-adjustment upper-bound proxy, with `hgamma` disciplined by total FDI, fDi Markets, affiliate expansion, and production-side expansion.

Scenario C is a scenario input, not a new entry block. Do not add wording or output labels implying fixed-cost affiliate entry unless the model is explicitly extended.

Do not copy Russia-specific counterfactual scripts as project entrypoints.
