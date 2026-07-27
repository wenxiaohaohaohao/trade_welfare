# Data Merge Input Quality Audit

- Generated at UTC: `2026-07-19T08:22:02.899322+00:00`
- Input count: `8`
- Failure count: `0`
- Validation status: **PASS**

## Summary

| Input | Duplicate rows | Key-null cells | Expected limitations | Status |
|---|---:|---:|---:|---|
| `baci_hs6_panel` | 0 | 0 | 2 | `PASS_WITH_EXPECTED_LIMITATIONS` |
| `us_census_hs6_monthly` | 0 | 0 | 2 | `PASS_WITH_EXPECTED_LIMITATIONS` |
| `section301_hs6_exposure` | 0 | 0 | 1 | `PASS_WITH_EXPECTED_LIMITATIONS` |
| `oecd_icio_output_va_fd` | 0 | 0 | 3 | `PASS_WITH_EXPECTED_LIMITATIONS` |
| `oecd_amne_affiliate_activity` | 0 | 0 | 2 | `PASS_WITH_EXPECTED_LIMITATIONS` |
| `bea_us_mne_affiliate_country_industry` | 0 | 0 | 8 | `PASS_WITH_EXPECTED_LIMITATIONS` |
| `bea_direct_investment_country_industry` | 0 | 0 | 6 | `PASS_WITH_EXPECTED_LIMITATIONS` |
| `mexico_fdi_country_sector_quarterly` | 0 | 0 | 5 | `PASS_WITH_EXPECTED_LIMITATIONS` |

## `baci_hs6_panel`

- Path: `data/interim/trade/baci_hs6_panel.parquet`
- Natural grain: `exporter-importer-HS6-year`
- Natural key: `year, exporter_iso3, importer_iso3, hs6`
- Duplicate rows: `0`
- Key-null rows by field: `{"year": 0, "exporter_iso3": 0, "importer_iso3": 0, "hs6": 0}`
- Status: **PASS_WITH_EXPECTED_LIMITATIONS**

### Numeric fields

| Field | Null | Negative | Zero | Min | Max |
|---|---:|---:|---:|---:|---:|
| `trade_value_usd` | 0 | 0 | 0 | 1.0 | 117673227677.0 |
| `quantity` | 3,328,696 | 0 | 0 | 0.001 | 820192189.44 |

### Expected limitations retained

- BACI quantity is missing in 3,328,696 rows and is not required for value-based measures
- BACI unit describes quantity; trade_value_usd is already expressed in USD

### Category counts

- `unit`: `{"metric_tons": 123313077}`

### Unit contract

- `trade_value_usd`: current USD; BACI v is multiplied by 1,000 in the builder
- `quantity`: metric tons when available; the unit column applies to quantity

## `us_census_hs6_monthly`

- Path: `data/interim/trade/us_imports_hs6_monthly.parquet`
- Natural grain: `origin-HS6-month`
- Natural key: `year, month, origin_iso3, hs6`
- Duplicate rows: `0`
- Key-null rows by field: `{"year": 0, "month": 0, "origin_iso3": 0, "hs6": 0}`
- Status: **PASS_WITH_EXPECTED_LIMITATIONS**

### Numeric fields

| Field | Null | Negative | Zero | Min | Max |
|---|---:|---:|---:|---:|---:|
| `import_value_usd` | 0 | 0 | 1,188,272 | 0.0 | 11290234421.0 |
| `quantity` | 0 | 0 | 5,017,364 | 0.0 | 0.0 |
| `customs_value` | 0 | 0 | 1,182,947 | 0.0 | 11230685361.0 |
| `duties` | 0 | 0 | 2,891,700 | 0.0 | 252652722.0 |
| `dutiable_value_usd` | 0 | 0 | 2,875,112 | 0.0 | 9694905499.0 |

### Expected limitations retained

