# Data Directory

This directory documents the data pipeline. Large raw and generated data files are ignored by git.

## Data Sources

| Source | Intended use | Status |
|---|---|---|
| OECD ICIO | Country-sector IO structure, final demand, value added, gross output | Not downloaded in this setup step. Source: https://www.oecd.org/sti/ind/inter-country-input-output-tables.htm |
| OECD AMNE | Foreign affiliate activity and MP-related production relocation | Not downloaded in this setup step. Source: https://www.oecd.org/en/data/datasets/activity-of-multinational-enterprises.html |
| BEA U.S. MNE MOFA country-industry tables | U.S. MNE affiliate activity by host country and affiliate industry | Archived locally under `data/raw/bea_usdia_mofas_2025-08/` (ignored by git). Mexico x Transportation equipment verified for 2020-2022; see `data/bea_mne_mexico_transportation_equipment_2020_2022.md`, `data/bea_usdia_mofas_2025_08_archive_manifest.md`, and `data/bea_mne_mofas_mexico_suppression_audit_2020_2022.md`. Source: https://www.bea.gov/international/di1usdop |
| BEA Direct Investment by Country and Industry | FDI position, flows, and income by country and selected industry; connector-country investment validation and Scenario C / `hgamma` support | Batch 6 archives both `U.S. direct investment abroad` and `foreign direct investment in the U.S.` country-by-industry files under `data/raw/bea_fdi/direct_investment_country_industry/` and writes `data/interim/fdi/bea_direct_investment_country_industry.parquet`. Source: https://www.bea.gov/data/intl-trade-investment/direct-investment-country-and-industry |
| Comtrade or BACI | Bilateral trade rerouting and connector ranking | Source choice pending data-access comparison. |
| Reference replication data | Conceptual model interface only | Kept under `reference/`, not copied here. |

## Reproducible BEA MOFA Check

The BEA U.S. MNE MOFA country-industry archive and Mexico suppression audit can be regenerated with:

```powershell
python -m pip install -r code\data_build\requirements-bea-mne.txt
python code\data_build\download_extract_bea_mne_mofas.py --overwrite
```

The script downloads the five BEA country-industry XLS tables, writes raw files to `data/raw/bea_usdia_mofas_2025-08/`, writes the ignored machine-readable audit CSV to `data/interim/`, and refreshes the tracked Markdown manifest and audit summary in `data/`.

## Batch 6: BEA Direct Investment Country-Industry Panel

The BEA direct-investment country-industry panel can be regenerated with:

```powershell
python -m pip install -r code\data_build\requirements-bea-fdi.txt
python code\data_build\build_bea_direct_investment_country_industry.py --overwrite
```

This build downloads BEA static XLSX files from the `U.S. direct investment abroad` and `foreign direct investment in the U.S.` pages, writes raw files to `data/raw/bea_fdi/direct_investment_country_industry/`, writes the raw-file manifest to `data/raw/bea_fdi/metadata/bea_direct_investment_country_industry_manifest.json`, and writes the ignored cleaned panel to `data/interim/fdi/bea_direct_investment_country_industry.parquet`.

Minimum panel fields:

- `year`
- `direction`
- `country`
- `industry`
- `position`
- `flows`
- `income`
- `source_file`

Direction convention: `us_direct_investment_abroad` reports U.S. outward direct investment; `foreign_direct_investment_in_us` reports foreign direct investment into the United States. BEA financial-transaction signs differ by direction: U.S. outward flows are outflows positive / inflows negative, while FDIUS flows are inflows positive / outflows negative. BEA `(D)` cells are missing, not zero; BEA `(*)` cells are stored as `0.0` with a small-value flag.

Current coverage limit: the default output is restricted to 2020-2024 because `position`, `flows`, and `income` are jointly available for both directions. BEA also lists 2025 position files, but matching 2025 annual flows and income are not included in this batch. If the project later needs a longer window or earlier historical years, continue with a separate BEA download and validation batch before merging those observations into the analysis panel.

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
