# Code Directory

Code is organized into three layers.

| Path | Role |
|---|---|
| `data_build/` | Build ICIO, AMNE, and trade inputs. |
| `analysis/` | Produce descriptive evidence and first-stage validation tables/figures. |
| `model_core/` | Host reusable MATLAB model code after migration from the reference package. |

No production code has been added in the setup phase. The first implementation step should build a small, auditable data sample before migrating MATLAB model functions.
