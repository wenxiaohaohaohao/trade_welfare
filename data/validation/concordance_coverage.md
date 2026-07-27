# Concordance Validation and Coverage Report

- Generated at UTC: `2026-07-19T12:30:10.250566+00:00`
- Validation status: **PASS**
- Failure count: `0`

## Concordance natural keys

| Crosswalk | Rows | Duplicate keys | Natural key |
|---|---:|---:|---|
| `country_crosswalk` | 611 | 0 | `source_name, source_country_id` |
| `time_aggregation_rules` | 39 | 0 | `input_id, metric_name` |
| `hs_to_hs2012_conversion` | 16209 | 0 | `source_revision, source_hs6` |
| `hs_revision_correlations` | 27726 | 0 | `source_revision, source_hs6, target_hs6` |
| `census_hs6_year_to_hs2012` | 57347 | 0 | `year, source_hs6` |
| `product_sector_crosswalk` | 5202 | 0 | `analysis_hs6` |
| `source_sector_crosswalk` | 517 | 0 | `source_name, source_sector_level, source_sector_code` |

## Production and FDI value coverage

Rates use absolute observed values so valid negative FDI flows, positions, and income do not cancel positive observations. Suppressed, confidential, and source-missing values remain missing and are excluded from the numeric denominator, never changed to zero.

| Source | Metric | Observed rows | Missing rows | Explicit-status coverage | Analysis-sector share | Ambiguous share |
|---|---|---:|---:|---:|---:|---:|
| `oecd_icio` | `gross_output` | 12000 | 0 | 100.000000% | 24.898970% | 0.000000% |
| `oecd_icio` | `value_added` | 12000 | 0 | 100.000000% | 15.313568% | 0.000000% |
| `oecd_icio` | `exports` | 12000 | 0 | 100.000000% | 47.457921% | 0.000000% |
| `oecd_icio` | `imports` | 12000 | 0 | 100.000000% | 46.340087% | 0.000000% |
| `oecd_amne` | `affiliate_output` | 1171365 | 0 | 100.000000% | 44.684752% | 0.000000% |
| `oecd_amne` | `affiliate_value_added` | 1171365 | 0 | 100.000000% | 32.163094% | 0.000000% |
| `oecd_amne` | `affiliate_employment` | 0 | 1171365 | n/a | n/a | n/a |
| `oecd_amne` | `affiliate_exports` | 1171365 | 0 | 100.000000% | 56.688053% | 0.000000% |
| `oecd_amne` | `affiliate_imports` | 1171365 | 0 | 100.000000% | 55.960301% | 0.000000% |
| `bea_mne` | `sales` | 4580 | 978 | 100.000000% | 27.869557% | 6.233441% |
| `bea_mne` | `value_added` | 4650 | 908 | 100.000000% | 27.709913% | 4.905715% |
| `bea_mne` | `employment` | 5113 | 445 | 100.000000% | 22.050061% | 8.537780% |
| `bea_mne` | `capital_expenditures` | 4507 | 1051 | 100.000000% | 27.481359% | 7.043862% |
| `bea_fdi` | `position` | 6464 | 1136 | 100.000000% | 23.982799% | 2.981004% |
| `bea_fdi` | `flows` | 5589 | 2011 | 100.000000% | 26.741486% | 3.967970% |
| `bea_fdi` | `income` | 5732 | 1868 | 100.000000% | 18.056538% | 2.739493% |
| `mexico_fdi` | `fdi_usd` | 305796 | 43780 | 100.000000% | 47.463706% | 0.819920% |

## Trade and product coverage

- BACI/CEPII product codes with explicit status: `100.000000%`.
- BACI trade value with explicit product status: `100.000000%`.
- BACI trade value in the first-round analysis-sector scope: `72.950566%`; this is a sample-scope share, not an unmapped-data rate.
- Minimum HS-revision observed-value coverage: `97.192253%`.
- Minimum HS-revision eligible-value coverage: `99.996285%`.

## Interpretation

All source codes now have an explicit status. A value can be outside the first-round analysis sector and still be fully mapped: exclusions, services, aggregates, residuals, and mixed sectors are reported separately. Therefore the 95 percent completion threshold is applied to explicit mapping-status coverage, not to the deliberately narrower analysis-sector share. Medical devices remain unavailable as a standalone sector in OECD and BEA, BEA transportation equipment remains an unweighted autos proxy, and Mexico aggregate sector levels remain outside the main join.

## Structurally unavailable metrics

These measures have no observed numeric denominator and are retained as unavailable rather than interpreted as zero:

- `oecd_amne.affiliate_employment`
