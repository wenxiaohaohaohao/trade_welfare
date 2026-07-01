# Connector Economies and the Hidden Cost of Geoeconomic Fragmentation

This repository starts a JMP-oriented international trade project on connector economies: countries that expand as intermediaries or production locations when direct economic links between geopolitical blocs weaken.

The project is built from an existing structural reference package but is not a replication project. The reference package gives the core trade + multinational production + input-output model. The new project asks a different question and needs new data, new country definitions, new connector measures, and a new empirical validation layer before the model can be used credibly.

## Current Data Notes / 当前数据说明

- BEA U.S. MNE MOFA country-industry tables have been checked for `Mexico x Transportation equipment`, 2020-2022. The verified cells are not suppressed and can be used to fill the post-2020 OECD Analytical AMNE gap for this North America production-side moment. See `data/bea_mne_mexico_transportation_equipment_2020_2022.md`.
- 已核实 BEA U.S. MNE MOFA 的 `Mexico x Transportation equipment` 2020-2022 行业级数据。核心指标没有 `(D)` suppression，可用于补 OECD Analytical AMNE 2020 年之后的缺口，并作为 North America extension 中 MP relocation / affiliate expansion 的校准依据。详见 `data/bea_mne_mexico_transportation_equipment_2020_2022.md`。

## 1. Project In One Paragraph

When direct trade and multinational production links between geopolitical blocs weaken, third countries can appear to "connect" the blocs. This can mean real production relocation, or it can mean trade rerouting and transshipment with little local value added. The project asks whether connector economies actually mitigate the welfare costs of geoeconomic fragmentation, or whether they mainly hide continued dependence through indirect routes. The empirical work will first identify connector countries and distinguish production relocation from gross trade rerouting. The structural work will then use a multi-country, multi-sector general-equilibrium model with trade, multinational production, and input-output linkages to quantify welfare effects.

## 2. Main Research Question

How much do connector economies mitigate the welfare costs of geoeconomic fragmentation, and does this mitigation come from real production relocation or from trade rerouting with limited local value added?

The core distinction is:

- **real relocation**: connector countries expand production, foreign affiliate activity, value added, or local sourcing;
- **rerouting**: connector countries expand gross exports or imports but do not show comparable production-side expansion;
- **hidden dependence**: the final destination imports from a connector, but the connector remains highly dependent on inputs from the original source bloc.

## 3. Why This Can Be A JMP

The project is not just about documenting trade diversion. Its intended contribution is to combine three elements:

1. a new empirical measurement of connector economies in a fragmentation episode;
2. a distinction between real production relocation and pure rerouting;
3. a welfare accounting framework that includes trade, multinational production, and input-output propagation.

This matters for policy because friend-shoring and decoupling can look successful in gross trade data while still preserving hidden dependence or raising real resource costs. For a top-field international trade audience, the project must therefore show both a new fact and a disciplined welfare interpretation.

## 4. The Reference Material

The local folder `reference/` contains the paper and replication package for:

> Xiayi Du and Zi Wang, "Multinationals, global value chains, and the welfare impacts of economic sanctions," Economics Letters, 2022.

The reference paper studies sanctions against Russia using a 44-economy, 34-sector model with trade, multinational production (MP), and input-output linkages. It is useful because it already has the type of structural model this project needs. It is insufficient because it is designed for Russia sanctions, uses older data, and does not measure connector economies.

The reference folder is treated as read-only source material. New project code should live under `code/`, not inside `reference/`.

## 5. What We Inherit From The Reference Code

This section lists exactly which settings or structures from the reference code are being used in the new project.

### 5.1 Model Class

The project inherits the reference model's basic environment:

- multi-country;
- multi-sector;
- trade linkages;
- multinational production linkages;
- input-output linkages;
- general-equilibrium welfare accounting.

In the reference code, this is implemented with country-sector arrays. The original setup fixes:

- `m.N = 44`: number of economies;
- `m.J = 34`: number of sectors;
- `m.JT = 18`: number of tradable goods sectors.

For this project, we inherit the array-based model structure but not these exact dimensions as permanent constants. The new data may require a different country set, sector aggregation, or time window. Therefore future code should read these values from country and sector mapping files rather than hard-coding them.

