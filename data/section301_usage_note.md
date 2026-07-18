# USTR Section 301 Tariff Data Usage Note

## Purpose and status

This batch builds a reproducible **gross statutory Section 301 exposure** measure for the China-to-United States trade link. It is suitable for affected-product flags, product-level policy exposure, and first-version `htau` discipline.

The build was completed and validated on 2026-07-18. It does not use PIIE/Bown or another cleaned third-party tariff file. Official USTR/Federal Register notices define the actions, official USITC HTS files define the action-date product universes, U.S. Census imports provide China HTS10 weights, and CEPII BACI HS2017 provides China/total-U.S. HS6 import shares.

This output is not a customs-entry reconstruction of duties collected. Historical product-description exclusions are archived but are not applied to the gross statutory exposure panel.

## Policy scope

The main HS2017 panel includes:

- List 1, effective 2018-07-06 at 25 percent;
- List 2, effective 2018-08-23 at 25 percent;
- List 3, effective 2018-09-24 at 10 percent and 25 percent from 2019-05-10;
- List 4A, effective 2019-09-01 at 15 percent and 7.5 percent from 2020-02-14.

List 4B is not treated as tariffed because its duty was suspended before its scheduled effective date. Exact-code and product-description exclusions remain in the official raw archive, but they are not used to zero whole HTS10 lines in this gross schedule.

The September 2024 four-year-review changes use the modern HTS nomenclature and are stored separately:

```text
data/interim/policy/section301_2024_review_codes.parquet
```

That table contains 367 affected codes: 355 at 25 percent, two at 50 percent, and ten at 100 percent, effective 2024-09-27. Two rows have description-level exceptions and are flagged `whole_code_applicable=false`. Do not merge this table to the 2017 exposure panel by taking only the first six digits; doing so would incorrectly assign modern statistical breakouts to older HS2017 products.

## Official base-list construction

The deterministic official-code build is:

```powershell
python code\data_build\build_ustr_section301_notice_codes.py --project-root . --overwrite
```

It writes:

```text
data/raw/ustr_section301/metadata/section301_notice_codes.csv
data/raw/ustr_section301/metadata/section301_notice_code_build_audit.json
```

Verified source-row counts are:

| Action | Rows |
|---|---:|
| List 1 | 818 |
| List 2 | 279 |
| List 3 | 5,775 |
| List 4A | 3,243 |
| Total | 10,115 |

Partial HTS8 descriptions in List 3 and List 4A are expanded only to the explicitly covered HTS10 lines. The two subheadings removed by 83 FR 49153, `03048110` and `03048150`, are excluded. The same notice replaced 12 obsolete Chapter 44 subheadings with 38 successors; the HS6 exposure build records that successor mapping explicitly.

The List 1 PDF text layer truncates its final `9033.00.90` entry to `9033.00`. The build restores `90330090` using the product-description table in the same official notice and then asserts uniqueness at `hts10 x list_id x effective_date`. Treating the truncated text as a whole HS6 would duplicate `9033002000` and `9033003000`.

Configured official HTS universes are:

| Action | USITC HTS file |
|---|---|
| List 1 | 2018 Revision 8 |
| List 2 | 2018 Revision 10 |
| List 3 | 2018 Revision 12, with the 2017 schedule retained only for superseded Chapter 44 codes |
| List 4A | 2019 Revision 12 |

The exact 2024 review table is regenerated with:

```powershell
python code\data_build\build_ustr_section301_2024_review_codes.py --project-root . --overwrite
```

## BACI HS2017 denominator

The Section 301 denominator uses CEPII BACI HS2017 V202601, not the project's general HS2012 panel. Regenerate it with resumable download and ZIP CRC validation:

```powershell
python code\data_build\build_baci_hs17_us_imports_2017.py --project-root . --download --overwrite
```

If an intercepting proxy prevents certificate validation, add `--insecure`; that choice is recorded in the run context. The raw archive and compact denominator are:

```text
data/raw/BACI_HS17_V202601/BACI_HS17_V202601.zip
data/interim/trade/baci_hs17_us_imports_2017.parquet
```

Validated BACI facts:

| Check | Result |
|---|---:|
| ZIP size | 794,583,540 bytes |
| ZIP SHA256 | `16aaa22d3b000cc87744c2c28ac97ce44394c3adf315ec259451d5bb4fcae609` |
| ZIP CRC test | Passed |
| 2017 source rows | 9,948,845 |
| 2017 U.S. import rows | 187,990 |
| HS2017 output rows | 5,384 |
| Total U.S. imports | USD 2,274,243,094,334 |
| Imports from China | USD 492,682,263,643 |

BACI publishes the petroleum heading 2710 as `271000`. The build maps the five detailed policy HS6 codes under that heading to this documented BACI aggregate. The Chapter 44 aliases follow the successor codes in 83 FR 49153.

## Main build and outputs

Run the full existing-archive build with:

```powershell
python code\data_build\build_ustr_section301.py --project-root . --process-only --overwrite
```

Outputs:

| File | Rows | Purpose |
|---|---:|---|
| `data/interim/policy/section301_hts10_list_panel.parquet` | 32,357 | Unique HTS10 policy-event panel, including the List 3 and List 4A rate changes. |
| `data/interim/policy/section301_hs6_exposure.parquet` | 55,308 | Balanced affected-HS6 panel for 2014-2024. |
| `data/interim/policy/section301_build_summary.json` | n/a | Paths, source mode, totals, aliases, and validation context. |
| `data/interim/policy/section301_2024_review_codes.parquet` | 367 | Exact modern-HTS four-year-review rates, kept separate from HS2017. |

The HS6 exposure fields are:

| Field | Meaning |
|---|---|
| `year` | Calendar year, 2014-2024. |
| `hs6` | HS2017 product code, including documented BACI aggregates/successors. |
| `origin_iso3`, `destination_iso3` | `CHN` and `USA`. |
| `tariffed_product` | True when any covered HTS10 line in the HS6 has a positive statutory rate. |
| `list_id` | Semicolon-separated contributing Section 301 actions. |
| `tariff_rate` | Calendar-day annual rate, weighted across China-origin Census HTS10 imports within HS6; a legally covered HS6 can have zero if its 2017 China imports occur only in uncovered HTS10 lines. |
| `china_import_share_2017` | BACI 2017 imports from China divided by total U.S. imports for the HS6. |
| `tariff_exposure` | `tariff_rate * china_import_share_2017`. |

The Census China HTS10 total used for within-HS6 weights is USD 498,987,736,788. The BACI China import total is USD 492,682,263,643; the difference is about 1.3 percent and reflects source/processing differences rather than a forced reconciliation.

## Interpretation limits

Use `section301_hs6_exposure.parquet` as a gross policy-shock measure. Do not describe it as the tariff actually paid after exclusions, refunds, avoidance, de minimis treatment, or customs rulings.

Use `section301_2024_review_codes.parquet` when the analysis explicitly needs the September 2024 targeted increases. It requires a modern HTS trade denominator or a scope-aware concordance before aggregation to the HS2017 exposure panel.

The raw archive remains under `data/raw/ustr_section301/` and is never overwritten by the processing scripts.
