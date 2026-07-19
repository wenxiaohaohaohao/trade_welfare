# Code Directory

Code is organized into three layers.

| Path | Role |
|---|---|
| `data_build/` | Build ICIO, AMNE, and trade inputs. |
| `analysis/` | Produce descriptive evidence and first-stage validation tables/figures. |
| `model_core/` | Host reusable MATLAB model code after migration from the reference package. |

`data_build/` now contains reproducible Python pipelines for OECD ICIO, OECD Analytical AMNE, BACI, U.S. Census imports, Section 301, BEA MNE activity, BEA direct investment, and Mexico official FDI. These builders generate the validated interim outputs documented in `data/README.md` and `docs/data_source_log.md`.

The remaining implementation gap is downstream analysis and structural modeling. `analysis/` does not yet contain the connector-ranking, structural-moment, or production-validation pipeline, and `model_core/` does not yet contain migrated MATLAB equilibrium or welfare-decomposition functions.