### 5.2 Data Interface To MATLAB

The reference package creates MATLAB-ready CSV files under its `tomatlab/` folder. This project will preserve the same conceptual input interface where possible because it lowers model-migration risk.

The inherited input concepts are:

| Reference input | Economic meaning | Future project use |
|---|---|---|
| `mpshare_2016.csv` | MP share by origin, production location, and sector | Foreign affiliate / MP exposure and relocation channel. |
| `trshare_2018.csv` | Trade share by origin, destination, and sector | Trade rerouting and sourcing shares. |
| `X_2018.csv` | Total expenditure by destination and sector | Country-sector expenditure baseline. |
| `va_2018.csv` | Final demand shares and value-added shares | Final demand and production-side calibration. |
| `IO_2018.csv` | Input-output shares by country and sector pair | Propagation through intermediate input linkages. |
| `tariff_2019.csv` | Bilateral tariff by sector | Baseline trade-cost component. |
| `cal_elasticity.csv` | Sectoral `sigma`, `theta`, and `rho` | Demand, trade, and MP elasticity parameters. |

The new project should generate analogous files under `data/model_inputs/`, but using current public data rather than copying the reference CSVs.

### 5.3 Four-Dimensional Flow Object

The reference model imputes a four-dimensional object:

`X_4d(i, ell, n, j)`

where:

- `i` is the origin country of the firm;
- `ell` is the production country;
- `n` is the destination market;
- `j` is the sector.

This object is central for connecting MP, trade, and final demand. The new project should keep this structure because connector economies are exactly about whether third countries enter as production locations, trade routes, or both.

The relevant reference files are:

- `main_impute_triflows.m`: reads MP shares, trade shares, expenditure, IO shares, tariffs, and elasticities;
- `impute_tri.m`: imputes `X_4d` and simulated MP/trade shares.

### 5.4 Equilibrium Solver

The reference files `eqm_iter.m` and `eqm_update.m` implement the equilibrium iteration. The project will reuse this solver logic after refactoring it into `code/model_core/`.

The inherited logic is:

- initialize wage, price, and expenditure changes;
- update trade and MP shares after shocks;
- update country-sector prices, wages, expenditures, profits, and tariff revenue;
- iterate until convergence.

The new version must remove project-specific assumptions from the reference scripts. In particular, it must not rely on fixed country indices from the Russia application.

### 5.5 Shock Representation

The reference counterfactuals represent shocks through:

- `htau`: changes in trade costs;
- `hgamma`: changes in MP costs;
- `tTar`: tariff levels.

In the Russia sanction scripts, cutting a link is approximated by setting the relevant `htau` and/or `hgamma` entries to a very large value such as `9999`.

This project will inherit the idea that fragmentation can be represented as changes in trade costs and MP costs. It will not inherit the hard-coded Russia-specific implementation. Future scenarios should be defined by configuration files:

- source bloc;
- destination bloc;
- connector countries;
- sectors;
- shock year;
- baseline year;
- trade-cost shock;
- MP-cost shock.

### 5.6 Welfare Decomposition

The reference file `wel_decomp.m` is especially important. It decomposes welfare changes into:

| Component | Interpretation for this project |
|---|---|
| `GFF` | Gains or losses from access to foreign final goods. |
| `GFI` | Gains or losses from access to foreign intermediate inputs. |
| `GOF` | Gains or losses from offshoring and MP access. |
| `SEC` | Sectoral input-output linkage channel. |
| `MS` | Market size effect. |
| `PT` | Profit and tariff revenue channel. |

For this project, the most important components are likely `GFI`, `GOF`, and `SEC`. If connector countries matter, they should change the cost of accessing foreign intermediates, the feasibility of foreign affiliate production, and the propagation of shocks through input-output linkages.

### 5.7 Baseline Adjustment

The reference file `main_cab.m` performs a baseline current-account adjustment before counterfactual simulations. The new project should keep this as a conceptual step: before comparing counterfactuals, the model must have a coherent baseline equilibrium. The exact adjustment routine should be reviewed after the new data interface is built.

## 6. What The Reference Material Does Not Solve

The reference package is useful but not sufficient for this project. The main gaps are listed below.

