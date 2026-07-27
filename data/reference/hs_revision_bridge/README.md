# HS Revision Bridge Sources

This folder contains the official public reference files used to harmonize HS2012, HS2017, and HS2022 six-digit product codes to the project's HS2012/CEPII analysis interface.

## Machine-readable sources

| File | Provider | Purpose | SHA256 |
|---|---|---|---|
| `source/unsd_hs2017_to_hs2012_conversion_correlation.xlsx` | United Nations Statistics Division | Official HS2017-to-HS2012 conversion and full correlation tables | `795b14a664a1a46e24bf72b45fae5128a05209c91f5f581ae419e57028497fac` |
| `source/unsd_hs2022_to_hs2012_conversion_correlation.xlsx` | United Nations Statistics Division | Official HS2022-to-HS2012 conversion and full correlation tables | `169a0f5e5fc66f6195964f0516ec177b864a09a8cd3514ccc2642d2d298ad453` |
| `source/unsd_hs2012_hs2017_bec5.xlsx` | United Nations Statistics Division | Official HS2012/HS2017 links to BEC Rev.5, BEC Rev.4, ISIC Rev.4, CPC, and GTAP | `a442ff475429a7a3bc908541c480bc511de5706166f746042cc1b67db064b37f` |

Source page: <https://unstats.un.org/unsd/classifications/econ>

## WCO validation sources

| File | Purpose | SHA256 |
|---|---|---|
| `source/wco_hs2017_to_hs2012_table_i_rev1.pdf` | WCO Table I, HS2017 to HS2012 with remarks | `0c143ddcd4f670f6d2310afe16cdc4d324bec4c735ca3a016c29e9cda53c0f6a` |
| `source/wco_hs2012_to_hs2017_table_ii_rev1.pdf` | WCO Table II, HS2012 to HS2017 | `00e04d7c307ec9211e3c994ad54cb8326365af830009d462a73ce5c1fdb98fa4` |
| `source/wco_hs2012_hs2017_corrigendum_1.pdf` | January 2016 correction, including the 8473 correlation block | `bea74bdd86da02646144bc3f8263f1a715ad4c5fa610f604699f906d162c39cc` |
| `source/wco_hs2012_hs2017_corrigendum_2.pdf` | October 2016 correction, including HS2012 4401.39 | `0962cf45038a27218fa5d23be68f0fcbff1b754d2f596d901e852a3bf567b6c5` |

Source pages:

- <https://www.wcoomd.org/en/topics/nomenclature/instrument-and-tools/hs_nomenclature_previous_editions/hs-nomenclature-2017-edition/correlation-tables-hs-2012-to-2017.aspx>
- <https://www.wcoomd.org/en/topics/nomenclature/instrument-and-tools/hs-nomenclature-2022-edition/correlation-tables-hs-2017-2022.aspx>

WCO states that its correlation tables are implementation guides rather than legal classification decisions. The project therefore keeps the original tables and corrigenda as provenance and uses the UNSD machine-readable conversion table for deterministic no-expansion harmonization.

## Project rule

The canonical conversion assigns exactly one HS2012 target and weight 1 to each source-revision code. The full many-to-many correlation is stored separately. Multi-target correlation rows intentionally have no numeric weight and cannot be used to aggregate values until a value-based weighting method is separately built and validated.

U.S. Census HS6 follows year-specific revision rules. National special-classification codes in chapters 98/99 are excluded from the internationally comparable product universe, while unresolved nonstandard codes remain explicit rather than receiving a guessed HS6 match.

The product-sector build uses the `HS12BEC5` sheet in the official UNSD workbook. `analysis_sector` is derived from its HS and ISIC Rev.4 fields. BEC final use remains a separate dimension. Official composite end uses and the CEPII `271000` collapse are retained without guessed allocation weights.