- Census scope is the configured 15 origins, not an all-origin U.S. import denominator
- Census HS6 quantity is unavailable in this output: all values are 0 and quantity_unit is '-'

### Category counts

- `origin_iso3`: `{"CAN": 537784, "CHN": 569839, "IDN": 217546, "IND": 439954, "JPN": 463000, "KOR": 393456, "MAR": 81876, "MEX": 452506, "MYS": 212479, "PHL": 168004, "POL": 263603, "THA": 286685, "TUR": 290408, "TWN": 378341, "VNM": 261883}`
- `month`: `{"1": 316534, "10": 458518, "11": 464818, "12": 470430, "2": 355848, "3": 381932, "4": 399740, "5": 413749, "6": 425377, "7": 435305, "8": 443834, "9": 451279}`
- `quantity_unit`: `{"-": 5017364}`

### Unit contract

- `import_value_usd`: current USD
- `customs_value`: current USD
- `duties`: current USD
- `dutiable_value_usd`: current USD
- `quantity`: unavailable in the current HS6 output; stored as 0 with quantity_unit '-'

## `section301_hs6_exposure`

- Path: `data/interim/policy/section301_hs6_exposure.parquet`
- Natural grain: `HS2017 product-year`
- Natural key: `hs6, year`
- Duplicate rows: `0`
- Key-null rows by field: `{"hs6": 0, "year": 0}`
- Status: **PASS_WITH_EXPECTED_LIMITATIONS**

### Numeric fields

| Field | Null | Negative | Zero | Min | Max |
|---|---:|---:|---:|---:|---:|
| `tariff_rate` | 0 | 0 | 21,556 | 0.0 | 0.25 |
| `china_import_share_2017` | 0 | 0 | 7,084 | 0.0 | 1.0 |
| `tariff_exposure` | 0 | 0 | 25,821 | 0.0 | 0.25 |

### Expected limitations retained

- Exposure is gross statutory exposure; historical product exclusions are not applied

### Category counts

- `origin_iso3`: `{"CHN": 55308}`
- `destination_iso3`: `{"USA": 55308}`
- `tariffed_product`: `{"False": 21412, "True": 33896}`
- `list_id`: `{"": 21412, "list1": 3321, "list1;list2": 176, "list1;list2;list3": 17, "list1;list2;list3;list4a": 18, "list1;list2;list4a": 6, "list1;list3": 268, "list1;list3;list4a": 54, "list1;list4a": 60, "list2": 1071, "list2;list3": 87, "list2;list3;list4a": 18, "list3": 20304, "list3;list4a": 696, "list4a": 7800}`

### Unit contract

- `tariff_rate`: fraction in [0, 1]
- `china_import_share_2017`: fraction in [0, 1]
- `tariff_exposure`: tariff_rate multiplied by China import share; fraction

## `oecd_icio_output_va_fd`

- Path: `data/interim/production/oecd_icio_output_va_fd.parquet`
- Natural grain: `country-OECD-sector-year`
- Natural key: `year, country_iso3, sector_oecd`
- Duplicate rows: `0`
- Key-null rows by field: `{"year": 0, "country_iso3": 0, "sector_oecd": 0}`
- Status: **PASS_WITH_EXPECTED_LIMITATIONS**

### Numeric fields

| Field | Null | Negative | Zero | Min | Max |
|---|---:|---:|---:|---:|---:|
| `gross_output` | 0 | 0 | 154 | 0.0 | 4883363.6277 |
| `gross_output_sales` | 0 | 0 | 154 | 0.0 | 4883363.6277 |
| `value_added` | 0 | 8 | 154 | -33.6241 | 3031953.1294 |
| `final_demand` | 0 | 0 | 154 | 0.0 | 4407430.373299994 |
| `intermediate_inputs` | 0 | 0 | 367 | 0.0 | 3474337.0554 |
| `taxes_less_subsidies` | 0 | 365 | 378 | -15622.7611 | 109673.0937 |
| `exports` | 0 | 0 | 375 | 0.0 | 656018.8691 |
| `imports` | 0 | 0 | 243 | 0.0 | 430894.9053 |
| `intermediate_sales` | 0 | 0 | 370 | 0.0 | 2618565.775000001 |
| `domestic_absorption` | 0 | 0 | 154 | 0.0 | 4684114.149600001 |

