# Phase 1 Feasibility Memo Template

Use this template after the first descriptive data build. The memo should be two to three pages and should decide whether the project has enough signal to justify model migration.

## Question

Does connector-country activity provide enough evidence to support a JMP-level welfare-bound design with Scenario A trade-only lower bound, Scenario B incumbent MP-intensive baseline, and Scenario C total MP-adjustment upper-bound proxy?

## Required Evidence

1. Connector-country ranking table.
2. Direct bloc-to-bloc trade decline and third-country rerouting figure.
3. Production-side evidence from AMNE, value added, or a comparable source.
4. Extensive-margin evidence from fDi Markets, FDI, BEA/AMNE affiliate expansion, or production-side expansion for Scenario C discipline.
5. Structural moment table mapping each evidence layer to Scenario A, Scenario B, or Scenario C.
6. Data-to-model compatibility check using a small MATLAB-ready sample.

## Interpretation Standard

- Strong signal: connector rankings are stable, production-side evidence moves with trade rerouting, and Scenario C can be disciplined as an upper-bound proxy without being confused with an entry model.
- Mixed signal: trade rerouting is visible but production-side evidence is weak, lagged, or sufficient only for Scenario A and Scenario B.
- Weak signal: connector rankings depend on one country, one product group, or one year, or Scenario C would require unsupported assumptions.

## Decision

Choose one:

- Proceed to model migration.
- Continue descriptive validation before model migration.
- Pivot to a narrower country-sector case.
- Stop this topic and preserve the setup for later reuse.

If proceeding, the memo must state that Scenario C is not a fixed-cost entry model and that the B-to-C gap is only an extensive-margin-related upper-bound increment.
