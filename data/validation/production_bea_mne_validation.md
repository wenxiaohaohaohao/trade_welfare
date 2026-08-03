# M4.3 BEA MNE Production Standardization Validation

- Validation status: **PASS**
- Generated at (UTC): `2026-08-03T00:58:58.904648+00:00`
- Config SHA256: `24db24e60bc70e7646773cf8cdebf80396c0c36c4e4439e9b388a89a4c74265b`
- Failures: `0`

## Canonical outputs

| Output | Rows | Columns | SHA256 |
|---|---:|---:|---|
| `data/processed/harmonized/production_bea_mne_source_industry_long.parquet` | 49,536 | 69 | `016c7b10891e3770c14eeb9cf0f489bd9d80281c91bd1e10e2a883f76205b514` |
| `data/processed/harmonized/production_validation_bea_mne_long.parquet` | 11,910 | 66 | `21d9998c77e9fa8b458af288a36746567d4ade49c3a50360a0f684b329691ade` |

## Grain and coverage

- Source input: 8,256 country/area-industry-year rows, 75 source geography labels, 16 published industries.
- Raw BEA aggregate rows: 1,792; canonical country override rows: 112; final aggregate rows excluded from analysis: 1,904.
- Actual-country input: 6,352 rows, 57 ISO3 countries and 397 observed country-years.
- Strict main source rows: 1,985; Transportation-equipment autos-proxy source rows: 397.
- The analysis table contains four main sectors plus a separately flagged `autos` robustness proxy. It does not materialize unsupported medical-devices or textiles/apparel rows.

## Suppression and small values

- `(D)` and employment size-range codes remain missing with `suppressed_flag=true`; no suppressed value is converted to zero.
- `(*)` remains numeric 0.0 with `small_value_flag=true`; `exact_zero_flag` distinguishes it from an ordinary reported zero.
- For multi-industry analysis sectors, `value` is defined only if every required component is disclosed. `source_disclosed_value_sum` is retained only as a diagnostic partial sum.

## Negative value added

| Layer | Negative observations |
|---|---:|
| Full source | 164 |
| Actual-country source | 138 |
| Strict main source mapping | 32 |
| Strict main analysis | 19 |
| Autos proxy analysis | 18 |

Negative values are retained as valid BEA observations; they are not clipped.

## Determinism and Stata interface

- Source-long deterministic SHA256 match: `True`.
- Analysis-long deterministic SHA256 match: `True`.
- Temporary outputs cleaned: `True`.
- All aliases cover the output schemas, are unique, legal Stata names, and do not exceed 32 characters. `.dta` export remains deferred to M7.

## Interpretation boundaries

- `sales` is BEA affiliate sales, not ICIO gross output.
- Affiliate trade is not additive with BACI/Census trade.
- Transportation equipment is broader than autos and is retained only as `analysis_scope=proxy_robustness`, `proxy_flag=true`, and `main_analysis_join_eligible=false`.
- Vietnam is observed only for 2019-2023; 2017-2018 are not filled with zeros. Morocco is absent from this BEA source.
- M4.3 does not construct growth, rankings, cross-source production merges, structural moments, or counterfactual inputs.