### Expected limitations retained

- ICIO value_added contains 8 negative accounting cells
- ICIO taxes_less_subsidies contains 365 negative accounting cells
- ICIO is observed only in 2017, 2018, and 2022; missing years will not be imputed

### Category counts

- `country_iso3`: `{"AGO": 150, "ARE": 150, "ARG": 150, "AUS": 150, "AUT": 150, "BEL": 150, "BGD": 150, "BGR": 150, "BLR": 150, "BRA": 150, "BRN": 150, "CAN": 150, "CHE": 150, "CHL": 150, "CHN": 150, "CIV": 150, "CMR": 150, "COD": 150, "COL": 150, "CRI": 150, "CYP": 150, "CZE": 150, "DEU": 150, "DNK": 150, "EGY": 150, "ESP": 150, "EST": 150, "FIN": 150, "FRA": 150, "GBR": 150, "GRC": 150, "HKG": 150, "HRV": 150, "HUN": 150, "IDN": 150, "IND": 150, "IRL": 150, "ISL": 150, "ISR": 150, "ITA": 150, "JOR": 150, "JPN": 150, "KAZ": 150, "KHM": 150, "KOR": 150, "LAO": 150, "LTU": 150, "LUX": 150, "LVA": 150, "MAR": 150, "MEX": 150, "MLT": 150, "MMR": 150, "MYS": 150, "NGA": 150, "NLD": 150, "NOR": 150, "NZL": 150, "PAK": 150, "PER": 150, "PHL": 150, "POL": 150, "PRT": 150, "ROU": 150, "ROW": 150, "RUS": 150, "SAU": 150, "SEN": 150, "SGP": 150, "STP": 150, "SVK": 150, "SVN": 150, "SWE": 150, "THA": 150, "TUN": 150, "TUR": 150, "TWN": 150, "UKR": 150, "USA": 150, "VNM": 150, "ZAF": 150}`
- `sector_oecd`: `{"A01": 243, "A02": 243, "A03": 243, "B05": 243, "B06": 243, "B07": 243, "B08": 243, "B09": 243, "C10T12": 243, "C13T15": 243, "C16": 243, "C17_18": 243, "C19": 243, "C20": 243, "C21": 243, "C22": 243, "C23": 243, "C24A": 243, "C24B": 243, "C25": 243, "C26": 243, "C27": 243, "C28": 243, "C29": 243, "C301": 243, "C302T309": 243, "C31T33": 243, "D": 243, "E": 243, "F": 243, "G": 243, "H49": 243, "H50": 243, "H51": 243, "H52": 243, "H53": 243, "I": 243, "J58T60": 243, "J61": 243, "J62_63": 243, "K": 243, "L": 243, "M": 243, "N": 243, "O": 243, "P": 243, "Q": 243, "R": 243, "S": 243, "T": 243}`

### Unit contract

- `value_fields`: current million USD

## `oecd_amne_affiliate_activity`

- Path: `data/interim/mne/oecd_amne_affiliate_activity.parquet`
- Natural grain: `parent-host-OECD-sector-year`
- Natural key: `year, host_country_iso3, parent_country_iso3, sector_oecd`
- Duplicate rows: `0`
- Key-null rows by field: `{"year": 0, "host_country_iso3": 0, "parent_country_iso3": 0, "sector_oecd": 0}`
- Status: **PASS_WITH_EXPECTED_LIMITATIONS**

### Numeric fields

