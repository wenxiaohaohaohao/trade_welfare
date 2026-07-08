# U.S. Census Imports Validation Report

Generated: 2026-07-08T16:08:15

Overall status: **PASS**

## Check Summary

| Check | Result |
|---|---|
| HS10 raw file count | PASS |
| HS10 raw JSON valid | PASS |
| HS10 parquet schema | PASS |
| HS10 parquet source_file valid | PASS |
| HS10 parquet grain | PASS |
| HS10 parquet validity | PASS |
| HS10 raw-parquet equality | PASS |
| HS6 raw file count | PASS |
| HS6 raw JSON valid | PASS |
| HS6 parquet schema | PASS |
| HS6 parquet source_file valid | PASS |
| HS6 parquet grain | PASS |
| HS6 parquet validity | PASS |
| HS6 raw-parquet equality | PASS |
| official API sample equality | PASS |

## Core Metrics

| Dataset | Raw files | Rows | Source files | Row groups |
|---|---:|---:|---:|---:|
| us_imports_hs10_monthly.parquet | 1,980 | 12,132,098 | 1,980 | 1,980 |
| us_imports_hs6_monthly.parquet | 1,980 | 5,017,364 | 1,980 | 1,980 |

## Official API Recheck

| Level | Month | Origin | API rows | Raw rows | Parquet rows | Exact raw match | Sorted raw match |
|---|---|---|---:|---:|---:|---|---|
| HS10 | 2014-01 | CAN | 7,132 | 7,132 | 7,132 | yes | yes |
| HS10 | 2018-07 | CHN | 13,748 | 13,748 | 13,748 | yes | yes |
| HS10 | 2019-06 | TWN | 6,905 | 6,905 | 6,905 | yes | yes |
| HS10 | 2020-04 | MEX | 7,753 | 7,753 | 7,753 | yes | yes |
| HS10 | 2024-12 | VNM | 7,272 | 7,272 | 7,272 | yes | yes |
| HS6 | 2014-01 | CAN | 3,281 | 3,281 | 3,281 | yes | yes |
| HS6 | 2018-07 | CHN | 4,442 | 4,442 | 4,442 | yes | yes |
| HS6 | 2019-06 | TWN | 2,893 | 2,893 | 2,893 | yes | yes |
| HS6 | 2020-04 | MEX | 3,252 | 3,252 | 3,252 | yes | yes |
| HS6 | 2024-10 | MEX | 3,938 | 3,938 | 3,938 | yes | yes |
| HS6 | 2024-12 | VNM | 2,727 | 2,727 | 2,727 | yes | yes |

## Notes

- Raw file completeness is checked against the configured 15 origins and 132 months.
- Raw-parquet equality compares row counts and sums of import value, quantity, customs value, duties, and dutiable value for every source file.
- Official API checks re-query selected country-month-level cells and compare the current API response against local raw JSON and parquet aggregates.
- The API key is read from the process environment and is not written to this report.
