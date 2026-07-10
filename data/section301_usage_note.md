# USTR Section 301 Tariff Data Usage Note

## Purpose

The Section 301 tariff layer is the policy-shock source for product-level tariff exposure, affected-product flags, and the direct `htau` shock discipline.

The first version uses official sources only:

- USTR China Section 301 tariff action pages;
- Federal Register or govinfo notices linked from USTR;
- CBP guidance linked from USTR.

PIIE/Bown or other cleaned third-party files are not used in the first version.

## Local Raw Layout

Raw source files are archived under:

```text
data/raw/ustr_section301/
  list1/
  list2/
  list3/
  list4/
  exclusions/
    machinery/
  four_year_review/
  metadata/
```

The generated raw-source manifest is:

```text
data/raw/ustr_section301/metadata/section301_source_manifest.json
```

Raw files and generated manifests remain ignored by git.

## Current Status

As of 2026-07-10, the raw archive has been downloaded, but interim policy outputs have not been generated. The detailed pause record is:

```text
data/section301_status_2026_07_10.md
```

Processing is paused because the verified official code table is not complete and the available Census HS10 parquet is a 15-origin comparator subset rather than a full-origin 2017 denominator.

## Build Commands

Install dependencies:

```powershell
python -m pip install -r code\data_build\requirements-ustr-section301.txt
```

Check configuration without network calls:

```powershell
python code\data_build\build_ustr_section301.py --check-config
```

Download official source pages and linked official notices:

```powershell
python code\data_build\build_ustr_section301.py --download-only
```

After a production download, inspect the manifest status counts. A manifest with `download_failed` entries is auditable, but it is not a complete raw archive:

```powershell
$m = Get-Content -Raw -Encoding UTF8 data\raw\ustr_section301\metadata\section301_source_manifest.json | ConvertFrom-Json
$m | Group-Object status | Select-Object Name,Count
```

Diagnostic capped downloads are allowed only to test connectivity and link parsing:

```powershell
python code\data_build\build_ustr_section301.py --download-only --max-links-per-page 3
```

Capped downloads write `section301_source_manifest_diagnostic.json`, not the production manifest. Do not use a diagnostic manifest as a data source.

Process an existing raw archive:

```powershell
python code\data_build\build_ustr_section301.py --process-only --overwrite
```

The processing stage is intentionally split:

```powershell
python code\data_build\build_ustr_section301.py --process-only --panel-only --overwrite
python code\data_build\build_ustr_section301.py --exposure-only --overwrite
```

`--panel-only` writes only `section301_hts10_list_panel.parquet`. It still requires a valid HTS10 source: exact HTS10 official codes can be used directly, but HTS8 codes require a full-origin 2017 Census HS10 universe for expansion.

`--exposure-only` reads an existing HTS10 panel and builds `section301_hs6_exposure.parquet`. It always requires full-origin 2017 Census HS10 imports.

## Census Dependency

The HS6 exposure file requires a full-origin U.S. Census HS10 import file for 2017:

```text
data/interim/trade/us_imports_hs10_monthly.parquet
```

The file must contain all U.S. origins, not only the project comparator subset. The script checks this by requiring at least 100 origins in 2017. If this condition is not met, exposure construction stops with an explicit error.

The current comparator-country Census file is useful for other project tasks, but it must not be used as the denominator for Section 301 exposure.

## Optional Official Code Table

Processing defaults to an official extracted code table at:

```text
data/raw/ustr_section301/metadata/section301_notice_codes.csv
```

Automatic text extraction from downloaded notices is disabled by default because regex-based HTS detection can be incomplete or can capture non-list codes. It can be enabled only for diagnostics with `--allow-text-extraction`; do not treat that output as final without manual review against the official notice.

Required columns:

| Field | Meaning |
|---|---|
| `source_code` | Official HTS8 or HTS10 code, with or without dots |
| `list_id` | `list1`, `list2`, `list3`, `list4a`, `list4b`, or a later official review label |
| `effective_date` | ISO date for rate effectiveness |
| `additional_tariff_rate` | Decimal rate, e.g. `0.25` for 25 percent |
| `source_notice` | Official notice title |

Recommended columns:

- `source_url`
- `source_file`
- `notice_date`
- `exclusion_flag`
- `exclusion_start`
- `exclusion_end`

List 4 should use this table unless a parser can distinguish List 4A from List 4B in the official annex text. This avoids treating postponed List 4B products as tariffed.

## Outputs

The script writes:

```text
data/interim/policy/section301_hts10_list_panel.parquet
data/interim/policy/section301_hs6_exposure.parquet
data/interim/policy/section301_build_summary.json
```

The HTS10 panel includes:

| Field | Meaning |
|---|---|
| `hts10` | Expanded 10-digit HTS code |
| `hs6` | First six digits of `hts10` |
| `list_id` | Section 301 list or review identifier |
| `effective_date` | Date on which the additional rate applies |
| `additional_tariff_rate` | Decimal additional tariff rate |
| `exclusion_flag` | Whether the row reflects an official exclusion |
| `exclusion_start`, `exclusion_end` | Exclusion interval if known |
| `source_notice` | Official notice label |
| `source_url`, `source_file` | Audit source |
| `notice_date` | Notice date if provided |
| `source_code`, `source_code_level` | Original official code and its level |
| `rate_adjustment_applied` | Whether the row changes the rate used in exposure |

The HS6 exposure file includes:

```text
hs6
year
origin_iso3
destination_iso3
tariffed_product
list_id
tariff_rate
china_import_share_2017
tariff_exposure
```

The exposure formula is:

```text
tariff_exposure = china_import_share_2017 * tariff_rate
```

`tariff_rate` is a calendar-day weighted annual rate, then aggregated from HTS10 to HS6 using 2017 total U.S. import value weights.

## Conservative Exclusion Rule

Whole-code or exact HTS10 exclusions can change the rate. Description-only exclusions are archived and auditable, but they should not zero out an entire HTS10 product line unless the official text clearly defines the full code as excluded.
