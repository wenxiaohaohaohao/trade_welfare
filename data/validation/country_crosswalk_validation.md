# Country Master Validation

- Generated at UTC: `2026-07-19T11:19:23.175596+00:00`
- Country master: `data/processed/concordances/country_crosswalk.parquet`
- SHA256: `29b4b4b936d8c974c2b9f9d9eaa37b9c5d67e170e94c39ccdbd5088be3adc4c6`
- Rows: `611`
- Sources: `8`
- Duplicate source keys: `0`
- Unresolved identifiers: `0`
- Invalid geography classifications: `0`
- Aggregate rows: `39`
- Residual rows: `1`
- Proxy rows: `1`
- Validation status: **PASS**

## Status by source

| Source | Mapping statuses |
|---|---|
| `baci` | `{"mapped_country": 225, "proxy": 1}` |
| `bea_fdi` | `{"aggregate": 20, "mapped_country": 60}` |
| `bea_mne` | `{"aggregate": 17, "mapped_country": 58}` |
| `mexico_fdi` | `{"mapped_country": 50, "residual": 1}` |
| `oecd_amne` | `{"aggregate": 1, "mapped_country": 80}` |
| `oecd_icio` | `{"aggregate": 1, "mapped_country": 80}` |
| `section301` | `{"mapped_country": 2}` |
| `us_census` | `{"mapped_country": 15}` |

## Required checks

- All analysis countries present: `yes`
- BACI S19 explicitly marked as TWN proxy: `yes`
- Forced BEA regional labels marked aggregate: `yes`

## Interpretation

The country master maps only genuine country observations to country_iso3. Aggregate, residual, and proxy records remain explicit. BACI S19 maps to TWN only as a documented project proxy. BEA regional/addendum labels and Mexico Otros paises cannot enter ordinary country joins.
