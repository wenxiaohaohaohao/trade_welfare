# Section 301 Tariff Pipeline Status, 2026-07-10

> Historical pause record. Superseded by the completed 2026-07-18 build documented in `data/section301_usage_note.md`. Do not use this file as the current status.

## Current Result

The Section 301 raw-source archive has been created, but no interim policy output has been generated.

Existing raw archive:

- `data/raw/ustr_section301/`
- `data/raw/ustr_section301/metadata/section301_source_manifest.json`

Manifest status from the latest local check:

| Status | Count |
|---|---:|
| Manifest entries | 224 |
| Downloaded | 216 |
| Download failed | 8 |

The failed downloads are legacy CBP CSMS or USTR exclusions portal links that repeatedly failed with connection/TLS errors. They are recorded in the manifest rather than treated as successful downloads.

## Outputs Not Generated

The following planned outputs have not been generated:

| Output | Reason |
|---|---|
| `data/interim/policy/section301_hts10_list_panel.parquet` | Missing verified official code table at `data/raw/ustr_section301/metadata/section301_notice_codes.csv`. |
| `data/interim/policy/section301_hs6_exposure.parquet` | Requires the HTS10 list panel and a full-origin 2017 Census HS10 denominator. Neither condition is currently satisfied. |
| `data/interim/policy/section301_build_summary.json` | Processing stage did not run to output because required inputs are incomplete. |
| `data/interim/policy/section301_hts10_expansion_audit.csv` | HTS8-to-HTS10 expansion was not run. |
| `data/interim/policy/section301_extraction_audit.csv` | Automatic text extraction is intentionally disabled for final data generation. |

## Why Processing Is Paused

Two required inputs are still missing.

First, the official HTS code table has not been finalized. The script requires:

```text
data/raw/ustr_section301/metadata/section301_notice_codes.csv
```

Automatic regex extraction from notices is not accepted as final data because the official PDFs contain multiple annexes, proposed lists, implemented lists, exclusions, amendments, and technical modifications in the same or related documents. A whole-document regex pass can mix actual tariffed products with proposed or descriptive codes. This is especially risky for List 1, List 4A/List 4B, and exclusion-related notices.

Second, the current Census HS10 file is not a full-origin denominator. The available file:

```text
data/interim/trade/us_imports_hs10_monthly.parquet
```

contains the project comparator-country subset. The latest check found 15 origins for 2017. Section 301 exposure requires total U.S. imports from all origins in 2017, because:

```text
china_import_share_2017 = China HS10 imports / total U.S. HS10 imports from all origins
tariff_exposure = china_import_share_2017 * tariff_rate
```

Using the 15-origin comparator subset would overstate or otherwise distort the denominator, so the script correctly refuses to generate exposure.

## Attempted Supplement Work

The local raw USTR archive was inspected for machine-readable notice content. Core notice PDFs can be parsed, but page-range and annex-level parsing is required before producing a defensible official code table. The preliminary checks showed that full-document extraction would over-include codes.

A small Census API probe for full-origin 2017 HS10 data was also attempted. The local environment did not have `CENSUS_API_KEY` set, and the request to `api.census.gov` timed out during TLS handshake even when retried with external network permission. No full-origin Census file was created.

## Conditions To Resume

Resume this batch when one of the following is available:

- a verified `section301_notice_codes.csv` built from official USTR/Federal Register/govinfo/CBP notices; and
- a full-origin 2017 Census HS10 import denominator, saved as a separate input or configured explicitly, without overwriting the existing comparator-country Census parquet.

Until both are available, do not generate:

- `section301_hts10_list_panel.parquet`
- `section301_hs6_exposure.parquet`

This avoids false precision and prevents incomplete or over-broad tariff exposure data from entering later model inputs.
