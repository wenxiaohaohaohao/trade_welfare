# Section 301 Tariff Pipeline Status, 2026-07-10

> Historical pause record only. Superseded by the completed 2026-07-18 build documented in `data/section301_usage_note.md`. Do not use this file as the current status.

As of 2026-07-10, the pipeline was paused because the official notice-code table and a valid all-origin denominator had not yet been completed. Those blockers were subsequently resolved by:

- constructing and auditing the official base-list code table;
- expanding the action-date HTS10 universes;
- using the validated BACI HS2017 U.S.-import denominator together with Census China HTS10 weights; and
- keeping the exact September 2024 modern-HTS review table separate from the HS2017 exposure panel.

The current outputs are:

| Output | Current status |
|---|---|
| `data/interim/policy/section301_hts10_list_panel.parquet` | Complete: 32,357 unique HTS10 event rows. |
| `data/interim/policy/section301_hs6_exposure.parquet` | Complete: 55,308 HS6-year rows for 2014-2024. |
| `data/interim/policy/section301_2024_review_codes.parquet` | Complete: 367 exact modern-HTS review rows. |
| `data/interim/policy/section301_build_summary.json` | Complete build and validation summary. |

The exposure remains a gross statutory measure, not realized duties after historical product exclusions. Use `data/section301_usage_note.md` and `data/interim/policy/section301_build_summary.json` as the current sources of truth.
