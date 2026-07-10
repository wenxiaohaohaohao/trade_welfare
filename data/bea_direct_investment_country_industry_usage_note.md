# BEA Direct Investment Country-Industry Usage Note

## Source

- Provider: U.S. Bureau of Economic Analysis (BEA)
- Source page: https://www.bea.gov/data/intl-trade-investment/direct-investment-country-and-industry
- U.S. direct investment abroad page: https://www.bea.gov/international/di1usdbal
- Foreign direct investment in the United States page: https://www.bea.gov/international/di1fdibal
- Local build script: `code/data_build/build_bea_direct_investment_country_industry.py`
- Cleaned output: `data/interim/fdi/bea_direct_investment_country_industry.parquet`
- Raw-file manifest: `data/raw/bea_fdi/metadata/bea_direct_investment_country_industry_manifest.json`

## Coverage

Batch 6 covers 2020-2024 because `position`, `flows`, and `income` are jointly available for both directions in the BEA static country-by-industry files. If the project later needs a longer window or earlier historical years, extend this as a separate follow-up batch by downloading the matching BEA files and rerunning validation before merging them into an analysis panel.

Directions:

- `us_direct_investment_abroad`: U.S. direct investment abroad by selected foreign country and selected industry.
- `foreign_direct_investment_in_us`: foreign direct investment in the United States by selected foreign country and selected industry.

The BEA pages also list 2025 position files. They are not included in the default panel because matching 2025 annual flows and income are not part of this batch. If later BEA releases provide matching 2025 flows and income, add them through the same download-manifest-validation workflow rather than manually appending position-only observations.

## Fields

Minimum fields:

- `year`
- `direction`
- `country`
- `industry`
- `position`
- `flows`
- `income`
- `source_file`

The output also keeps BEA area classification and indicator-level provenance:

- `bea_area_type`
- `bea_parent_area`
- `{position,flows,income}_raw_code`
- `{position,flows,income}_suppressed`
- `{position,flows,income}_small_value`
- `{position,flows,income}_source_file`
- `{position,flows,income}_source_url`

## Interpretation

Use this source for investment validation, not as a direct production measure. `position`, `flows`, and `income` can support connector-country investment checks and Scenario C / `hgamma` discipline when kept separate from affiliate output, value added, employment, and sales evidence.

Financial-transaction sign conventions differ by direction:

- `us_direct_investment_abroad`: BEA reports outflows as positive and inflows as negative.
- `foreign_direct_investment_in_us`: BEA reports inflows as positive and outflows as negative.

BEA `(D)` values are disclosure-suppressed cells and should be treated as unavailable, not as zero. BEA `(*)` cells are rounded small values and are stored as `0.0` with the corresponding small-value flag.

## Scenario Mapping

- Scenario A: not a direct trade-only input.
- Scenario B: secondary support only; use BEA MNE / AMNE affiliate activity first for incumbent MP-intensive calibration.
- Scenario C: useful as model-external investment evidence, especially for Mexico / Canada North America extension checks and broader connector-country investment validation.
