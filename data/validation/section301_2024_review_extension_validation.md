# Section 301 2024 Review Exact-HTS Extension Validation

- Generated at UTC: `2026-07-19T12:52:53.906173+00:00`
- Output: `data/processed/policy/section301_2024_review_exact_hts.parquet`
- Validation status: **PASS**
- Exact HTS rows: `367`

## Required checks

- Input SHA256 matches: `yes`
- Unique exact HTS code: `yes`
- HTS8/HTS10 lengths preserved: `yes`
- Whole-code rows: `365`; description-scoped rows: `2`.
- Rate counts match the official-notice extraction: `yes`
- Historical HS6 merge prohibited and no `analysis_hs6` assigned: `yes`

## Interpretation

This is a separate 2024 exact-HTS extension. It is not part of the historical HS2017/HS2012 product-treatment panel. Two records are description-scoped and cannot be treated as whole-code coverage. No first-six-digit truncation or forced HS6 assignment is performed; integration requires a separately validated modern HTS concordance and scope rule.
