# Interim Data

This directory stores cleaned, source-specific outputs that are reproducible from `data/raw/` and `code/data_build/`.

| Subdirectory | Current contents |
|---|---|
| `trade/` | BACI annual HS6 panels, U.S. Census monthly HS10/HS6 imports, and the BACI HS2017 U.S.-import denominator. |
| `policy/` | Section 301 HTS10 events, annual HS6 gross statutory exposure, and the separate exact 2024 review table. |
| `production/` | OECD ICIO output/value-added/final-demand objects and long-form IO shares. |
| `mne/` | OECD Analytical AMNE affiliate activity/MP shares and BEA U.S. MNE affiliate activity. |
| `fdi/` | BEA direct-investment country-industry data and nine Mexico official FDI tables. |

Each output family has a `*_build_summary.json` recording coverage, row counts, validation checks, and source provenance. Interim files remain source-specific; they are not yet the harmonized analysis panel.