| Field | Null | Negative | Zero | Min | Max |
|---|---:|---:|---:|---:|---:|
| `affiliate_output` | 0 | 0 | 0 | 0.0052 | 279943.520547134 |
| `affiliate_value_added` | 0 | 166 | 0 | -163.4721669910283 | 88835.52478434611 |
| `affiliate_employment` | 1,260,053 | 0 | 0 | None | None |
| `affiliate_exports` | 0 | 0 | 1,313 | 0.0 | 150666.2487636182 |
| `affiliate_imports` | 0 | 0 | 463 | 0.0 | 86629.26531903478 |
| `foreign_affiliate_output_total` | 0 | 0 | 0 | 0.0052 | 765865.2263 |
| `gross_output` | 0 | 0 | 0 | 0.0052 | 5218452.6583 |
| `parent_affiliate_output_share` | 0 | 0 | 0 | 1.7548434646601264e-08 | 1.0 |

### Expected limitations retained

- AMNE affiliate_employment is unavailable and null in 1,260,053 rows
- AMNE value added, exports, and imports are allocated to parents; allocation_method is retained

### Category counts

- `host_country_iso3`: `{"AGO": 23485, "ARE": 31681, "ARG": 24722, "AUS": 14967, "AUT": 9989, "BEL": 6537, "BGD": 13576, "BGR": 10901, "BLR": 12073, "BRA": 19901, "BRN": 16984, "CAN": 20565, "CHE": 22570, "CHL": 12479, "CHN": 33071, "CIV": 14376, "CMR": 19946, "COD": 19340, "COL": 27288, "CRI": 5771, "CYP": 2199, "CZE": 14014, "DEU": 17662, "DNK": 8392, "EGY": 24519, "ESP": 10466, "EST": 4726, "FIN": 5721, "FRA": 12530, "GBR": 19022, "GRC": 3630, "HKG": 27526, "HRV": 7993, "HUN": 12234, "IDN": 16441, "IND": 17829, "IRL": 6806, "ISL": 2257, "ISR": 3149, "ITA": 13812, "JOR": 13505, "JPN": 16710, "KAZ": 16440, "KHM": 11795, "KOR": 14092, "LAO": 13572, "LTU": 9293, "LUX": 4188, "LVA": 9157, "MAR": 13403, "MEX": 24955, "MLT": 3623, "MMR": 16934, "MYS": 27551, "NGA": 15377, "NLD": 10609, "NOR": 8767, "NZL": 10039, "PAK": 16013, "PER": 19921, "PHL": 16022, "POL": 11780, "PRT": 9300, "ROU": 18186, "ROW": 45447, "RUS": 21088, "SAU": 24567, "SEN": 7995, "SGP": 29485, "STP": 6886, "SVK": 7058, "SVN": 7591, "SWE": 10366, "THA": 26273, "TUN": 21226, "TUR": 6828, "TWN": 23367, "UKR": 31131, "USA": 23845, "VNM": 23735, "ZAF": 20783}`
- `parent_country_iso3`: `{"AGO": 17685, "ARE": 28280, "ARG": 20014, "AUS": 15563, "AUT": 15154, "BEL": 14581, "BGD": 6678, "BGR": 3110, "BLR": 6391, "BRA": 15971, "BRN": 16088, "CAN": 23471, "CHE": 40608, "CHL": 6802, "CHN": 30505, "CIV": 10834, "CMR": 13146, "COD": 11177, "COL": 17087, "CRI": 4264, "CYP": 5952, "CZE": 3839, "DEU": 32793, "DNK": 22700, "EGY": 25124, "ESP": 15881, "EST": 4580, "FIN": 14002, "FRA": 32591, "GBR": 33303, "GRC": 3217, "HKG": 30814, "HRV": 1781, "HUN": 3351, "IDN": 13368, "IND": 21791, "IRL": 7457, "ISL": 2942, "ISR": 11510, "ITA": 26971, "JOR": 21176, "JPN": 30559, "KAZ": 6709, "KHM": 11694, "KOR": 27806, "LAO": 9938, "LTU": 3635, "LUX": 8193, "LVA": 3373, "MAR": 20112, "MEX": 10058, "MLT": 2872, "MMR": 13117, "MYS": 27136, "NGA": 16057, "NLD": 32374, "NOR": 16810, "NZL": 9432, "PAK": 18412, "PER": 6470, "PHL": 9095, "POL": 7255, "PRT": 6694, "ROU": 2030, "ROW": 43241, "RUS": 19017, "SAU": 25464, "SEN": 1782, "SGP": 30593, "STP": 3459, "SVK": 2677, "SVN": 3866, "SWE": 15763, "THA": 18446, "TUN": 17204, "TUR": 8108, "TWN": 24524, "UKR": 21111, "USA": 37726, "VNM": 16886, "ZAF": 17803}`
- `sector_oecd`: `{"A01T03": 34718, "B05T09": 27019, "C10T12": 31458, "C13T15": 31281, "C16": 32102, "C17T18": 33071, "C19": 24366, "C20": 30926, "C21": 28284, "C22": 32602, "C23": 32551, "C24": 31040, "C25": 34991, "C26": 28997, "C27": 30433, "C28": 31527, "C29": 27921, "C30": 29439, "C31T33": 34616, "D35_E36T39": 28842, "F41T43": 35717, "G45T47": 42128, "H49": 33088, "H50": 30231, "H51": 28763, "H52": 35221, "H53": 28527, "I55T56": 33652, "J58T60": 35483, "J61": 30681, "J62T63": 37764, "K64T66": 34538, "L68": 35744, "M69T75": 41036, "N77T82": 37953, "P85": 29555, "Q86T88": 30941, "R90T93": 31252, "S94T96": 31595}`
- `ownership_type`: `{"F": 1260053}`
- `allocation_method`: `{"allocated_by_parent_affiliate_output_share": 1260053}`

