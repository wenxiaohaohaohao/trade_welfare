# BACI 202601 Usage Note

## Local Raw Data

The usable BACI 202601 raw data are stored at:

`data/raw/BACI_HS12_V202601/`

This directory contains yearly CSV files for 2012-2024:

`BACI_HS12_Y{year}_V202601.csv`

It also contains:

- `country_codes_V202601.csv`
- `product_codes_HS12_V202601.csv`
- `Readme.txt`

The older file `data/raw/baci.dta` is not sufficient for Batch 1 because it only covers 2000-2014.

## Verified Coverage

| Item | Verified result |
|---|---|
| BACI version | 202601 |
| Release date in README | 2026-01-22 |
| Local CSV years | 2012-2024 |
| Batch 1 required years | 2014-2024 |
| Product metadata rows | 5,202 |
| Product code length | 6 digits |
| Trade value unit | thousand USD |
| Quantity unit | metric tons |

The local files cover the full `pre_period`, `shock_period`, and `post_period` defined in `configs/time_windows.yaml`.

## Raw Field Mapping

| Raw column | Meaning | Batch 1 field |
|---|---|---|
| `t` | year | `year` |
| `i` | exporter numeric country code | map to `exporter_iso3` using `country_codes_V202601.csv` |
| `j` | importer numeric country code | map to `importer_iso3` using `country_codes_V202601.csv` |
| `k` | HS6 product code | `hs6`, preserved as a six-character string |
| `v` | value in thousand USD | `trade_value_usd = v * 1000` |
| `q` | quantity in metric tons | `quantity` |
| raw filename | yearly CSV source | `source_file` |

Set `unit = "metric_tons"` for the quantity field.

## Country Mapping

Use `country_codes_V202601.csv` to convert `i` and `j` to ISO3 codes.

The required countries are available except Taiwan:

| ISO3 in config | BACI status |
|---|---|
| `CHN`, `USA`, `VNM`, `MEX`, `CAN`, `IND`, `IDN`, `MYS`, `PHL`, `THA`, `KOR`, `POL`, `MAR`, `TUR`, `JPN` | Direct ISO3 mapping exists |
| `TWN` | No direct ISO3 mapping; BACI uses `country_code = 490`, `country_iso3 = S19`, `country_name = Other Asia, nes` |

Do not silently map `TWN` to `S19`. If Taiwan is used in the first-round comparator set, the mapping must be explicitly documented as a proxy.

## Batch 1 Outputs

The first processing pass should create:

```text
data/interim/trade/baci_hs6_panel.parquet
data/interim/trade/baci_connector_flows.parquet
data/interim/trade/baci_country_product_year_flags.parquet
```

Recommended construction:

1. Read yearly CSV files for 2014-2024 only.
2. Preserve `k` as a string to avoid losing leading zeros.
3. Merge exporter and importer numeric codes to ISO3.
4. Convert `v` from thousand USD to USD.
5. Keep `q` as metric tons; allow missing quantity.
6. Add `source_file`.
7. Filter or flag country pairs needed for China -> connector and connector -> USA.
8. Add sector and BEC mappings only after the HS6 panel is built.

## Required Python Dependency

The Batch 1 build writes parquet outputs with `pyarrow`. Install the BACI build dependencies before running:

```powershell
python -m pip install -r code\data_build\requirements-baci.txt
```

Then build the Batch 1 outputs with:

```powershell
python code\data_build\build_baci_batch1.py --overwrite
```

For Stata-facing work, keep `baci_hs6_panel.parquet` as parquet and export only the two lightweight tables:

```powershell
python code\data_build\export_baci_lightweight_dta.py --overwrite
```

## Verification Samples

Target flows were verified in 2014, 2018, 2020, and 2024 for:

- CHN -> VNM
- CHN -> MEX
- CHN -> CAN
- VNM -> USA
- MEX -> USA
- CAN -> USA
- CHN -> USA

All checked flows have positive row counts and positive trade values in those years.
