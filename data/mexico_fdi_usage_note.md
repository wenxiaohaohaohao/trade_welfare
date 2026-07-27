# Mexico Official FDI Data Usage Note

## Purpose

This batch archives and normalizes official inward FDI flows published by Mexico's Secretaría de Economía through datos.gob.mx and Data México. It supports the 2021-2024 Mexico nearshoring check and Scenario C / `hgamma` discipline.

The archived raw snapshot and its hashes are dated 2026-07-18.

FDI is a financial flow. It is not affiliate output, value added, employment, plant entry, or proof that production moved from China to Mexico. Use it together with AMNE, BEA MNE, trade, and production-side evidence.

`fDi Markets` is explicitly outside this batch and was not downloaded or processed.

## Reproduction

```powershell
python code\data_build\download_build_mexico_fdi.py --project-root . --overwrite
```

If the local network uses an intercepting TLS proxy that prevents certificate validation, add `--insecure`. The script never overwrites an existing raw file. Archive a revised official vintage in a new versioned raw directory before changing the configured inputs, because historical official data may be revised retroactively.

## Coverage

Data México API outputs:

| Output | Frequency | Coverage | Rows |
|---|---|---|---:|
| `mexico_fdi_national_quarterly.parquet` | Quarter | 1999Q1-2024Q4 | 104 |
| `mexico_fdi_national_investment_type_quarterly.parquet` | Quarter x investment type | 1999Q1-2024Q4 | 312 |
| `mexico_fdi_parent_country_annual.parquet` | Year x source country | 1999-2024 | 1,191 |
| `mexico_fdi_sector_annual.parquet` | Year x SCIAN sector | 1999-2024 | 520 |

datos.gob.mx detailed CSV outputs:

| Output | Dimensions | Coverage | Rows | Confidential cells |
|---|---|---|---:|---:|
| `mexico_fdi_state_country_quarterly.parquet` | State x source country x quarter | 2006Q1-2024Q2 | 96,200 | 0 |
| `mexico_fdi_state_sector_quarterly.parquet` | State x SCIAN level x quarter | 2006Q1-2024Q2 | 616,420 | 126,221 |
| `mexico_fdi_state_investment_type_quarterly.parquet` | State x type x quarter | 2006Q1-2024Q2 | 7,104 | 79 |
| `mexico_fdi_country_sector_quarterly.parquet` | Source country x SCIAN level x quarter | 2006Q1-2024Q2 | 596,366 | 86,123 |
| `mexico_fdi_country_investment_type_quarterly.parquet` | Source country x type x quarter | 2006Q1-2024Q2 | 10,878 | 2,368 |

All output paths are under `data/interim/fdi/`. Raw CSV and API JSON snapshots are under `data/raw/mexico_fdi/`. The complete hash and query record is `data/interim/fdi/mexico_fdi_build_summary.json`. The national API panels include all four quarters of 2024, while the five detailed quarterly cross-tables currently contain only Q1-Q2; use 2024 detail only quarterly or H1-to-H1, not as a full calendar year.

## Variables

Common fields:

| Field | Meaning |
|---|---|
| `year`, `quarter`, `period`, `date` | Time identifiers. Detailed tables use quarterly source dates. |
| `fdi_million_usd` | Official inward FDI flow in current million U.S. dollars. Negative flows are valid and are retained. |
| `fdi_usd` | `fdi_million_usd * 1,000,000`. |
| `confidential_flag` | True when the official CSV reports `C`; the value remains null, not zero. |
| `source_file` | Raw CSV or API JSON source. |

Dimension fields include `host_state_name`, `parent_country_iso3`, `parent_country_name`, `sector_level`, `sector_code`, `sector_name`, and `investment_type` where available.

SCIAN labels are parsed at three levels: two-digit sectors, three-digit subsectors, and four-digit industry groups. The valid range sectors `31-33` and `48-49` are retained as sector codes rather than forced into one two-digit code.

## Country aggregates

The detailed source-country files include special rows:

- `parent_country_total_flag=true` marks `Total general`. Exclude it before summing individual countries or the result will double count the total.
- `parent_country_residual_flag=true` marks `Otros países`. It is an additive residual group but has no ISO3 code.

Named countries use ISO3 codes. The official long Spanish names for China, South Korea, the United States, Russia, the United Kingdom, Czechia, Taiwan, and Venezuela are mapped explicitly.

## Confidentiality and reconciliation

The national quarterly total and the sum of the three investment types agree to within USD 885, which is only API floating-point precision. The validated 2024 national total is USD 36,872.421 million.

Published confidential amounts are suppressed. Rows coded `C` are retained with null values and `confidential_flag=true`; therefore the disclosed country and industry detail does not add exactly to the national total. The maximum annual gaps in the current snapshot are:

| Detail table | Maximum gap to national annual total |
|---|---:|
| Source country | USD 464.170 million |
| SCIAN sector | USD 1,152.320 million |

These gaps are documented source behavior, not values to impute as zero. Use the national panel for total FDI trends and the detailed panels for disclosed composition. Any imputation or residual allocation must be a separate, explicitly documented analysis step.