### Unit contract

- `value_fields`: current million USD
- `parent_affiliate_output_share`: fraction in [0, 1]
- `affiliate_employment`: unavailable in the current source

### Unit metadata from build summary

- `coverage.unit`: `"current million USD for value variables; shares are fractions"`

## `bea_us_mne_affiliate_country_industry`

- Path: `data/interim/mne/bea_us_mne_affiliate_country_industry.parquet`
- Natural grain: `affiliate-country-industry-year`
- Natural key: `year, affiliate_country, industry`
- Duplicate rows: `0`
- Key-null rows by field: `{"year": 0, "affiliate_country": 0, "industry": 0}`
- Status: **PASS_WITH_EXPECTED_LIMITATIONS**

### Numeric fields

| Field | Null | Negative | Zero | Min | Max |
|---|---:|---:|---:|---:|---:|
| `employment` | 740 | 0 | 690 | 0.0 | 14381.7 |
| `sales` | 1,344 | 0 | 325 | 0.0 | 8066619.0 |
| `value_added` | 1,290 | 164 | 362 | -7447.0 | 1645556.0 |
| `capital_expenditures` | 1,494 | 0 | 1,011 | 0.0 | 216164.0 |
| `goods_exports_to_us` | 1,996 | 0 | 3,523 | 0.0 | 442880.0 |
| `goods_imports_from_us` | 2,055 | 0 | 2,767 | 0.0 | 377775.0 |

### Expected limitations retained

- capital_expenditures_suppressed->capital_expenditures preserves 1,494 flagged missing cells
- sales_suppressed->sales preserves 1,344 flagged missing cells
- value_added_suppressed->value_added preserves 1,290 flagged missing cells
- employment_suppressed->employment preserves 740 flagged missing cells
- goods_imports_from_us_suppressed->goods_imports_from_us preserves 2,055 flagged missing cells
- goods_exports_to_us_suppressed->goods_exports_to_us preserves 1,996 flagged missing cells
- BEA MNE contains 1,792 aggregate geography rows to exclude downstream
- BEA suppressed and employment size-range cells remain missing, not zero

