# Data Source Log

This file records data-source decisions and downloads. Do not use it to store data.

| Source | URL | Vintage / release | Years | Download date | Local path | Notes |
|---|---|---|---|---|---|---|
| OECD ICIO | https://www.oecd.org/sti/ind/inter-country-input-output-tables.htm | Pending | Pending | Pending | `data/raw/` | Needed for IO, final demand, value added, and gross output. |
| OECD AMNE | https://www.oecd.org/en/data/datasets/activity-of-multinational-enterprises.html | Pending | Pending | Pending | `data/raw/` | Needed for foreign affiliate activity and MP channel. |
| BEA U.S. MNE MOFA country-industry tables | https://www.bea.gov/international/di1usdop | 2025-08 downloadable tables | 2009-2023; verified 2020-2022 for Mexico x Transportation equipment | 2026-07-01 | Raw files: `data/raw/bea_usdia_mofas_2025-08/` (ignored); manifest: `data/bea_usdia_mofas_2025_08_archive_manifest.md`; audit: `data/bea_mne_mofas_mexico_suppression_audit_2020_2022.md`; script: `code/data_build/download_extract_bea_mne_mofas.py` | BEA reports selected annual U.S. MNE activity tables were discontinued or impacted on 2025-08-22 beginning with 2023 preliminary data. Verification found no suppression for Mexico x Transportation equipment in assets, employment, value added, PPE expenditures, or sales for 2020-2022. |
| Comtrade or BACI | Pending | Pending | Pending | Pending | `data/raw/` | Choose after comparing access, coverage, and HS-to-sector concordance quality. |

## Download Rule

For every downloaded batch, add a new row rather than overwriting an existing one. If a source updates, record the new vintage separately.