### 6.1 It Studies Russia Sanctions, Not Connector Economies

The reference counterfactual is built around Russia. Its scenario scripts hard-code specific country indices such as Russia, China, the United States, and a fixed set of sanctioning or non-sanctioning countries.

This project needs a flexible design:

- geopolitical blocs must be defined externally;
- connector candidates must be measured from data, not assumed;
- country roles must be allowed to change by episode, sector, and year;
- scenarios must not depend on country index numbers embedded in MATLAB scripts.

### 6.2 It Does Not Measure Rerouting

The reference model can evaluate the welfare effects of a given shock. It does not by itself identify whether trade is being rerouted through third countries.

This project needs a separate empirical layer that constructs:

- direct bloc-to-bloc trade changes;
- third-country import growth from the source bloc;
- third-country export growth to the destination bloc;
- sector-level connector exposure;
- measures that distinguish rerouting from true production relocation.

This requires Comtrade or BACI-style bilateral trade data at a more detailed product level than the reference model inputs.

### 6.3 It Does Not Distinguish Real Production Relocation From Transshipment

The reference package uses MP shares and input-output data, but it was not designed to decide whether a connector country's rise reflects actual production or merely pass-through trade.

This project needs production-side evidence, such as:

- OECD AMNE foreign affiliate activity;
- value added and gross output from ICIO;
- domestic production or employment by sector where available;
- possibly FDI, firm-level, or plant-level data if public aggregate data are too weak.

Without this layer, the project would risk becoming a gross-trade rerouting exercise rather than a JMP-level contribution.

### 6.4 The Data Vintage Is Not Enough

The reference package uses:

- AMNE data from 2016;
- ICIO trade and IO data from 2018;
- tariffs from 2019;
- a pre-2022 baseline designed for Russia sanctions.

The connector-economy question is about recent geoeconomic fragmentation and supply-chain reorganization. The project therefore needs updated data where available and a clear rule for combining:

- structural baseline years;
- shock years;
- post-shock descriptive evidence;
- data releases with different coverage and lags.

### 6.5 It Has No Connector-Country Definition

The reference model has countries and sectors, but it does not define a connector economy. This project needs a measurable definition.

A first-pass connector measure should combine:

1. increased imports from a source bloc;
2. increased exports to a destination bloc;
3. sectoral overlap between those flows;
4. production-side support from AMNE, value added, or gross output;
5. persistence across years rather than a one-year spike.

The definition should be tested for stability before entering the structural model.

### 6.6 It Has No Country-Group Configuration Layer

The reference scripts encode scenarios directly in MATLAB code. That is not acceptable for this project because collaborators need to inspect and revise country groups and assumptions.

Future implementation should add configuration files under `configs/` for:

- bloc membership;
- connector candidate lists;
- sector lists;
- baseline and shock years;
- shock intensity;
- scenario names and output labels.

### 6.7 It Has No Model Input Validation Layer

The reference code assumes that the inputs have the correct order and dimensions. For this project, that is risky because the data will be rebuilt from multiple sources.

Before running MATLAB, the new pipeline must validate:

- country ordering;
- sector ordering;
- missing countries or sectors;
- whether all country-sector pairs exist;
- whether shares sum correctly;
- whether all arrays match the expected dimensions;
- whether connector definitions match the model country list.

### 6.8 The Gravity Calibration May Need Updating

The reference `cal_gravity.do` estimates sector-level trade elasticities using tariff variation and gravity controls. This is useful as a template but not automatically sufficient.

For this project, the calibration must be reconsidered because:

- the country set may differ;
- the sector aggregation may differ;
- the time window may differ;
- recent fragmentation shocks may involve non-tariff barriers, sanctions, export controls, or policy uncertainty, not only tariffs;
- connector-country behavior may require separate sensitivity checks for elasticities.

### 6.9 It Does Not Provide An Identification Strategy

The reference package is a structural counterfactual exercise. It does not establish the empirical fact that connector economies are responding to fragmentation shocks.

This project needs first-stage evidence before the model:

- Which countries become connectors?
- Which sectors drive the connector pattern?
- Is the pattern stable across definitions?
- Is the result driven by one country, one product, or one year?
- Is there production-side evidence behind the trade pattern?

