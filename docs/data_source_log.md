# Data Source Log

This file records data-source decisions, access status, and download actions. Do not use it to store raw data.

## Current Assessment

| Source | Access status | Coverage / latest usable vintage | Key limitation | Project use |
|---|---|---|---|---|
| [OECD ICIO, including Extended ICIO](https://www.oecd.org/en/data/datasets/inter-country-input-output-tables.html) | Free public download | 2025 edition, second revision released in mid-January 2026; regular ICIO covers 80 economies plus rest of world; Extended ICIO separately identifies China and Mexico ownership/firm-type layers; latest years cover through 2022 | Does not cover the 2023 nearshoring wave | Baseline IO, gross output, value added, final demand, intermediate linkages, and the first data layer for Mexico/China foreign-owned versus domestic-owned production splits |
| [OECD Analytical AMNE / MNE-GVC](https://www.oecd.org/en/data/datasets/multinational-enterprises-and-global-value-chains.html) | Free public download | 2024 release, consistent with the OECD ICIO release published in February 2024; ownership-split output, value added, trade, and ICIO tables cover 2000-2020 | Major structural gap: no 2021-2023 nearshoring period | Core source for separating multinational-production ownership shares from IO tables and disciplining the numerator of `hgamma`; must be bridged after 2020 with BEA, Mexico FDI, and fDi Markets evidence |
| [BEA U.S. MNE MOFA country-industry tables](https://www.bea.gov/data/intl-trade-investment/activities-us-multinational-enterprises-mnes) | Free public download / BEA Interactive Data | Current release includes 2023 preliminary and 2022 revised U.S. MNE activity statistics; local archive downloaded from 2025-08 tables | Some country-industry cells may be suppressed as `(D)`; selected detailed annual tables were discontinued or affected from the 2023 preliminary-data cycle | U.S.-MNE production-side bridge for Mexico after OECD Analytical AMNE ends in 2020; local audit verifies no suppression for Mexico x Transportation equipment in assets, employment, value added, PPE expenditures, or sales for 2020-2022 |
| [BEA Direct Investment by Country and Industry](https://www.bea.gov/data/intl-trade-investment/direct-investment-country-and-industry) | Free public download | Batch 6 uses BEA static country-by-industry files for 2020-2024, covering `U.S. direct investment abroad` and `foreign direct investment in the U.S.` with position, financial transactions, and income | FDI position and flows are investment-account measures, not affiliate output or value added; some country-industry cells may be suppressed as `(D)`; 2025 position files are listed but matching 2025 flows and income are not included in this batch | Connector-country investment validation, North America extension checks for Mexico/Canada, and Scenario C / `hgamma` support when interpreted separately from BEA MNE affiliate production activity |
| [fDi Markets](https://www.fdimarkets.com/) | Commercial subscription database; user has confirmed access | Real-time greenfield FDI project database since 2003; project-level parent firm, source country, destination, sector, activity, capital expenditure, jobs, and announcement source | Announcement data are not the same as realized production, and access/export provenance must be documented | Main project-level source for the model-external extensive-margin evidence section: new plant/project announcements, sector targeting, source-country composition, and expected employment/capex in Mexico and other connector economies |
| [BACI](https://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=37) | Free public download | CEPII HS6 bilateral annual trade data; latest listed update is version 202601 with data through 2024 | Annual HS6 trade only; no ownership, plant, or firm information; requires HS-to-sector concordance | Preferred product-level trade source for connector rankings, rerouting measures, Section 301 exposure, and industry-level trade-cost moments |
| Mexico Secretaria de Economia / DataMexico FDI data | Free public government data | User-provided target coverage: quarterly FDI flows from 1999 through 2024 Q4, by source country and industry | Flow data, not activity stock or realized output; mixes reinvested earnings, new equity, and intercompany debt; not project-level greenfield data | Trend validation for 2021-2024 nearshoring after Analytical AMNE ends; complements BEA MNE activity and fDi Markets project announcements |
| Section 301 tariff data: USTR lists, USITC HTS, and PIIE/Bown tariff files | Free public data | 2018-2019 tariff lists and later modifications/exclusions can be mapped at HS8 and aggregated to project sectors | Need to track exclusions, reinstatements, effective dates, and HS concordance across versions | Cleanest policy-shock layer; used to construct product-level tariff exposure and sector-level effective tariff shocks for `htau` scenarios |
| USITC USMCA automotive rules-of-origin reports | Free public statutory reports | Biennial reports required under USMCA implementation legislation; user-supplied target statistic: non-preference light-vehicle imports from Canada/Mexico rose from 0.5% in 2019 to 8.2% in 2023 | Automotive-sector specific; exact table and definition must be verified before citation | Direct evidence for the auto-sector distinction between genuine production integration and rerouting/light assembly that does not satisfy USMCA preference rules |

## Current Decision

The data strategy is now viable for a first structural version plus a separate extensive-margin evidence section.

- `hgamma` should be disciplined by OECD Analytical AMNE through 2020, then bridged with BEA U.S. MNE activity, BEA direct-investment country-industry data, Mexico FDI flows, and fDi Markets project-level greenfield announcements.
- fDi Markets is available and should be treated as the primary source for new-project/extensive-margin evidence, not as a speculative optional source.
- The Du-Wang counterfactual should still be described as intensive-margin welfare accounting. fDi Markets evidence can validate the nearshoring narrative and bound `hgamma` scenarios, but it is not an endogenous prediction of the Du-Wang model.

## Immediate Data Checks

1. Export fDi Markets project-level records for Mexico and comparison connector economies, 2017-2024, restricted to manufacturing and the priority sectors: transportation equipment/autos, electronics, machinery, medical devices, and related components.
2. In BEA Interactive Data, verify whether Mexico x electronics/computers and Mexico x medical devices cells are suppressed for 2020-2023. Mexico x transportation equipment has already passed the 2020-2022 suppression check.
3. Download OECD ICIO Extended and OECD Analytical AMNE/MNE-GVC files, preserving the release version and readme files.
4. Download BACI version 202601 and build the HS6-to-model-sector concordance.
5. Download USTR/USITC Section 301 tariff lists and create a product-year tariff panel with exclusions/effective dates.
6. Download Mexico Secretaria de Economia / DataMexico FDI series and verify the user-provided 2024 aggregate/source-country numbers before citing them.
7. Download the relevant USITC USMCA automotive rules-of-origin report and verify the 0.5% to 8.2% statistic before using it in the manuscript.

## Existing Local Artifacts

| Source | Local path | Status |
|---|---|---|
| BEA U.S. MNE MOFA country-industry tables | Raw files: `data/raw/bea_usdia_mofas_2025-08/` (ignored); manifest: `data/bea_usdia_mofas_2025_08_archive_manifest.md`; audit: `data/bea_mne_mofas_mexico_suppression_audit_2020_2022.md`; script: `code/data_build/download_extract_bea_mne_mofas.py` | Downloaded and checked for Mexico x Transportation equipment, 2020-2022 |
| BEA Direct Investment by Country and Industry | Batch 6 raw files: `data/raw/bea_fdi/direct_investment_country_industry/` (ignored); Batch 6 manifest: `data/raw/bea_fdi/metadata/bea_direct_investment_country_industry_manifest.json` (ignored); Batch 6 output: `data/interim/fdi/bea_direct_investment_country_industry.parquet` (ignored); Batch 6 script: `code/data_build/build_bea_direct_investment_country_industry.py` | Batch 6 country-industry panel covers 2020-2024 for both direct-investment directions with position, flows, income, source-file provenance, and BEA suppression flags. If the project later needs earlier years or a longer window, add them as a separate download and validation batch. |

## Download Rule

For every downloaded batch, add a new row rather than overwriting an existing one. If a source updates, record the new vintage separately.
