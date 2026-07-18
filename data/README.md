# Data Directory

This directory documents the data pipeline. Large raw and generated data files are ignored by git.

## Data Sources

| Source | Intended use | Status |
|---|---|---|
| OECD ICIO | Country-sector IO structure, final demand, value added, gross output | Regular and Extended 2025-edition raw archives are complete through 2022 under `data/raw/oecd_icio/`. Source: https://www.oecd.org/en/data/datasets/inter-country-input-output-tables.html |
| OECD AMNE | Foreign affiliate activity and Scenario B MP-intensive reallocation | Raw Analytical AMNE files are archived under `data/raw/oecd_amne/`; the affiliate-activity and MP-share outputs are under `data/interim/mne/`. Source: https://www.oecd.org/en/data/datasets/activity-of-multinational-enterprises.html |
| BEA U.S. MNE MOFA country-industry tables | U.S. MNE affiliate activity by host country and affiliate industry; Scenario B bridge and Scenario C support when combined with broader production evidence | Archived locally under `data/raw/bea_usdia_mofas_2025-08/` (ignored by git). Mexico x Transportation equipment verified for 2020-2022; see `data/bea_mne_mexico_transportation_equipment_2020_2022.md`, `data/bea_usdia_mofas_2025_08_archive_manifest.md`, and `data/bea_mne_mofas_mexico_suppression_audit_2020_2022.md`. Source: https://www.bea.gov/international/di1usdop |
| BEA Direct Investment by Country and Industry | FDI position, flows, and income by country and selected industry; connector-country investment validation and Scenario C / `hgamma` support | Batch 6 archives both `U.S. direct investment abroad` and `foreign direct investment in the U.S.` country-by-industry files under `data/raw/bea_fdi/direct_investment_country_industry/` and writes `data/interim/fdi/bea_direct_investment_country_industry.parquet`. Source: https://www.bea.gov/data/intl-trade-investment/direct-investment-country-and-industry |
| fDi Markets | Model-external extensive-margin evidence and Scenario C upper-bound discipline | Explicitly excluded from the current batch by user instruction; no download or processing was attempted. |
| Mexico FDI data | Post-2020 FDI-flow validation and Scenario C support | Official Secretaría de Economía data are archived and normalized: national coverage is 1999Q1-2024Q4 and detailed cross-tables cover 2006Q1-2024Q4. See `data/mexico_fdi_usage_note.md`. |
| BACI | Bilateral trade rerouting, connector ranking, and the Section 301 denominator | The main project HS2012 panel is retained; a separate CEPII BACI HS2017 V202601 archive and 2017 U.S.-import denominator were added for Section 301. |
| USTR Section 301 | Gross statutory China tariff exposure and `htau` discipline | Official base-list HTS10 panel and 2014-2024 HS2017 exposure are built; exact September 2024 modern-HTS increases are stored separately. See `data/section301_usage_note.md`. |
| Reference replication data | Conceptual model interface only | Kept under `reference/`, not copied here. |

## Reproducible BEA MOFA Check

The BEA U.S. MNE MOFA country-industry archive and Mexico suppression audit can be regenerated with:

```powershell
python -m pip install -r code\data_build\requirements-bea-mne.txt
python code\data_build\download_extract_bea_mne_mofas.py --overwrite
```

The script downloads the five BEA country-industry XLS tables, writes raw files to `data/raw/bea_usdia_mofas_2025-08/`, writes the ignored machine-readable audit CSV to `data/interim/`, and refreshes the tracked Markdown manifest and audit summary in `data/`.

## Batch 5: BEA U.S. MNE Affiliate Country-Industry Panel

The full BEA U.S. MNE majority-owned foreign affiliate panel can be regenerated with:

```powershell
python -m pip install -r code\data_build\requirements-bea-mne.txt
python code\data_build\build_bea_us_mne_affiliate_country_industry.py --overwrite
```

This build downloads BEA annual comprehensive tables for 2017-2023 from the Activities of U.S. MNEs pages, writes raw XLS files to `data/raw/bea_mne/activities_us_mnes/`, writes the raw-file manifest to `data/raw/bea_mne/metadata/bea_us_mne_activities_manifest.json`, and writes the ignored cleaned panel to `data/interim/mne/bea_us_mne_affiliate_country_industry.parquet`.

Minimum panel fields:

- `year`
- `affiliate_country`
- `industry`
- `employment`
- `sales`
- `value_added`
- `capital_expenditures`
- `goods_exports_to_us`
- `goods_imports_from_us`

Direction convention: `goods_exports_to_us` comes from BEA Table II.H 11, U.S. imports of goods shipped by affiliates. `goods_imports_from_us` comes from BEA Table II.H 3, U.S. exports of goods shipped to affiliates. BEA `(D)` cells and employment size-range codes `A/F/G/H/I/J/K/L/M` are missing, not zero; BEA `(*)` cells are stored as `0.0` with a small-value flag.

Current coverage limit: the full six-field panel is built for 2017-2023. If the project later needs years before 2017, download and validate those older BEA annual files as a separate extension rather than mixing them into this completed Batch 5 build.

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

## Section 301 Policy Data

Regenerate the official base-list code table, the dedicated BACI HS2017 denominator, the main exposure outputs, and the separate 2024 review table with:

```powershell
python code\data_build\build_ustr_section301_notice_codes.py --project-root . --overwrite
python code\data_build\build_baci_hs17_us_imports_2017.py --project-root . --download --overwrite
python code\data_build\build_ustr_section301.py --project-root . --process-only --overwrite
python code\data_build\build_ustr_section301_2024_review_codes.py --project-root . --overwrite
```

The main output is a gross statutory exposure measure. It applies the four initial actions and the List 3/List 4A rate changes, but it does not claim to reconstruct duties collected after product exclusions. The September 2024 increases use modern HTS codes and remain in a separate exact-code table. Full sources, hashes, row counts, formula definitions, and limitations are in `data/section301_usage_note.md`.

## Mexico Official FDI

Regenerate the official Secretaría de Economía archive and nine normalized outputs with:

```powershell
python code\data_build\download_build_mexico_fdi.py --project-root . --overwrite
```

The national quarterly total and investment-type panels cover 1999Q1-2024Q4. Source-country and sector annual panels cover 1999-2024, while state/country/sector/type quarterly cross-tables cover 2006Q1-2024Q4. Official `C` cells remain null with `confidential_flag=true`; `Total general` rows are flagged to prevent double counting. See `data/mexico_fdi_usage_note.md` for fields, coverage, reconciliation gaps, and interpretation.

`fDi Markets` is not part of this batch.

## Scenario-Mapping Rule

Every model-facing data extract should state whether it supports:

- Scenario A: trade-only connector lower bound;
- Scenario B: incumbent MP-intensive baseline;
- Scenario C: total MP-adjustment upper-bound proxy.

Do not label fDi Markets or FDI-flow evidence as a structural entry equation. These sources can discipline Scenario C, but the Du-Wang model does not endogenize affiliate or plant entry.

## Non-Negotiable Rule

Do not overwrite raw data in place. If a source is updated, save it under a dated or versioned folder and update the metadata note.
