# Product-Sector and BEC Crosswalk Validation

- Generated at UTC: `2026-07-19T12:16:01.320538+00:00`
- Output: `data/processed/concordances/product_sector_crosswalk.parquet`
- Validation status: **PASS**
- Product rows: `5202`

## Required checks

- Official source SHA256 matches: `yes`
- Unique `analysis_hs6`: `yes`
- BACI product universe fully covered with explicit status: `yes`
- Priority-sector set matches `sector_scope.yaml`: `yes`
- Eligible sector weights equal 1 and excluded weights are null: `yes`
- Ambiguous BEC rows kept without numeric allocation weights: `yes`
- CEPII `271000` collapse preserves BEC ambiguity: `yes`
- BACI `999999` remains an unmapped residual: `yes`

## Coverage

| Measure | Rate | Interpretation |
|---|---:|---|
| Explicit product status | 100.000000% | Every BACI product is mapped, excluded, outside manufacturing, or identified as residual. |
| Official ISIC classification | 100.000000% | The only non-official residual is BACI `999999`. |
| Official BEC end use | 100.000000% | Excludes official `n/a` monetary-gold/coin codes and BACI `999999`. |
| First-round analysis-sector share | 72.950566% | Sample-scope share, not an unmapped-data rate. |

## Sector counts

| Analysis sector | HS6 rows |
|---|---:|
| `autos` | 64 |
| `electrical_equipment` | 177 |
| `electronics` | 252 |
| `machinery` | 467 |
| `medical_devices` | 32 |
| `other_manufacturing` | 2422 |
| `textiles_apparel` | 823 |
| `<excluded or outside scope>` | 965 |

## Interpretation

`analysis_sector` and BEC end use are separate dimensions. Sector assignment is one-to-one and has weight 1 only for included manufacturing products. BEC composite labels retain all official uses, but they receive no allocation weights; using those labels to split trade values requires a later value-based rule. CEPII `271000` is sector-consistent across its five official HS2012 components but has multiple BEC uses, so it remains explicitly ambiguous for end-use analysis.