### Category counts

- `bea_area_type`: `{"aggregate": 1792, "country_or_area": 6464}`
- `industry`: `{"All industries": 516, "Chemicals": 516, "Computers and electronic products": 516, "Electrical equipment, appliances, and components": 516, "Finance and insurance": 516, "Food": 516, "Information": 516, "Machinery": 516, "Manufacturing total": 516, "Mining": 516, "Other industries": 516, "Primary and fabricated metals": 516, "Professional, scientific, and technical services": 516, "Retail trade": 516, "Transportation equipment": 516, "Wholesale trade": 516}`

### Suppression/confidentiality consistency

- `capital_expenditures_suppressed->capital_expenditures`: `{"flagged_missing": 1494, "flagged_nonmissing": 0, "unflagged_missing": 0, "unflagged_nonmissing": 6762}`
- `sales_suppressed->sales`: `{"flagged_missing": 1344, "flagged_nonmissing": 0, "unflagged_missing": 0, "unflagged_nonmissing": 6912}`
- `value_added_suppressed->value_added`: `{"flagged_missing": 1290, "flagged_nonmissing": 0, "unflagged_missing": 0, "unflagged_nonmissing": 6966}`
- `employment_suppressed->employment`: `{"flagged_missing": 740, "flagged_nonmissing": 0, "unflagged_missing": 0, "unflagged_nonmissing": 7516}`
- `goods_imports_from_us_suppressed->goods_imports_from_us`: `{"flagged_missing": 2055, "flagged_nonmissing": 0, "unflagged_missing": 0, "unflagged_nonmissing": 6201}`
- `goods_exports_to_us_suppressed->goods_exports_to_us`: `{"flagged_missing": 1996, "flagged_nonmissing": 0, "unflagged_missing": 0, "unflagged_nonmissing": 6260}`

### Unit contract

- `employment`: thousands of employees
- `other_value_fields`: millions of current dollars

### Unit metadata from build summary

- `coverage.units`: `{"employment": "thousands of employees", "sales": "millions of dollars", "value_added": "millions of dollars", "capital_expenditures": "millions of dollars", "goods_exports_to_us": "millions of dollars", "goods_imports_from_us": "millions of dollars"}`

## `bea_direct_investment_country_industry`

- Path: `data/interim/fdi/bea_direct_investment_country_industry.parquet`
- Natural grain: `direction-country-industry-year`
- Natural key: `year, direction, country, industry`
- Duplicate rows: `0`
- Key-null rows by field: `{"year": 0, "direction": 0, "country": 0, "industry": 0}`
- Status: **PASS_WITH_EXPECTED_LIMITATIONS**

### Numeric fields

| Field | Null | Negative | Zero | Min | Max |
|---|---:|---:|---:|---:|---:|
| `position` | 1,549 | 851 | 610 | -21176.0 | 6697705.0 |
| `flows` | 2,919 | 2,348 | 936 | -56996.0 | 386107.0 |
| `income` | 2,707 | 1,136 | 1,484 | -8128.0 | 601862.0 |

### Expected limitations retained

- flows_suppressed->flows preserves 2,919 flagged missing cells
- income_suppressed->income preserves 2,707 flagged missing cells
- position_suppressed->position preserves 1,549 flagged missing cells
- BEA FDI contains 2,610 aggregate geography rows to exclude downstream
- BEA FDI contains 4,335 negative position/flow/income cells; signs are economically valid and retained
- BEA FDI is a financial-account source, not affiliate output or plant entry

### Category counts

