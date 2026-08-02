# M4.2 OECD Analytical AMNE Production-Side Validation

- Origin Date: `2026-08-02`
- Verification Status: `VERIFIED`
- Version Label: `production_amne_rules_v1`

## Result

- Validation status: **PASS**.
- Parent-host source-detail long: `data/processed/harmonized/production_amne_parent_host_sector_long.parquet`; `7560318 × 71`; SHA256 `6e3d0a77838b9c1d0cbae6445ee9b3f5637114747e51a148162c720d26605bcb`.
- Host-analysis-sector long: `data/processed/harmonized/production_validation_amne_host_sector_long.parquet`; `53760 × 56`; SHA256 `b9219fbfe2852f5ca7088bcedf290526479147a57c3b63cc0a693194cc499179`.
- Natural-key duplicates: parent `0`, host `0`.
- Deterministic second-build hashes match: parent `True`, host `True`.

## Frozen Inputs and Coverage

- Positive-link affiliate activity: `1,260,053` rows; full zero-inclusive MP-share universe: `4,250,880` rows.
- The MP-share universe contains `2,990,827` zero-output parent links; its positive subset matches the activity table keys: `True`.
- Coverage is 81 source hosts, 81 source parents, 41 full-universe source sectors, and 16 years (2008–2023). Every host-source-sector-year has exactly 80 foreign parents.
- The two full-universe auxiliary sectors are `O84, T97T98`; all `207,360` rows have zero affiliate output and are explicitly excluded from manufacturing analysis without modifying M1.

## Direct, Allocated, Derived, and Unavailable Metrics

- `affiliate_output` is direct bilateral OECD AMNE output.
- Parent-level value added, exports, and imports are allocated from host-sector foreign-owned totals using bilateral parent output shares; they are not direct bilateral observations.
- Parent-share formula maximum error is `0`; allocated-metric formula maximum error is `1.46e-11` million USD.
- All `1,260,053` positive-link employment values remain missing and are marked unavailable; none are converted to zero.
- All `166` negative allocated parent-level value-added observations remain signed.

## Host-Sector Totals and Reconciliation

- Analysis grid: 80 actual hosts × 6 supported analysis sectors × 16 years = `7,680` cells; medical devices are not fabricated.
- Host foreign-affiliate output is the direct XVEM total. The bilateral parent-output sum is retained as a separate reconciliation metric and parent-share denominator.
- Maximum absolute bilateral-minus-XVEM gap is `0.112743254114` million USD at source-sector level and `0.205832572254` million USD after analysis-sector aggregation; this expected source-concept difference is not forced to zero.
- The host foreign-affiliate share is recomputed as a ratio of analysis-sector sums; formula maximum error is `0`.
- ROW parent contributions are included in host totals; ROW host is excluded from the actual-country analysis grid.

## Stata and Interpretation Boundary

- Stata aliases: parent long `71`, host long `56`; all are complete, unique, legal, and at most 32 characters.
- Parquet remains canonical; `.dta` export remains an M7 task.
- This module constructs annual levels only. It does not construct AMNE growth, MPE expansion, ranking, `hgamma`, structural moments, welfare inputs, BEA/FDI integration, or the final cross-source production table.
- AMNE affiliate activity supports incumbent MP-intensive evidence; it does not by itself prove plant entry or firm-level relocation.
