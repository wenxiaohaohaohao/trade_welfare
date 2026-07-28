# M3.3 Connector Trade Sector Growth Diagnostics Validation

## Material Passport

- Origin Skill: `academic-research-suite/experiment-agent`
- Origin Mode: `run + validate`
- Origin Date: `2026-07-28`
- Verification Status: `VERIFIED`
- Version Label: `connector_trade_sector_growth_diagnostic_rules_v1`

## Result

- Validation status: **PASS**
- Output: `data/processed/harmonized/connector_trade_sector_growth_diagnostics.parquet`
- Rows / columns: `364 / 64`
- Natural key: `connector_iso3, analysis_sector, flow_id`
- SHA256: `fe69d953cd84a2acfc64ddb17b1ee57e3d0e44f7b44cad348f9016aee7e0953d`

## Required gates

- Frozen M3.2 hash matches: `yes`.
- Input rows / columns / duplicate keys: `91 / 142 / 0`.
- Output rows / columns / duplicate keys: `364 / 64 / 0`.
- Incomplete four-flow connector-sector cells: `0`.
- Deterministic Parquet SHA256 match: `yes`.
- DH out-of-bounds / infinite numeric values: `0 / 0`.

## Small-base rules

- Absolute threshold: annual-mean pre-period trade value `<= USD 25,000,000`.
- Sector-relative threshold: nearest-rank 10th percentile within `flow_id × analysis_sector`; 13 connectors imply rank 2.
- The repeated China-to-USA benchmark does not receive a connector-relative threshold.
- Combined flag: `pre_zero OR absolute_small_base OR sector_relative_small_base`.
- Raw levels, level changes, DH growth, and log growth are never overwritten.

| Flow | Absolute | Sector-relative | Combined | Primary DH eligible | No-threshold DH eligible |
|---|---:|---:|---:|---:|---:|
| `china_to_connector` | 0 | 14 | 14 | 77 | 91 |
| `east_asia_to_connector` | 0 | 14 | 14 | 77 | 91 |
| `connector_to_usa` | 4 | 14 | 14 | 77 | 91 |
| `china_to_usa` | 0 | 0 | 0 | 91 | 91 |

## Abnormal-growth diagnostics

- Robust z-score uses the median and MAD within `flow_id × analysis_sector`; `|z| > 3.5` is flagged.
- A second mechanical flag marks `|DH| >= 1.5`, equivalent to a post/pre ratio of at least 7 or at most 1/7.
- The combined abnormal flag is advisory. It does not automatically exclude or alter an observation.
- MAD-zero groups: `7`; these are the seven repeated China-to-USA sector groups and robust z is undefined there.

| Flow | Robust-z outliers | Mechanical extremes | Combined abnormal |
|---|---:|---:|---:|
| `china_to_connector` | 1 | 0 | 1 |
| `east_asia_to_connector` | 1 | 0 | 1 |
| `connector_to_usa` | 1 | 3 | 4 |
| `china_to_usa` | 0 | 0 | 0 |

## Winsorized sensitivity variables

- DH and log growth receive flow-level p5/p95 linear/type-7 winsorized alternatives.
- Each flow has 91 reference cells. Winsorized measures are sensitivity variables only.
- Level changes are not winsorized. Raw DH/log values remain in separate fields.

| Flow | DH affected | Log affected | DH lower | DH upper | Log lower | Log upper |
|---|---:|---:|---:|---:|---:|---:|
| `china_to_connector` | 10 | 10 | 0.162408755628 | 1.057554663008 | 0.162768160865 | 1.176893562500 |
| `east_asia_to_connector` | 10 | 10 | -0.006410698626 | 0.812882457228 | -0.006414369323 | 0.862785485221 |
| `connector_to_usa` | 10 | 10 | -0.093441691738 | 1.277589923540 | -0.093509784296 | 1.513237664965 |
| `china_to_usa` | 0 | 0 | -0.167366766137 | 0.435611412071 | -0.167759100673 | 0.442702749251 |

## Preserved edge cases and interface

- Negative post-pre changes by flow are retained: `{'china_to_connector': {'pre_zero': 0, 'post_zero': 0, 'negative_change': 3}, 'east_asia_to_connector': {'pre_zero': 0, 'post_zero': 0, 'negative_change': 5}, 'connector_to_usa': {'pre_zero': 0, 'post_zero': 0, 'negative_change': 6}, 'china_to_usa': {'pre_zero': 0, 'post_zero': 0, 'negative_change': 26}}`.
- China-to-USA repeated-field inconsistencies: `0`.
- TWN rows / false proxy flags: `28 / 0`.
- Stata aliases: `64`; maximum length `11`; pass `yes`.
- Canonical format remains Parquet. No `.dta` is generated before M7.

## Interpretation boundaries

- `small_base_flag` controls eligibility for the preferred DH/log comparison; the raw no-threshold DH measure remains available for robustness.
- `abnormal_growth_flag` is a review flag, not a deletion rule.
- Winsorized growth values are robustness alternatives, not replacements for raw growth.
- This module does not construct replacement ratios, connector rankings, production-side variables, structural moments, or counterfactual inputs.