- `direction`: `{"foreign_direct_investment_in_us": 4950, "us_direct_investment_abroad": 6660}`
- `bea_area_type`: `{"aggregate": 2610, "country_or_area": 9000}`
- `industry`: `{"All industries": 645, "Chemicals": 645, "Computers and electronic products": 645, "Depository institutions": 645, "Electrical equipment, appliances, and components": 645, "Finance (except depository institutions) and insurance": 645, "Food": 645, "Holding companies (nonbank)": 370, "Information": 645, "Machinery": 645, "Manufacturing total": 645, "Mining": 370, "Other industries": 645, "Other manufacturing": 645, "Primary and fabricated metals": 645, "Professional, scientific, and technical services": 645, "Real estate and rental and leasing": 275, "Retail trade": 275, "Transportation equipment": 645, "Wholesale trade": 645}`
- `unit`: `{"Millions of dollars": 11610}`

### Suppression/confidentiality consistency

- `flows_suppressed->flows`: `{"flagged_missing": 2919, "flagged_nonmissing": 0, "unflagged_missing": 0, "unflagged_nonmissing": 8691}`
- `income_suppressed->income`: `{"flagged_missing": 2707, "flagged_nonmissing": 0, "unflagged_missing": 0, "unflagged_nonmissing": 8903}`
- `position_suppressed->position`: `{"flagged_missing": 1549, "flagged_nonmissing": 0, "unflagged_missing": 0, "unflagged_nonmissing": 10061}`

### Unit contract

- `position_flows_income`: millions of current dollars

### Unit metadata from build summary

- `coverage.unit`: `"Millions of dollars"`

## `mexico_fdi_country_sector_quarterly`

- Path: `data/interim/fdi/mexico_fdi_country_sector_quarterly.parquet`
- Natural grain: `parent-country-SCIAN-sector-quarter`
- Natural key: `year, quarter, parent_country_name, sector_level, sector_code`
- Duplicate rows: `0`
- Key-null rows by field: `{"year": 0, "quarter": 0, "parent_country_name": 0, "sector_level": 0, "sector_code": 0}`
- Status: **PASS_WITH_EXPECTED_LIMITATIONS**

### Numeric fields

| Field | Null | Negative | Zero | Min | Max |
|---|---:|---:|---:|---:|---:|
| `fdi_million_usd` | 86,123 | 7,152 | 473,609 | -4488.505191000001 | 13255.507123000005 |
| `fdi_usd` | 86,123 | 7,152 | 473,609 | -4488505191.000001 | 13255507123.000006 |

### Expected limitations retained

- confidential_flag->fdi_million_usd preserves 86,123 flagged missing cells
- confidential_flag->fdi_usd preserves 86,123 flagged missing cells
- Mexico FDI contains 19,980 residual-country rows
- Mexico FDI contains 14,304 negative flow cells; flow reversals are retained
- Mexico confidential C cells remain null and cannot be treated as additive zeros

### Category counts

- `sector_level`: `{"industry_group": 362526, "sector": 57202, "subsector": 176638}`
- `parent_country_total_flag`: `{"False": 596366}`
- `parent_country_residual_flag`: `{"False": 576386, "True": 19980}`
- `confidential_flag`: `{"False": 510243, "True": 86123}`

### Suppression/confidentiality consistency

- `confidential_flag->fdi_million_usd`: `{"flagged_missing": 86123, "flagged_nonmissing": 0, "unflagged_missing": 0, "unflagged_nonmissing": 510243}`
- `confidential_flag->fdi_usd`: `{"flagged_missing": 86123, "flagged_nonmissing": 0, "unflagged_missing": 0, "unflagged_nonmissing": 510243}`

### Unit contract

- `fdi_million_usd`: millions of current USD
- `fdi_usd`: current USD; equals fdi_million_usd multiplied by 1,000,000

## Interpretation

PASS means the frozen inputs have unique stated natural keys, no null key cells, and no hard inconsistency in the source-specific checks. Expected limitations remain part of the downstream data contract; PASS does not authorize converting suppressed, confidential, aggregate, allocated, or unavailable observations to zero.
