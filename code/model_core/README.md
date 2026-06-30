# Model Core

This folder will host reusable MATLAB model functions after migration from `reference/EL_replication/EL_replication`.

Migration rule:

- copy only general model functions after documenting changes;
- remove hard-coded country indices;
- require country, sector, and scenario configuration inputs;
- preserve welfare decomposition labels and meanings.

Do not copy Russia-specific counterfactual scripts as project entrypoints.
