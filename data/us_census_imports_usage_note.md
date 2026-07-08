# U.S. Census Monthly Import Data Usage Note

## Purpose

The U.S. Census International Trade API will be used as the high-frequency U.S.-destination trade source for:

- U.S. imports from China before and after Section 301;
- import substitution from Vietnam, Mexico, Canada, and comparator origins;
- HS10 and HS6 monthly event-window facts;
- later Section 301 tariff exposure work.

This source complements BACI. BACI is global and annual; Census is U.S.-destination and monthly.

## Official API

Endpoint:

`https://api.census.gov/data/timeseries/intltrade/imports/hs`

The endpoint uses `CTY_CODE` rather than ISO3 country codes, so the pipeline first builds a Census country-code lookup and maps it back to the project's ISO3 origin list.

The Census API currently requires an API key. The build script reads it from:

`CENSUS_API_KEY`

Do not store the key in tracked files.

## Local Raw Layout

Raw API responses should be stored under:

```text
data/raw/us_census/
  hs10_monthly_imports/
  hs6_monthly_imports/
  metadata/
```

The directories are ignored by git.

## Build Command

Install dependencies:

```powershell
python -m pip install -r code\data_build\requirements-us-census.txt
```

Check the planned scope without making API calls:

```powershell
python code\data_build\download_us_census_imports.py --check-config
```

After setting `CENSUS_API_KEY`, download and process:

```powershell
python code\data_build\download_us_census_imports.py --overwrite
```

The script uses a staging directory by default. Official raw files and parquet
outputs are published only after all API calls, parquet writes, and output
validation succeed.

## Output Files

The script writes:

```text
data/interim/trade/us_imports_hs10_monthly.parquet
data/interim/trade/us_imports_hs6_monthly.parquet
```

Minimum analysis fields:

| Field | Meaning |
|---|---|
| `year` | Year |
| `month` | Month |
| `origin_iso3` | Project ISO3 origin code |
| `hts10` | HTS10 code for HS10 output; missing for HS6 output |
| `hs6` | Six-digit HS code |
| `import_value_usd` | General imports total value, from `GEN_VAL_MO` |
| `quantity` | General imports quantity 1, from `GEN_QY1_MO` |
| `customs_value` | Imports-for-consumption total value, from `CON_VAL_MO` |
| `duties` | Calculated duty, from `CAL_DUT_MO` |
| `source_file` | Raw API response file |

Extra fields retained:

- `origin_census_code`
- `origin_name`
- `quantity_unit`
- `dutiable_value_usd`
- `commodity_description`

## Current Build Status

Built successfully for monthly `2014-2024` data on 2026-07-08.

Raw file counts:

| Raw directory | Files |
|---|---:|
| `data/raw/us_census/hs10_monthly_imports/` | 1,980 |
| `data/raw/us_census/hs6_monthly_imports/` | 1,980 |

Output validation:

| Output | Rows | Years | Origins | Positive-value rows |
|---|---:|---|---:|---:|
| `data/interim/trade/us_imports_hs10_monthly.parquet` | 12,132,098 | 2014-2024 | 15 | 8,368,182 |
| `data/interim/trade/us_imports_hs6_monthly.parquet` | 5,017,364 | 2014-2024 | 15 | 3,829,092 |

Validation summary file:

```text
data/interim/trade/us_census_imports_build_summary.json
```

The successful run used `CENSUS_API_KEY` from the process environment. The API
key is not stored in tracked project files.

## Validation Status

Full validation passed on 2026-07-08 after rebuilding the parquet outputs from
the official raw directory.

Validation artifacts:

```text
data/validation/us_census_imports_validation.json
data/validation/us_census_imports_validation.md
```

Validation scope:

- checked all 1,980 HS10 raw JSON files and all 1,980 HS6 raw JSON files;
- checked parquet schema, source-file paths, HS code length rules, nonnegative
  measures, required fields, and within-source product-key uniqueness;
- compared raw JSON and parquet row counts and sums for every source file;
- re-queried selected Census API country-month-level cells and confirmed exact
  matches against local raw JSON and parquet aggregates.

Important correction: the first staged parquet build recorded staging paths in
`source_file`. The parquet outputs were rebuilt with `--process-only --overwrite`
so `source_file` now points to the official raw files under
`data/raw/us_census/`.
