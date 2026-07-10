# Phase 1 Setup Checklist

## Completion Standard

Phase 1 setup is complete when the repository has a clean project skeleton, research design, data route, reference-model reuse rule, and A/B/C scenario-bound design. It does not require a full data build or MATLAB counterfactual.

## Required Files

- `README.md`
- `docs/research_design.md`
- `docs/reference_model_map.md`
- `data/README.md`
- `code/README.md`
- `output/README.md`

## First Empirical Deliverables

1. Connector-country ranking table.
2. Rerouting descriptive figure.
3. Production-relocation evidence table.
4. Extensive-margin evidence table for Scenario C discipline.
5. Structural moment table mapping evidence to Scenario A, Scenario B, and Scenario C.
6. Two-to-three page feasibility memo.
7. Small MATLAB-ready sample input.

## Validation Rules

- Do not edit files under `reference/`.
- Do not commit raw data, generated data, logs, or large binary outputs.
- Every raw data source must have source URL, download date, vintage, and coverage.
- Every country and sector mapping must be traceable to a documented concordance.
- Every model-facing moment must specify whether it supports Scenario A, Scenario B, or Scenario C.
- Scenario C must be labeled as an upper-bound proxy, not as a structural entry model.
- Every model input must pass dimension and ordering checks before MATLAB execution.

## Stop Conditions

Do not proceed to full model migration if:

- connector rankings are unstable across reasonable exposure definitions;
- trade rerouting has no production-side support from AMNE, value added, or related evidence;
- Scenario C cannot be disciplined by fDi Markets, FDI, BEA/AMNE, or production-side evidence without double counting Scenario B;
- country-sector concordances cannot be made transparent;
- model inputs cannot be generated without hard-coded country indices.
