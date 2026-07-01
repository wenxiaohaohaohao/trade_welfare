# Data Directory

This directory documents the data pipeline. Large raw and generated data files are ignored by git.

## Data Sources

| Source | Intended use | Status |
|---|---|---|
| OECD ICIO | Country-sector IO structure, final demand, value added, gross output | Not downloaded in this setup step. Source: https://www.oecd.org/sti/ind/inter-country-input-output-tables.htm |
| OECD AMNE | Foreign affiliate activity and MP-related production relocation | Not downloaded in this setup step. Source: https://www.oecd.org/en/data/datasets/activity-of-multinational-enterprises.html |
| BEA U.S. MNE MOFA country-industry tables | U.S. MNE affiliate activity by host country and affiliate industry | Mexico x Transportation equipment verified for 2020-2022; see `data/bea_mne_mexico_transportation_equipment_2020_2022.md`. Source: https://www.bea.gov/international/di1usdop |
| Comtrade or BACI | Bilateral trade rerouting and connector ranking | Source choice pending data-access comparison. |
| Reference replication data | Conceptual model interface only | Kept under `reference/`, not copied here. |

## Subdirectories

| Path | Contents |
|---|---|
| `raw/` | Original downloaded files, never edited manually. |
| `interim/` | Cleaned but not final data extracts. |
| `processed/` | Analysis-ready panel files. |
| `model_inputs/` | MATLAB-ready CSV inputs modeled after the reference package. |
| `sample/` | Tiny tracked sample files may be stored here later for tests. |

## Required Metadata For Each Download

Every raw data batch should be accompanied by a text or Markdown note with:

- source URL;
- download date;
- data vintage or release version;
- years covered;
- country and sector coverage;
- license or access notes;
- checksum when practical.

Use `docs/data_source_log.md` as the running registry for these records.

## Non-Negotiable Rule

Do not overwrite raw data in place. If a source is updated, save it under a dated or versioned folder and update the metadata note.
