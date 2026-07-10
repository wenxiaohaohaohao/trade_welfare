# Research Design

## Title

Connector Economies and the Hidden Cost of Geoeconomic Fragmentation

## Motivation

Recent fragmentation is not only a bilateral trade story. When direct links between geopolitical blocs weaken, third countries can expand as intermediaries, exporters, or production locations. A JMP version of this project should ask whether these connector economies create real productive reallocation or mostly re-label supply-chain dependence through rerouting.

The contribution must go beyond documenting trade diversion. The project should quantify how connector economies change welfare losses once trade, multinational production, and input-output linkages are considered jointly. The main welfare output should be a scenario-bound matrix: Scenario A is trade-only connector access, Scenario B is incumbent MP-intensive reallocation, and Scenario C is an upper-bound proxy for total MP adjustment disciplined by FDI and production-side expansion evidence.

## Primary Research Question

How much do connector economies mitigate the welfare costs of geoeconomic fragmentation, and how does the mitigation differ across trade-only rerouting, incumbent MP-intensive reallocation, and an upper-bound total MP-adjustment scenario?

## Sub-Questions

1. Which countries become connectors when direct bloc-to-bloc trade and MP links weaken?
2. Is connector activity associated with increased local production and foreign affiliate activity, or only increased gross trade flows?
3. How much of the apparent mitigation survives in a trade + MP + IO general-equilibrium model?
4. How wide is the welfare interval between the trade-only lower bound, the incumbent MP baseline, and the total MP-adjustment upper-bound proxy?

## Mechanism

The mechanism has four layers:

1. A fragmentation shock raises bilateral trade costs and/or MP costs between geopolitical blocs.
2. Direct bloc-to-bloc flows fall.
3. Connector countries expand as trade partners, production locations, or both.
4. Welfare effects depend on whether connectors lower effective sourcing costs or merely add a costly intermediate path.
5. External evidence on new projects, FDI, affiliate activity, and production expansion does not create an entry block in the model, but it can discipline an upper-bound `hgamma` scenario.

The empirical work must separate three outcomes:

- **direct decoupling**: reduced direct trade or MP between exposed blocs;
- **connector mitigation**: substitution through third countries;
- **hidden dependence**: continued reliance on original bloc inputs through indirect routes.

## Phase 1 Feasibility Tests

The first phase should not estimate the full model. It should answer whether the project has enough empirical signal for a JMP.

| Test | Required Output | Pass Condition |
|---|---|---|
| Connector ranking | Country-sector ranking table | Stable connectors across at least two exposure definitions. |
| Trade rerouting | Descriptive figure | Direct bloc decline and third-country expansion move in opposite directions. |
| Production relocation | AMNE or value-added evidence | Connector activity is not explained only by gross exports. |
| Scenario discipline | A/B/C structural moment table | Evidence maps cleanly to Scenario A, Scenario B, and Scenario C without treating entry as endogenous. |
| Model compatibility | Small MATLAB-ready sample | Country-sector ordering and dimensions match the model interface. |

## Data Strategy

The first version uses public data only:

- OECD ICIO for country-sector IO structure, final demand, gross output, and value added.
- OECD AMNE for foreign affiliate activity and MP-related intensive reallocation moments.
- BEA U.S. MNE, Mexico FDI, and fDi Markets for post-2020 nearshoring evidence and Scenario C discipline.
- Comtrade or BACI for bilateral trade rerouting and HS-to-sector aggregation.

The preferred time window is 2018-2024 where available. If ICIO or AMNE availability ends earlier, use the latest common year for structural calibration and newer trade data for descriptive rerouting evidence.

## Model Strategy

The reference model provides the structural backbone:

- multi-country, multi-sector general equilibrium;
- trade costs, MP costs, and tariffs;
- input-output linkages;
- welfare decomposition into GFF, GFI, GOF, SEC, MS, and PT.

The new project should not hard-code Russia or China indices. Country groups, connector countries, and shock scenarios must be read from mapping/config files in a later implementation phase.

The model strategy should report:

| Scenario | Interpretation |
|---|---|
| Scenario A | Trade-only connector lower bound with `hgamma = 1`. |
| Scenario B | Incumbent MP-intensive baseline disciplined by AMNE/affiliate activity. |
| Scenario C | Upper-bound proxy for total MP adjustment disciplined by FDI, fDi Markets, affiliate expansion, and production-side expansion. |

Scenario C is not a fixed-cost entry model. Its role is to let extensive-margin evidence discipline a welfare upper bound without claiming structural identification of entry-margin welfare.

## FINER Assessment

| Criterion | Score | Rationale |
|---|---:|---|
| Feasible | 4 | Public ICIO, AMNE, and trade data can support the first-stage evidence and model inputs. |
| Interesting | 5 | The distinction between real relocation and rerouting is central to current fragmentation debates. |
| Novel | 4 | The combination of connector-country measurement with trade + MP + IO welfare accounting is stronger than a simple diversion study. |
| Ethical | 5 | The project uses aggregate public economic data and does not involve human subjects. |
| Relevant | 5 | The result speaks directly to friend-shoring, decoupling, sanctions, and supply-chain resilience. |

## Main Risks

- Connector activity may reflect transshipment or reporting artifacts rather than real production relocation.
- AMNE coverage may be too coarse or lagged for recent shocks.
- Scenario C may be over-interpreted unless it is consistently labeled as an upper-bound proxy rather than an entry model.
- Country-sector concordances may dominate the measured results.
- A full structural model could become too broad for a JMP if the first-stage empirical fact is weak.

## Decision Rule For Proceeding

Proceed to model migration only if the first-stage evidence shows:

1. stable connector-country rankings;
2. trade rerouting that is economically meaningful, not just statistically visible;
3. at least one production-side measure consistent with relocation or affiliate expansion;
4. a clear mapping from data outputs to Scenario A/B/C assumptions;
5. a clear mapping from data outputs to the reference model's MATLAB input structure.
