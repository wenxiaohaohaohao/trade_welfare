# Model Inputs

Store MATLAB-ready CSV inputs here. The target interface should remain close to the reference package's `tomatlab/*.csv` structure where possible.

## Current Baselines

Validated OECD ICIO regular-table baselines exist for 2017, 2018, and 2022:

- `icio_baseline_2017/`
- `icio_baseline_2018/`
- `icio_baseline_2022/`

Each directory contains `X_baseline.csv`, `va_baseline.csv`, `IO_baseline.csv`, `trshare_baseline.csv`, and `manifest.json`. The manifests record schemas, units, and source parquet files.

Scenario-specific shock files are not yet built. The next model-input stage must add transparent country/sector indices plus Scenario A/B/C `htau` and `hgamma` inputs without hard-coded country positions.