The structural model should be used only after these facts are established.

## 7. First-Stage Empirical Plan

The first empirical stage should produce four outputs.

### 7.1 Connector Ranking Table

Rank countries by sector-level connector activity. A country should rank high if it simultaneously increases:

- imports from the source bloc;
- exports to the destination bloc;
- production-side activity in the same or related sectors.

### 7.2 Rerouting Figure

Produce a figure showing:

- decline in direct bloc-to-bloc flows;
- increase in source-bloc-to-connector flows;
- increase in connector-to-destination-bloc flows.

This figure should be produced at aggregate and sector levels.

### 7.3 Production-Side Validation Table

For the main connector candidates, check whether trade growth is accompanied by:

- AMNE affiliate activity;
- value added;
- gross output;
- employment or investment if available.

The purpose is to identify whether connectors are production locations or mainly trade routes.

### 7.4 Small MATLAB-Ready Sample

Build a small sample with a limited country-sector set and export MATLAB-ready inputs similar to the reference `tomatlab/` files. This sample should test the interface before migrating the full model.

## 8. Data Plan

The first version uses public data.

| Source | Role in the project |
|---|---|
| OECD ICIO | Input-output structure, final demand, gross output, value added, country-sector baseline. |
| OECD AMNE | Foreign affiliate activity and MP-related production relocation. |
| Comtrade or BACI | Bilateral trade rerouting and product-level connector measures. |
| WTO / tariff data | Baseline tariffs or policy-cost controls if needed. |
| Reference replication data | Only for understanding the model interface and sanity checks. |

The project should not copy reference data into the new pipeline as final data. Reference data may be used for sanity checks and interface tests only.

## 9. Repository Structure

| Path | Purpose |
|---|---|
| `README.md` | This collaborator-facing overview. |
| `docs/research_design.md` | Research question, mechanism, feasibility tests, and risks. |
| `docs/reference_model_map.md` | Detailed map from reference code to future model-core code. |
| `docs/data_source_log.md` | Data-source registry and download log. |
| `docs/phase1_feasibility_memo_template.md` | Template for deciding whether the project has enough first-stage signal. |
| `configs/` | Future country group, connector definition, sector mapping, and scenario files. |
| `code/data_build/` | Future scripts for ICIO, AMNE, and trade data construction. |
| `code/analysis/` | Future scripts for connector rankings, figures, and descriptive validation. |
| `code/model_core/` | Future MATLAB model code migrated from the reference package. |
| `data/` | Data documentation and ignored data folders. |
| `output/` | Regenerable tables, figures, logs, and memos. |
| `reference/` | Local read-only reference materials; ignored by git. |

## 10. Current Status

This repository currently contains project documentation and setup files only. It does not yet include:

- downloaded OECD ICIO or AMNE data;
- Comtrade or BACI data;
- new Stata, Python, or MATLAB data-build scripts;
- migrated model-core MATLAB functions;
- executable counterfactual scenarios.

This is intentional. The next task is to build the first empirical data layer, not to run the full structural model immediately.

## 11. Immediate Next Steps

1. Download and document current OECD ICIO and OECD AMNE data in `docs/data_source_log.md`.
2. Decide whether Comtrade or BACI is better for the first rerouting exercise.
3. Build a transparent country and sector mapping.
4. Construct the first connector ranking table.
5. Produce the first rerouting figure.
6. Validate whether trade rerouting is accompanied by production-side evidence.
7. Build a small MATLAB-ready sample to test compatibility with the reference model interface.
8. Only after these checks, migrate `eqm_iter.m`, `eqm_update.m`, `wel_decomp.m`, and related model-core functions into `code/model_core/`.

## 12. Decision Rule For Moving To Structural Counterfactuals

Move to full model migration only if the first-stage evidence shows:

- connector rankings are stable across reasonable definitions;
- direct bloc-to-bloc decline and third-country expansion are economically meaningful;
- at least one production-side source supports real relocation for key connectors;
- country-sector concordances are transparent;
- model inputs can be generated without hard-coded country indices;
- welfare channels can be reported separately for direct fragmentation, connector mitigation, MP, and IO propagation.

If these conditions fail, the project should either narrow to a specific country-sector episode or remain at the descriptive validation stage.
