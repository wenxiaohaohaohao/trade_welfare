# Phase 1 Setup Checklist

## Completion Standard

Phase 1 setup is complete when the repository has a clean project skeleton, research design, data route, and reference-model reuse rule. It does not require a full data build or MATLAB counterfactual.

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
4. Two-to-three page feasibility memo.
5. Small MATLAB-ready sample input.

## Validation Rules

- Do not edit files under `reference/`.
- Do not commit raw data, generated data, logs, or large binary outputs.
- Every raw data source must have source URL, download date, vintage, and coverage.
- Every country and sector mapping must be traceable to a documented concordance.
- Every model input must pass dimension and ordering checks before MATLAB execution.

## Stop Conditions

Do not proceed to full model migration if:

- connector rankings are unstable across reasonable exposure definitions;
- trade rerouting has no production-side support from AMNE, value added, or related evidence;
- country-sector concordances cannot be made transparent;
- model inputs cannot be generated without hard-coded country indices.
