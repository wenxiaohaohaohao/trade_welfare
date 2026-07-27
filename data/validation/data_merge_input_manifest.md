# Data Merge Input Manifest

- Generated at UTC: `2026-07-19T13:22:01.869268+00:00`
- Git branch: `data-processing-variables`
- Git commit: `2df0a0628343c9abca6b3e26d893db351ec22b94`
- Input count: `8`
- Total frozen size: `1,512,110,467` bytes
- Validation status: **PASS**

## Frozen inputs

| Input | Rows | Years | Size bytes | SHA256 |
|---|---:|---|---:|---|
| `baci_hs6_panel` | 123,313,077 | 2014-2024 (11 years) | 1,179,013,952 | `23ab6734c70503b3a0a7c6c7ec015cc4bf75ee334242dce6cf43ec68cfef46a4` |
| `us_census_hs6_monthly` | 5,017,364 | 2014-2024 (11 years) | 263,763,588 | `65746c64f8e72a215fa55506f9d1eded5b13bf3e035fbb830a8407237299a205` |
| `section301_hs6_exposure` | 55,308 | 2014-2024 (11 years) | 348,420 | `22863ef3e034bc560d40fcbbc0945678ccd2e07bb3829ba630a36f4dfe6ca299` |
| `oecd_icio_output_va_fd` | 12,150 | 2017, 2018, 2022 | 1,096,583 | `4c3c5b1a11d344e7b13b727a7036230d053312c137871525cb1fb412a4679643` |
| `oecd_amne_affiliate_activity` | 1,260,053 | 2008-2023 (16 years) | 65,440,219 | `ae5f859573e95773274928d0f27a90fe974fca2bd95f22fa78a849d8a2d8f856` |
| `bea_us_mne_affiliate_country_industry` | 8,256 | 2017-2023 (7 years) | 314,517 | `ab2e064459cc9dac8c13eebd7e399e91047133a93e8f35b9821520add7f219e8` |
| `bea_direct_investment_country_industry` | 11,610 | 2020-2024 (5 years) | 248,802 | `a80c567f8d2e966a5f56b1d64f3c3e0005734d5ea9840f6c5d1c43246f01b0ba` |
| `mexico_fdi_country_sector_quarterly` | 596,366 | 2006-2024 (19 years) | 1,884,386 | `fce725b009dc96ae825bd3fed2d2b02ba5cc13501c5a6657bcdf3a09a022261a` |

## Interfaces

### `baci_hs6_panel`

- Path: `data/interim/trade/baci_hs6_panel.parquet`
- Source/release: CEPII BACI — HS2012 Version 202601
- Natural grain: `exporter-importer-HS6-year`
- Natural key: `year, exporter_iso3, importer_iso3, hs6`
- Builder: `code/data_build/build_baci_batch1.py`
- Build summary: `data/interim/trade/baci_batch1_build_summary.json`
- Schema: `year: int16, exporter_iso3: string, importer_iso3: string, hs6: string, trade_value_usd: double, quantity: double, unit: string, source_file: string`

### `us_census_hs6_monthly`

- Path: `data/interim/trade/us_imports_hs6_monthly.parquet`
- Source/release: U.S. Census International Trade API — validated configured-origin batch
- Natural grain: `origin-HS6-month`
- Natural key: `year, month, origin_iso3, hs6`
- Builder: `code/data_build/download_us_census_imports.py`
- Build summary: `data/interim/trade/us_census_imports_build_summary.json`
- Schema: `year: int16, month: int8, origin_iso3: string, origin_census_code: string, origin_name: string, hts10: string, hs6: string, import_value_usd: double, quantity: double, quantity_unit: string, customs_value: double, duties: double, dutiable_value_usd: double, commodity_description: string, source_file: string`

### `section301_hs6_exposure`

- Path: `data/interim/policy/section301_hs6_exposure.parquet`
- Source/release: USTR Section 301 public notices with BACI/Census weights — validated base-list exposure batch
- Natural grain: `HS2017 product-year`
- Natural key: `hs6, year`
- Builder: `code/data_build/build_ustr_section301.py`
- Build summary: `data/interim/policy/section301_build_summary.json`
- Schema: `hs6: string, year: int16, origin_iso3: string, destination_iso3: string, tariffed_product: bool, list_id: string, tariff_rate: double, china_import_share_2017: double, tariff_exposure: double`

### `oecd_icio_output_va_fd`

- Path: `data/interim/production/oecd_icio_output_va_fd.parquet`
- Source/release: OECD Inter-Country Input-Output tables — ICIO 2025 edition regular tables
- Natural grain: `country-OECD-sector-year`
- Natural key: `year, country_iso3, sector_oecd`
- Builder: `code/data_build/build_oecd_icio_baseline.py`
- Build summary: `data/interim/production/oecd_icio_build_summary.json`
- Schema: `year: int16, country_iso3: string, sector_oecd: string, gross_output: double, gross_output_sales: double, value_added: double, final_demand: double, intermediate_inputs: double, taxes_less_subsidies: double, exports: double, imports: double, intermediate_sales: double, domestic_absorption: double, source_file: string`

