# Data Build Code

This folder contains the reproducible raw-to-interim data pipelines. Builders preserve raw files, write generated data under `data/interim/` or `data/model_inputs/`, and write JSON summaries for validation and provenance.

## Current Builders

| Data layer | Main script | Main output family |
|---|---|---|
| OECD ICIO | `build_oecd_icio_baseline.py` | `data/interim/production/oecd_icio_*.parquet` and three `data/model_inputs/icio_baseline_*/` directories |
| OECD Analytical AMNE | `build_oecd_amne.py` | `data/interim/mne/oecd_amne_*.parquet` |
| CEPII BACI | `build_baci_batch1.py` | `data/interim/trade/baci_*.parquet` |
| U.S. Census imports | `download_us_census_imports.py`, `validate_us_census_imports.py` | `data/interim/trade/us_imports_*.parquet` |
| Section 301 | `build_ustr_section301_notice_codes.py`, `build_ustr_section301.py`, `build_ustr_section301_2024_review_codes.py` | `data/interim/policy/section301_*.parquet` |
| BEA U.S. MNE activity | `build_bea_us_mne_affiliate_country_industry.py` | `data/interim/mne/bea_us_mne_affiliate_country_industry.parquet` |
| BEA direct investment | `build_bea_direct_investment_country_industry.py` | `data/interim/fdi/bea_direct_investment_country_industry.parquet` |
| Mexico official FDI | `download_build_mexico_fdi.py` | nine `data/interim/fdi/mexico_fdi_*.parquet` outputs |

Use `configs/data_versions.yaml` for source versions and output paths. Use each `*_build_summary.json` as the machine-readable record of coverage, row counts, and validation results. Full commands and interpretation limits are documented in `data/README.md` and the source-specific usage notes.

`fDi Markets` is excluded from the current batch and has no builder here.
