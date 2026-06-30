# Connector Economies and the Hidden Cost of Geoeconomic Fragmentation

This repository starts a JMP-oriented project on whether connector economies mitigate or disguise the welfare costs of geoeconomic fragmentation.

The first phase is deliberately narrow: build the project structure, define the research design, document the data route, and specify how the existing `reference/EL_replication` model will be reused. The repository does not yet run a full structural counterfactual.

## Research Question

When direct trade and multinational production links between geopolitical blocs weaken, do connector economies such as Mexico, Vietnam, India, and Turkey absorb real production relocation, or do they mainly reroute trade in ways that preserve hidden supply-chain dependence?

## Working Hypothesis

Connector economies partially cushion the direct welfare losses from fragmentation, but this cushioning is costly and incomplete. The key empirical distinction is between:

- real production relocation through foreign affiliate activity and domestic value added;
- trade rerouting or transshipment with limited local production;
- general-equilibrium propagation through input-output linkages and multinational production.

## Current Project Stage

Phase 1 setup only:

- define the JMP framing and first-stage feasibility tests;
- keep `reference/` as read-only upstream material;
- use public data first: OECD ICIO, OECD AMNE, and Comtrade or BACI;
- prepare a clean path for reusing the MATLAB model structure from the reference package.

## Repository Layout

| Path | Purpose |
|---|---|
| `docs/` | Research design, reference model map, and setup checklist. |
| `data/` | Data inventory and tracked README files only. Raw and generated data are ignored. |
| `code/data_build/` | Future data construction code for ICIO, AMNE, and trade data. |
| `code/model_core/` | Future reusable MATLAB model core derived from the reference code. |
| `code/analysis/` | Future descriptive evidence and first-stage validation scripts. |
| `output/` | Regenerable figures, tables, logs, and memos. |
| `reference/` | Local read-only reference package; ignored by git. |

## Reproduction Status

There is no executable project pipeline yet. The first executable milestone will be a small-sample data build that produces MATLAB-ready inputs with the same conceptual structure as the reference package's `tomatlab/*.csv` files.

## Immediate Next Milestones

1. Download and document current OECD ICIO and OECD AMNE public data.
2. Choose Comtrade or BACI for the first trade rerouting exercise.
3. Build a connector-country ranking table using public data.
4. Produce one descriptive figure showing direct bloc-to-bloc decline and third-country rerouting.
5. Create a small MATLAB-ready sample to test country-sector ordering before migrating model code.