### `oecd_amne_affiliate_activity`

- Path: `data/interim/mne/oecd_amne_affiliate_activity.parquet`
- Source/release: OECD Analytical AMNE — 2026 release
- Natural grain: `parent-host-OECD-sector-year`
- Natural key: `year, host_country_iso3, parent_country_iso3, sector_oecd`
- Builder: `code/data_build/build_oecd_amne.py`
- Build summary: `data/interim/mne/oecd_amne_build_summary.json`
- Schema: `year: int16, host_country_iso3: string, parent_country_iso3: string, sector_oecd: string, affiliate_output: double, affiliate_value_added: double, affiliate_employment: double, affiliate_exports: double, affiliate_imports: double, ownership_type: string, foreign_affiliate_output_total: double, gross_output: double, parent_affiliate_output_share: double, allocation_method: string, source_file: string`

### `bea_us_mne_affiliate_country_industry`

- Path: `data/interim/mne/bea_us_mne_affiliate_country_industry.parquet`
- Source/release: BEA Activities of U.S. Multinational Enterprises — 2017-2023 comprehensive country-industry batch
- Natural grain: `affiliate-country-industry-year`
- Natural key: `year, affiliate_country, industry`
- Builder: `code/data_build/build_bea_us_mne_affiliate_country_industry.py`
- Build summary: `data/interim/mne/bea_us_mne_affiliate_country_industry_build_summary.json`
- Schema: `year: int16, affiliate_country: string, industry: string, employment: double, sales: double, value_added: double, capital_expenditures: double, goods_exports_to_us: double, goods_imports_from_us: double, bea_area_type: string, bea_parent_area: string, capital_expenditures_raw_code: string, capital_expenditures_suppressed: bool, capital_expenditures_small_value: bool, capital_expenditures_source_file: string, sales_raw_code: string, sales_suppressed: bool, sales_small_value: bool, sales_source_file: string, value_added_raw_code: string, value_added_suppressed: bool, value_added_small_value: bool, value_added_source_file: string, employment_raw_code: string, employment_suppressed: bool, employment_small_value: bool, employment_source_file: string, goods_imports_from_us_raw_code: string, goods_imports_from_us_suppressed: bool, goods_imports_from_us_small_value: bool, goods_imports_from_us_source_file: string, goods_exports_to_us_raw_code: string, goods_exports_to_us_suppressed: bool, goods_exports_to_us_small_value: bool, goods_exports_to_us_source_file: string, release_vintage: string, download_date: string, source_page: string`

### `bea_direct_investment_country_industry`

- Path: `data/interim/fdi/bea_direct_investment_country_industry.parquet`
- Source/release: BEA Direct Investment by Country and Industry — 2020-2024 two-direction batch
- Natural grain: `direction-country-industry-year`
- Natural key: `year, direction, country, industry`
- Builder: `code/data_build/build_bea_direct_investment_country_industry.py`
- Build summary: `data/interim/fdi/bea_direct_investment_country_industry_build_summary.json`
- Schema: `year: int16, direction: string, country: string, industry: string, position: double, flows: double, income: double, source_file: string, bea_area_type: string, bea_parent_area: string, flows_raw_code: string, flows_suppressed: bool, flows_small_value: bool, flows_source_file: string, flows_source_url: string, income_raw_code: string, income_suppressed: bool, income_small_value: bool, income_source_file: string, income_source_url: string, position_raw_code: string, position_suppressed: bool, position_small_value: bool, position_source_file: string, position_source_url: string, release_vintage: string, download_date: string, source_page: string, unit: string`

### `mexico_fdi_country_sector_quarterly`

- Path: `data/interim/fdi/mexico_fdi_country_sector_quarterly.parquet`
- Source/release: Mexico Secretaria de Economia official FDI tables — national release through 2024Q4; country-sector quarterly input observed through 2024Q2
- Natural grain: `parent-country-SCIAN-sector-quarter`
- Natural key: `year, quarter, parent_country_name, sector_level, sector_code`
- Builder: `code/data_build/download_build_mexico_fdi.py`
- Build summary: `data/interim/fdi/mexico_fdi_build_summary.json`
- Schema: `year: int16, quarter: int8, period: large_string, date: timestamp[us], parent_country_iso3: large_string, parent_country_name: large_string, parent_country_total_flag: bool, parent_country_residual_flag: bool, sector_level: large_string, sector_code: large_string, sector_name: large_string, fdi_million_usd: double, fdi_usd: double, confidential_flag: bool, source_file: large_string`

## Scope of this validation

This M0.3 manifest verifies file identity, row counts, exact year coverage, schema, natural-key field presence, builder presence, and build-summary presence. It does not yet verify natural-key uniqueness, value ranges, missingness, aggregate geography rows, suppression, confidentiality, or units; those checks belong to M0.4.
