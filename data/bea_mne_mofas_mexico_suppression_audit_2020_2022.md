# BEA U.S. MNE MOFA Mexico Suppression Audit, 2020-2022

## Scope

- Country: Mexico
- Source: BEA U.S. Direct Investment Abroad, Activities of U.S. Multinational Enterprises, Majority-Owned Foreign Affiliates country-by-industry downloadable tables.
- BEA release/vintage: 2025-08 downloadable tables
- Download/audit date: 2026-07-01
- Machine-readable extract: `data/interim/bea_mne_mofas_mexico_suppression_audit_2020_2022.csv` (ignored by git).

## Main Result: Mexico x Transportation Equipment

| Indicator | Unit | 2020 | 2021 | 2022 | 2020-2022 change | Suppressed in 2020-2022? |
|---|---|---:|---:|---:|---:|---|
| Employment | Thousands of employees | 353.8 | 364.3 | 406.4 | 52.6 (+14.9%) | No |
| Value added | Millions of dollars | 8,247 | 11,000 | 12,588 | 4,341 (+52.6%) | No |
| PPE expenditures | Millions of dollars | 1,556 | 2,454 | 3,400 | 1,844 (+118.5%) | No |
| Sales | Millions of dollars | 65,192 | 81,052 | 95,617 | 30,425 (+46.7%) | No |
| Assets | Millions of dollars | 38,964 | 49,526 | 59,242 | 20,278 (+52.0%) | No |

Conclusion: `Mexico x Transportation equipment` is not suppressed in any of the five audited MOFA indicators for 2020-2022. It is usable for the North America production-side validation and can fill the post-2020 OECD Analytical AMNE gap for this sector-country line.

## Nearby Sector Check: Mexico x Computers and Electronic Products

| Indicator | Unit | 2020 | 2021 | 2022 | Suppressed in 2020-2022? |
|---|---|---:|---:|---:|---|
| Employment | Thousands of employees | 73.8 | 73.4 | 79.9 | No |
| Value added | Millions of dollars | 1,754 | 1,653 | 1,978 | No |
| PPE expenditures | Millions of dollars | (D) | (D) | (D) | Yes |
| Sales | Millions of dollars | 3,604 | 4,081 | 4,672 | No |
| Assets | Millions of dollars | 3,343 | 3,793 | 4,348 | No |

## Suppressed Mexico Cells Found In The Audit

| Indicator | Industry | Year | Value |
|---|---|---:|---|
| PPE expenditures | Computers and electronic products | 2020 | `(D)` |
| PPE expenditures | Information | 2020 | `(D)` |
| PPE expenditures | Other industries | 2020 | `(D)` |
| PPE expenditures | Computers and electronic products | 2021 | `(D)` |
| PPE expenditures | Computers and electronic products | 2022 | `(D)` |
| Sales | Mining | 2020 | `(D)` |
| Sales | Other industries | 2020 | `(D)` |
| Sales | Mining | 2021 | `(D)` |
| Sales | Other industries | 2021 | `(D)` |

## Interpretation Rules

- `(D)` means BEA suppressed the cell to avoid disclosure of individual-company data; it should be treated as unavailable, not as zero.
- `Transportation equipment` is a broad BEA affiliate-industry category. It is usable as the project-level automotive-chain proxy only if the sector concordance records this aggregation choice.
- Aggregate MOFA data identify affiliate activity expansion, not firm-level relocation. Use these moments to discipline MP relocation scenarios rather than to claim direct plant movement.
