# Connector Economies and the Hidden Cost of Geoeconomic Fragmentation

This repository starts a JMP-oriented international trade project on the welfare value of connector economies: countries that expand as intermediaries or production locations when direct economic links between geopolitical blocs weaken.

The project is built from an existing structural reference package but is not a replication project. The reference package gives the core trade + multinational production + input-output model. Recent empirical work has already studied whether connector countries reflect trade reallocation or trade rerouting. This project therefore should not claim that distinction as its main novelty. The intended contribution is to move from connector-country facts to structural welfare accounting: how much connectors mitigate fragmentation losses, and through which channels.

## Current Data Notes / 当前数据说明

- BEA U.S. MNE MOFA country-industry tables have been checked for `Mexico x Transportation equipment`, 2020-2022. The verified cells are not suppressed and can be used to fill the post-2020 OECD Analytical AMNE gap for this North America production-side moment. See `data/bea_mne_mexico_transportation_equipment_2020_2022.md`.
- fDi Markets is available through the user's access. It should now be treated as the primary project-level source for the model-external extensive-margin evidence section, especially greenfield manufacturing projects in Mexico and other connector economies after 2018.
- The current data plan is: OECD ICIO Extended for IO and ownership-split baseline objects through 2022; OECD Analytical AMNE for ownership-split multinational-production moments through 2020; BEA U.S. MNE, Mexico FDI, and fDi Markets to bridge the 2021-2024 nearshoring period; BACI and Section 301 tariff files for product-level trade shocks.
- 已核实 BEA U.S. MNE MOFA 的 `Mexico x Transportation equipment` 2020-2022 行业级数据。核心指标没有 `(D)` suppression，可用于补 OECD Analytical AMNE 2020 年之后的缺口，并作为 North America extension 中 MP relocation / affiliate expansion 的校准依据。详见 `data/bea_mne_mexico_transportation_equipment_2020_2022.md`。
- fDi Markets 这里已经可得。它应作为模型外 extensive-margin evidence section 的核心项目级数据，重点整理 2018 年之后 Mexico 和其他 connector economies 的 greenfield manufacturing projects。
- 当前数据策略是：用 OECD ICIO Extended 构造 2022 年以前的 IO 和 ownership-split 基准对象；用 OECD Analytical AMNE 构造 2020 年以前的 multinational-production ownership moments；用 BEA U.S. MNE、Mexico FDI 和 fDi Markets 补 2021-2024 年 nearshoring 证据；用 BACI 和 Section 301 tariff files 构造产品层面贸易冲击。

## 1. Project In One Paragraph

When direct trade and multinational production links between geopolitical blocs weaken, third countries can appear to "connect" the blocs. Existing empirical work already shows that this can mean real production reallocation in some cases and trade rerouting or transshipment in others. This project asks the next question: conditional on these connector channels existing, how much do they mitigate the welfare costs of geoeconomic fragmentation? The empirical layer will be used for validation, calibration, country scope, and shock discipline. The core contribution should come from a multi-country, multi-sector general-equilibrium model with trade, multinational production, and input-output linkages.

## 2. Main Research Question

How much do connector economies mitigate the welfare costs of geoeconomic fragmentation, and how much of that mitigation comes from trade rerouting, multinational production relocation, and input-output propagation?

The core distinction is:

- **real relocation**: connector countries expand production, foreign affiliate activity, value added, or local sourcing;
- **rerouting**: connector countries expand gross exports or imports but do not show comparable production-side expansion;
- **hidden dependence**: the final destination imports from a connector, but the connector remains highly dependent on inputs from the original source bloc.

## 3. Why This Can Be A JMP

The project is not just about documenting trade diversion. After Schulze and Xin (2025), documenting and empirically disentangling trade reallocation from trade rerouting is no longer enough as the main contribution. The intended contribution must combine three different elements:

1. a structural welfare accounting framework for connector economies;
2. a decomposition of connector mitigation into trade rerouting, multinational production relocation, and input-output propagation;
3. a disciplined empirical validation and calibration layer that uses existing connector facts without treating them as the paper's main novelty.

This matters for policy because friend-shoring and decoupling can look successful in gross trade data while still preserving hidden dependence or raising real resource costs. For a top-field international trade audience, the project must now show more than a new fact: it needs a credible counterfactual that quantifies the welfare value and residual cost of connector economies.

### 3.1 Closest Existing Empirical Paper And Revised Positioning

The closest currently identified paper is:

> Tatjana Schulze and Weining Xin, "Demystifying Trade Patterns In A Fragmenting World," IMF Working Paper WP/25/129, June 2025.

This paper directly overlaps with the original empirical plan. It studies connector countries after the U.S.-China trade tensions, distinguishes **trade reallocation** from **trade rerouting**, uses granular trade data, value-added measures from a multi-region input-output database, greenfield FDI evidence, and a synthetic control design. Its main sample covers six Asian economies: India, Indonesia, Malaysia, the Philippines, Thailand, and Vietnam. Its main conclusion is that Vietnam shows the clearest evidence of trade reallocation and domestic value-added expansion in strategic sectors, while evidence for the other five economies is much weaker. It also finds no broad evidence that Vietnam mainly acted as a transshipment channel for Chinese exports to the U.S.

This changes the project's positioning. The new paper should not present the following as main contributions:

- proving that connector countries exist;
- showing that gross trade can hide supply-chain dependence;
- distinguishing trade reallocation from trade rerouting in Asian connector economies;
- using value-added data and synthetic control to test the Vietnam case.

Those are now part of the literature base. The remaining credible contribution is to ask a different question:

> Given that connector channels exist, what is their general-equilibrium welfare value, and how does that value differ between trade-only rerouting, multinational-production relocation, and input-output network propagation?

The project should therefore use Schulze and Xin (2025) as a benchmark and then move beyond it in three directions:

1. **Welfare accounting**: quantify how much connector economies reduce fragmentation losses, rather than only identifying whether trade reallocation occurred.
2. **MP channel**: use the reference model's multinational production structure to separate production-location changes from trade-cost changes.
3. **North American extension**: add Mexico and possibly Canada as a separate connector environment, because Schulze and Xin focus on Asian economies and do not make Mexico the central case.

## 4. The Reference Material

The local folder `reference/` contains the paper and replication package for:

> Xiayi Du and Zi Wang, "Multinationals, global value chains, and the welfare impacts of economic sanctions," Economics Letters, 2022.

The reference paper studies sanctions against Russia using a 44-economy, 34-sector model with trade, multinational production (MP), and input-output linkages. It is useful because it already has the type of structural model this project needs. It is insufficient because it is designed for Russia sanctions, uses older data, and does not measure connector economies.

The reference folder is treated as read-only source material. New project code should live under `code/`, not inside `reference/`.

### 4.1 Technical Check: How Du-Wang Models The MP Margin

The core model risk is whether Du-Wang can be used directly for this project's MP channel. The check is clear: Du-Wang models MP through an **iceberg MP cost**, not through a Tintelnot-style fixed-cost entry margin.

The paper states that a firm from origin country `i` can produce in country `ell` subject to an iceberg MP cost `gamma_iell^j >= 1`, with `gamma_ii^j = 1`. The firm's unit cost contains `gamma_iell^j` multiplied by the trade-cost term `kappa_elln^j`. The replication code implements the same structure: `eqm_update.m` constructs `hxi_4d` by multiplying `hgamma`, `hkappa`, wage changes, and intermediate-input price changes, then updates the MP and sourcing shares through `hpsi_4d` and `hlam_3d`.

This means `hgamma` should be interpreted as a change in MP variable cost, or a change in the effective cost of producing through a foreign affiliate location. It should **not** be interpreted as an entry fixed cost, an affiliate-entry threshold, or a firm-count relocation object. The reference code has no fixed-cost entry equation, no endogenous affiliate count, no binary entry decision, and no plant-level relocation margin.

The implication for this project is:

| Possible route | Assessment |
|---|---|
| Use Du-Wang with project-specific scenario/config refactoring | Recommended first version. It already has trade, MP, IO linkages, and welfare decomposition. |
| Add a modest project-specific patch to discipline `hgamma` with AMNE, BEA MNE, FDI, or production-side moments | Needed. The size of MP-cost shocks must be disciplined by evidence rather than chosen arbitrarily. |
| Switch immediately to a BHLP/Bonadio-style framework with a new MP layer | Not recommended for the first version unless the project abandons the Du-Wang sufficient-statistics structure. It would increase model-building burden sharply. |
| Build a Tintelnot-style fixed-cost entry model | Only appropriate if the paper's core question becomes affiliate entry or plant-count relocation, which requires stronger micro or firm-level evidence. |

Therefore, Du-Wang is usable as the first structural backbone for connector welfare accounting, but only with a narrow interpretation: it can quantify welfare effects of trade-cost and MP-cost shocks. It cannot by itself prove that firms entered a connector country or that plants physically relocated there. Any claim about real production relocation must come from the empirical validation layer and then enter the model as a disciplined `hgamma` scenario.

### 4.2 Model Boundary: Intensive Margin Versus New Entry

The paper should not claim that the Du-Wang model explains new firms entering Mexico after Section 301. The main model should be positioned as **intensive-margin welfare accounting**. It can answer how welfare changes when trade costs and effective MP variable costs change across already represented country-sector links. It cannot endogenously explain a Chinese, U.S., Korean, Japanese, or European firm opening a new plant in Mexico.

The two project mechanisms remain valid if they are stated carefully:

| Mechanism | How the model can handle it | What remains outside the model |
|---|---|---|
| Trade rerouting / indirect sourcing | Changes in `htau`, sourcing shares, foreign intermediates, and IO propagation. | Product-level evidence that rerouting actually occurred. |
| MP relocation / nearshoring | Changes in `hgamma` that shift production intensity toward connector locations already represented in the MP-share system. | New affiliate entry, new plant announcements, and plant-count changes. |

This does not make the project nonviable. It changes the paper's contract with the reader. The structural model quantifies the welfare implications of connector access and effective MP-cost changes; the empirical section validates whether the nearshoring narrative has extensive-margin support.

For a JIE-level paper, this boundary is acceptable only if the empirical and counterfactual discipline is strong. The first version should therefore add an explicit **extensive-margin evidence section outside the model**. That section should use fDi Markets, BEA MNE, AMNE, FDI, value added, employment, or investment data to show whether Mexico and other connector economies experienced new projects or affiliate expansion in the relevant sectors. The evidence should be used to motivate and discipline the `hgamma` scenarios, not to claim that Du-Wang endogenously generates entry.

The recommended wording is:

> The structural model captures intensive reallocation across existing MP links. It does not endogenize entry of new affiliates or plants. We therefore treat greenfield FDI and new project announcements as model-external evidence that validates the nearshoring mechanism and helps discipline MP-cost counterfactuals.

Moving to a full Tintelnot-style fixed-cost foreign-investment model should be reserved for a different version of the paper where affiliate entry itself is the central research question. That path would require stronger firm-level or project-level data and a substantially new model block.

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

The specific reference counterfactuals are:

| Reference script | Shock design | Interpretation | Output |
|---|---|---|---|
| `main_cf_RUS_sanction.m` | For every sector, both `htau` and `hgamma` are set to `9999` for bilateral links between Russia and almost all other economies; Russia domestic links remain open; China-Russia links remain open. | Trade and MP isolation of Russia, with China treated as an exempt partner. | `RUS_sanction_TRMP.csv` |
| `main_cf_RUS_sanction_notrade.m` | Same Russia link structure, but only `htau` is set to `9999`; `hgamma` remains at baseline. | Trade-only sanction shock. MP links are not directly cut. | `RUS_sanction_TR.csv` |
| `main_cf_RUS_sanction2.m` | Both `htau` and `hgamma` are cut for Russia links, but links with a broader exempt group remain open: China, Brazil, Indonesia, India, Mexico, ROW, Turkey, and Taiwan in the reference country order. | Trade and MP isolation of Russia with a wider non-sanction or connector-like outside set. | `RUS_sanction_TRMP2.csv` |
| `main_cf_RUS_sanction_notrade2.m` | Trade-only version of the broader-exempt-group scenario. | Trade-only isolation with outside links left open. | `RUS_sanction_TR2.csv` |

For the new connector-economy project, these scripts should be treated as a scenario template rather than a literal policy design. The Russia index `38`, China index `8`, and the hard-coded exempt-country list must be replaced by external country-group configuration files. The natural project-level counterfactual matrix is:

| New scenario | Shock object | Purpose |
|---|---|---|
| Baseline | `htau = 1`, `hgamma = 1`, `tTar = baseline tariffs` | Coherent pre-shock model equilibrium. |
| Direct fragmentation, no connectors | Increase `htau` and possibly `hgamma` on source-bloc to destination-bloc links. | Measures the welfare cost of direct decoupling. |
| Trade-only connector access | Keep or reduce connector-related `htau` while direct bloc links remain costly; leave `hgamma` unchanged. | Isolates gross trade rerouting through third countries. |
| MP relocation through connectors | Allow connector-related `hgamma` to remain open or improve, with matching trade access. | Measures real production relocation and foreign affiliate activity. |
| Full connector mitigation | Combine trade rerouting and MP relocation channels. | Quantifies how much connectors reduce fragmentation losses. |
| No-connector stress test | Raise both direct-bloc and connector-bloc barriers. | Shows residual welfare cost when third-country adjustment is unavailable. |

The first structural version should report welfare changes for each scenario and decompose them into direct fragmentation losses, connector mitigation, MP relocation, and input-output propagation. The reference package can already compute welfare decomposition after a shock; what it cannot do is define the connector countries or validate whether the connector channel is real rather than pure rerouting.

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

This project still needs an empirical layer before the model, but the role of that layer has changed after Schulze and Xin (2025). It should not be framed as the paper's main novelty. It should be used to verify the sample, discipline the shock, and calibrate the structural counterfactuals.

The required empirical questions are:

- Which countries become connectors?
- Which sectors drive the connector pattern?
- Do the patterns in the new data replicate or extend the existing IMF evidence?
- Does Mexico or another North American connector display a pattern not covered by the Asian sample?
- Which moments can discipline the size of trade-cost and MP-cost shocks in the structural model?
- Is there production-side evidence strong enough to justify an MP relocation scenario?

The structural model should be used only after these validation and calibration facts are established.

## 7. Empirical Validation And Calibration Plan

The first empirical stage should produce six outputs. These are not intended to be the paper's main contribution; they are needed to anchor the structural model in credible observed facts.

### 7.1 Connector Ranking Table

Rank countries by sector-level connector activity, but explicitly compare the ranking with Schulze and Xin (2025). A country should rank high if it simultaneously increases:

- imports from the source bloc;
- exports to the destination bloc;
- production-side activity in the same or related sectors.

### 7.2 Rerouting Figure

Produce a figure showing:

- decline in direct bloc-to-bloc flows;
- increase in source-bloc-to-connector flows;
- increase in connector-to-destination-bloc flows.

This figure should be produced at aggregate and sector levels. Its purpose is to discipline shock design and verify that the project sample captures the same fragmentation episode as the existing literature.

### 7.3 Production-Side Validation Table

For the main connector candidates, check whether trade growth is accompanied by:

- AMNE affiliate activity;
- value added;
- gross output;
- employment or investment if available.

The purpose is to determine whether the structural model should include a trade-only connector scenario, an MP relocation scenario, or both.

### 7.4 Small MATLAB-Ready Sample

Build a small sample with a limited country-sector set and export MATLAB-ready inputs similar to the reference `tomatlab/` files. This sample should test the interface before migrating the full model.

### 7.5 Structural Moment Table

Create a table that translates empirical facts into model moments:

- observed decline in direct bloc-to-bloc trade;
- observed increase in connector exports to the destination bloc;
- observed increase in connector imports from the source bloc;
- production-side expansion where available;
- FDI or foreign-affiliate activity where available;
- implied scenario choices for `htau` and `hgamma`.

This table is the bridge between the existing empirical literature and the new welfare counterfactual.

### 7.6 Extensive-Margin Evidence Table

Create a separate table for project-level or firm-entry evidence. This table should not be folded into the Du-Wang model as an endogenous entry outcome. Its role is to validate the nearshoring narrative and discipline MP-cost scenarios.

The table should include:

- greenfield project counts and announced investment by host country, origin country, sector, and year;
- BEA MNE or AMNE affiliate activity where available;
- FDI, employment, value added, or investment indicators in the same sectors;
- a flag for whether the evidence supports an MP-intensive scenario, a trade-only scenario, or only a narrative motivation.

The model-facing output is not an entry equation. It is a documented choice of `hgamma` scenarios and sensitivity bounds.

## 8. Data Plan

The first version can start from public data, but the evidentiary strength differs sharply across the project's three tasks: identifying trade rerouting, validating real production relocation, and computing welfare counterfactuals. Public data are strong enough for the first and third tasks. They are only partially sufficient for the second task unless they are supplemented by production-side and, ideally, firm-, plant-, or shipment-level evidence.

### 8.1 What Public Data Can Support

| Research object | Public-data status | Why |
|---|---|---|
| Direct bloc-to-bloc trade decline | Strong | BACI, UN Comtrade, and U.S. import data can measure whether U.S. imports from China fall at the product-country-year or product-country-month level. |
| Third-country rerouting | Strong | The same product-level trade data can test whether connector candidates increase imports from the source bloc and exports to the destination bloc in the same products or related sectors. |
| Hidden dependence on Chinese or East Asian inputs | Medium to strong | Product-level imports can be mapped to intermediate goods using BEC or sector concordances. This can show whether connector exports to the U.S. or EU are accompanied by increased sourcing from China or East Asia. |
| Real production relocation | Partial | OECD ICIO, OECD Analytical AMNE, BEA MNE data, FDI data, and national manufacturing statistics can validate sector-level production, value added, employment, investment, or foreign-affiliate expansion. They cannot by themselves prove that a specific firm moved a plant from China to Vietnam or Mexico. |
| Pure transshipment versus light assembly versus real local value added | Partial to weak | Aggregate public data can reject some simple transshipment stories if value added and employment rise, but it cannot cleanly separate relabeling, light assembly, and deep local production without firm-, plant-, or shipment-level data. |
| General-equilibrium welfare counterfactuals | Sufficient for a first structural version | OECD ICIO plus trade shares, elasticity parameters, tariffs, and the reference model's welfare decomposition can support counterfactuals. The key is that shock sizes should be estimated or disciplined by product-level evidence rather than chosen arbitrarily. |

The key interpretation is therefore not "public data prove relocation." A more defensible statement is: public data can establish a strong rerouting fact, can validate whether production-side aggregates move in the same direction, and can support welfare counterfactuals. Direct proof of firm-level relocation requires stronger data.

### 8.2 Core Available Data Sources

| Source | Role in the project | Concrete use |
|---|---|---|
| [OECD ICIO, including Extended ICIO](https://www.oecd.org/en/data/datasets/inter-country-input-output-tables.html) | Country-sector production and input-output structure | Build gross output, value added, final demand, intermediate-input linkages, and model baseline objects. The Extended ICIO is especially useful because it separately treats China and Mexico ownership/firm-type layers. |
| [OECD TiVA](https://www.oecd.org/en/data/datasets/trade-in-value-added.html), where useful | Value-added trade interpretation | Check whether gross trade rerouting corresponds to value-added exposure. |
| [OECD Analytical AMNE](https://www.oecd.org/en/data/datasets/multinational-enterprises-and-global-value-chains.html) / [AMNE](https://www.oecd.org/en/data/datasets/activity-of-multinational-enterprises.html) | Foreign-affiliate activity and multinational production | Validate whether connector countries show foreign-affiliate sales, employment, value added, or output expansion in relevant sectors. This is the main ownership-split source for disciplining `hgamma` through 2020. |
| [fDi Markets](https://www.fdimarkets.com/) | Greenfield FDI project evidence; access confirmed by the user | Build the model-external extensive-margin evidence table: new projects, source countries, destination locations, sectors, business activity, announced capex, and expected jobs. |
| [BACI](https://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=37) | Product-level bilateral trade | Build connector rankings, rerouting figures, source-bloc imports, destination-bloc exports, and sector-level overlap measures. BACI is preferred over DOTS or aggregate trade data because HS6 products map more cleanly to autos, electronics, medical devices, machinery, and components. |
| [UN Comtrade](https://comtradeplus.un.org/) | Product-level bilateral trade cross-check | Use as a robustness or cross-check source if BACI concordance or timing creates problems. |
| [U.S. Census USA Trade Online](https://usatrade.census.gov/) | High-resolution U.S. import evidence | Use U.S.-destination product-level data, ideally at monthly or HS10 detail where accessible, to validate U.S.-China tariff exposure and import substitution. |
| USTR Section 301 lists, [USITC HTS](https://hts.usitc.gov/), WITS / TRAINS, WTO, and related official tariff files | Policy shock measurement | Construct HS-level tariff and policy-cost shocks, especially for U.S.-China Section 301 products and other fragmentation episodes. |
| [BEA U.S. MNE data](https://www.bea.gov/data/intl-trade-investment/activities-us-multinational-enterprises-mnes) | U.S. multinational affiliate activity | Check whether U.S. firms' affiliate employment, sales, value added, capital expenditure, or trade in goods expand in connector countries. |
| [BEA direct investment by country and industry](https://www.bea.gov/data/intl-trade-investment/direct-investment-country-and-industry) | FDI validation | Check whether industry-country investment positions or flows support a production-relocation interpretation. |
| Mexico Secretaria de Economia / DataMexico FDI data | Mexico FDI-flow validation | Track 2021-2024 Mexico nearshoring trends by source country and industry. This fills a different role from BEA MNE activity because it is a flow measure, not affiliate output or value added. |
| USITC USMCA automotive rules-of-origin reports | Auto-sector production-integration evidence | Check whether Mexico/Canada auto exports to the U.S. satisfy USMCA preference rules. This helps separate genuine regional production integration from rerouting or shallow assembly. |
| National statistical agencies | Production-side validation | Use sources such as [INEGI](https://www.inegi.org.mx/) for Mexico, [Vietnam GSO](https://www.gso.gov.vn/en/homepage/) for Vietnam, and other national agencies for industry output, employment, investment, or manufacturing indices. |
| Reference replication data | Model-interface benchmark | Use only for sanity checks, variable definitions, and MATLAB input-interface tests. It should not be treated as final data for the new project. |

### 8.3 Updated Data Availability Assessment

| Data source | Availability | Coverage and current constraint | Project implication |
|---|---|---|---|
| OECD ICIO Extended | Free, direct download | Latest OECD release reaches 2022 and includes a China/Mexico split useful for ownership/firm-type heterogeneity | Very strong baseline source for IO and ownership-split production objects; 2023 nearshoring must be handled outside ICIO |
| OECD Analytical AMNE | Free, direct download | Ownership-split AMNE/ICIO tables cover through 2020 | Most important structural source for `hgamma`, but it stops before the full 2021-2023 nearshoring wave |
| BEA U.S. MNE Activity | Free, but selected detailed tables have discontinuities and some cells may be suppressed | BEA activity statistics can be queried through 2023 preliminary / 2022 revised releases; local check confirms Mexico x Transportation equipment, 2020-2022, is usable | Main post-2020 bridge for U.S.-MNE affiliate activity in Mexico; still need suppression checks for electronics and medical devices |
| fDi Markets | Available through the user's access | Project-level greenfield FDI database since 2003 | Central source for extensive-margin evidence; use it to document new projects, not as an endogenous Du-Wang model outcome |
| BACI | Free, direct download | HS6 bilateral annual trade; latest release currently listed through 2024 | Preferred trade source for rerouting, connector rankings, and sector-level exposure to Section 301 shocks |
| Mexico Secretaria de Economia / DataMexico FDI | Free government data | Quarterly FDI flows by country and industry, user-provided target range 1999-2024 Q4 | Useful for validating the direction and magnitude of Mexico nearshoring, but not a direct activity or plant-level measure |
| Section 301 tariff data | Free public data | USTR/USITC HS-level lists and effective tariff changes | Clean policy-shock layer for constructing `htau` inputs |
| USITC USMCA auto reports | Free statutory reports | Auto-sector rules-of-origin evidence; exact table references must be verified before citation | Useful for the auto-sector distinction between genuine production integration and rerouting/shallow assembly |

The practical data bottleneck has changed. fDi Markets access is no longer the binding constraint. The two remaining constraints are: (i) OECD Analytical AMNE stops in 2020, so the nearshoring period must be bridged with BEA, Mexico FDI, and fDi Markets; and (ii) BEA country-industry cells must be checked sector by sector for suppression.

### 8.4 What Additional Data Would Make The Project More Mature

For a JIE-level paper, the public-data version is feasible only if the research design is disciplined. The project should not overclaim firm-level relocation from aggregate evidence. The strongest version would add one or more of the following data layers:

| Additional data | Why it matters |
|---|---|
| Firm-level data such as Orbis, local business registries, or customs-linked firm data | Directly identifies firms, ownership, subsidiaries, industry, location, employment, revenue, and possibly entry or expansion in connector countries. |
| Plant-level or establishment-level manufacturing data | Separates genuine capacity expansion from simple trading-company activity. |
| Shipment-level data such as Panjiva, Datamyne, or ImportGenius | Tracks supplier-consignee links and can show whether Chinese suppliers ship to connector-country exporters that then ship to U.S. buyers. |
| Greenfield investment data beyond the available fDi Markets export, if needed | Improves validation of realized projects, cancellations, and follow-up operation status. |
| Special economic zone or export-processing-zone statistics | Useful for Vietnam, Mexico, and other connector candidates because relocation may concentrate in export platforms. |
| Product-level rules-of-origin or customs enforcement data | Helps distinguish genuine local production from transshipment or minimal processing. |

These data are not all required at the start. The minimum mature public-data package should combine: product-level trade data, tariff-shock data, OECD ICIO, OECD Analytical AMNE, BEA MNE or FDI data, and at least one national production-side source for each core connector country.

### 8.5 Recommended Empirical Standard

The first serious empirical version should require four linked facts before calling a country a production connector:

1. U.S. or EU imports from China decline in the affected products.
2. Imports from a connector country rise in the same products or sectors.
3. The connector country increases imports of related intermediate inputs from China or East Asia.
4. The connector country also shows sector-level production-side expansion, measured by value added, gross output, employment, investment, foreign-affiliate activity, or FDI.

If facts 1-3 hold but fact 4 is weak, the paper should frame the result as trade rerouting with limited production-side validation. If all four facts hold, the project can credibly claim that connector economies are not just statistical rerouting nodes but partial production reallocation channels.

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
- fDi Markets exported project-level data;
- new Stata, Python, or MATLAB data-build scripts;
- migrated model-core MATLAB functions;
- executable counterfactual scenarios.

This is intentional. The next task is to benchmark the existing empirical evidence, build a validation and calibration layer, and then migrate the structural model. The project should not spend its main effort reproducing an empirical contribution that Schulze and Xin (2025) already cover.

## 11. Immediate Next Steps

1. Add Schulze and Xin (2025) to the literature map as the closest empirical benchmark.
2. Reproduce only the minimum facts needed for validation: connector rankings, Vietnam-style value-added moments, and a North America/Mexico extension.
3. Export fDi Markets project-level records for Mexico and comparison connector economies, 2017-2024, with sector, business activity, parent/source country, capex, jobs, and announcement source.
4. Download and document OECD ICIO Extended, OECD Analytical AMNE/MNE-GVC, BACI, Section 301 tariff lists, Mexico FDI, and BEA MNE data in `docs/data_source_log.md`.
5. Check BEA suppression for Mexico x electronics/computers and Mexico x medical devices, matching the completed Mexico x transportation equipment check.
6. Build transparent country and sector mappings, with separate flags for Asian connectors and North American connectors.
7. Build an extensive-margin evidence table from fDi Markets, BEA MNE, AMNE, FDI, employment, investment, and value-added sources.
8. Construct a structural moment table that links observed trade, value-added, FDI, and affiliate-activity changes to candidate `htau` and `hgamma` shocks.
9. Build a small MATLAB-ready sample to test compatibility with the reference model interface.
10. Migrate `eqm_iter.m`, `eqm_update.m`, `wel_decomp.m`, and related model-core functions into `code/model_core/`.
11. Run the first welfare-counterfactual matrix: no connectors, trade-only connectors, MP intensive reallocation through connectors, and full connector mitigation.

## 12. Decision Rule For Moving To Structural Counterfactuals

Move to full model migration only if the first-stage evidence shows:

- the project can clearly state what Schulze and Xin (2025) already did and what this project adds;
- connector rankings and value-added moments are stable enough to discipline model shocks;
- direct bloc-to-bloc decline and third-country expansion are economically meaningful;
- at least one production-side source supports real relocation for key connectors, or the model explicitly treats relocation as a scenario rather than a proven fact;
- extensive-margin evidence is kept separate from model-implied outcomes and used only as validation or scenario discipline;
- country-sector concordances are transparent;
- model inputs can be generated without hard-coded country indices;
- welfare channels can be reported separately for direct fragmentation, connector mitigation, MP, and IO propagation.

If these conditions fail, the project should either narrow to a specific country-sector episode, focus on a Mexico/North America extension, or remain at the validation stage without claiming a full JMP contribution.

---

# 中文版项目介绍

## 双语维护规则

从本节加入开始，根目录 `README.md` 同时包含英文版和中文版项目说明。以后如果更新项目定位、研究问题、数据来源、模型复用规则、目录结构、下一步计划或进入结构模型的判断标准，必须同时更新英文部分和中文部分，避免合作者看到两个版本时得到不一致的信息。

## 1. 项目一句话

本项目研究 geoeconomic fragmentation 背景下 connector economies 的福利价值：当两个地缘政治集团之间的直接贸易和跨国生产联系变弱时，一些第三方国家可能成为新的中间人、出口平台或生产地点。已有实证文献已经研究了这些国家到底是真实生产转移，还是贸易绕行和转口。本项目现在应进一步问：这些 connector countries 到底在一般均衡中缓解了多少 fragmentation 的福利损失，这种缓解来自 trade rerouting、multinational production relocation，还是 input-output 网络传播？

本项目不是对现有文献的简单复现。`reference/` 中的 Du and Wang (2022) 复现包提供了一个非常有用的结构模型框架：多国、多部门、同时包含 trade、multinational production 和 input-output linkages。但最新的 IMF Working Paper 已经覆盖了相当一部分 connector economies 的实证识别。因此，本项目不能把“区分生产转移和贸易绕行”作为主贡献，而应把它作为模型校准和验证的事实基础。

## 2. 核心研究问题

本项目的主问题是：

> connector economies 在多大程度上缓解了 geoeconomic fragmentation 的福利成本？这种缓解分别来自 trade rerouting、multinational production relocation 和 input-output propagation 的哪一部分？

这里需要严格区分三种现象：

- **真实生产转移**：connector countries 的生产、foreign affiliate activity、value added、本地采购或就业同步增加。
- **贸易绕行**：connector countries 的进口或出口增加，但没有相应的本地生产扩张证据。
- **隐藏依赖**：最终目的国表面上从 connector country 进口，但 connector country 本身仍高度依赖原始来源集团的中间投入。

如果不能区分这三类现象，项目很容易退化为一个 gross trade diversion 的描述性研究。更重要的是，Schulze and Xin (2025) 已经系统做了这一区分，所以本项目必须把贡献推进到结构福利反事实。

## 3. 为什么这个题目有 JMP 潜力

这个题目不是简单地问“贸易是否转移到第三国”。在 Schulze and Xin (2025) 之后，单独证明 connector economies 存在，或者区分 production relocation 和 trade rerouting，已经不足以作为 JMP 主贡献。本项目的潜在贡献应转为把三个层面结合起来：

1. **结构福利核算**：量化 connector economies 到底降低了多少 fragmentation 的福利损失。
2. **机制分解**：把 connector mitigation 分解为 trade rerouting、MP relocation 和 IO propagation。
3. **经验校准与验证**：利用已有实证事实和新数据约束模型冲击，而不是把实证识别本身作为主贡献。

政策上，friend-shoring、near-shoring 和 decoupling 常常会根据 gross trade flows 判断是否成功。但即使我们知道第三国是真实生产转移还是贸易绕行，仍然不知道它在一般均衡中到底节省了多少福利成本。本项目的目标就是把这个 welfare value 讲清楚。

### 3.1 直接竞争文献与项目调整

目前最直接的竞争文献是：

> Tatjana Schulze and Weining Xin, "Demystifying Trade Patterns In A Fragmenting World," IMF Working Paper WP/25/129, June 2025.

这篇文章已经覆盖了本项目原来设想中的相当一部分第一阶段实证工作。它研究中美贸易摩擦后的 connector countries，明确区分 **trade reallocation** 和 **trade rerouting**，使用 granular trade data、multi-region input-output 数据中的 value-added measures、greenfield FDI 数据，并使用 synthetic control 方法。它的核心样本是六个亚洲经济体：India、Indonesia、Malaysia、Philippines、Thailand 和 Vietnam。

这篇文章的主要结论是：Vietnam 在 strategic sectors 中有比较清楚的 trade reallocation 证据，即对美国出口中的 domestic value added 上升，同时没有明显证据表明 Vietnam 主要是在替中国做大规模 transshipment。其他五个亚洲经济体的证据则比较弱。文章还用 Orbis Cross-Border Investment 数据说明，Vietnam 的结果可能与来自中国的 greenfield FDI 有关。

因此，本项目不能再把以下内容当作主贡献：

- 证明 connector countries 存在；
- 说明 gross trade flows 可能隐藏供应链依赖；
- 在亚洲 connector economies 中区分 trade reallocation 和 trade rerouting；
- 用 value-added 数据和 synthetic control 证明 Vietnam 的生产侧扩张。

这些内容现在应作为已有文献基础。本项目真正有空间的地方是进一步问：

> 在 connector channel 已经存在的前提下，它的一般均衡福利价值是多少？trade-only rerouting、MP relocation 和 IO 网络传播分别缓解了多少 fragmentation 的福利损失？

因此，项目应往三个方向调整。第一，做 **welfare accounting**，而不是只做实证识别。第二，利用 `reference` 模型中的 MP 结构，把 production-location change 和 trade-cost change 分开。第三，加入 Mexico 和可能的 Canada，形成 North American connector extension，因为 Schulze and Xin (2025) 的核心样本是亚洲经济体，没有把 Mexico 作为中心案例。

## 4. `reference` 材料是什么

`reference/` 文件夹包含 Du and Wang (2022) 的论文和复现包：

> Xiayi Du and Zi Wang, "Multinationals, global value chains, and the welfare impacts of economic sanctions," Economics Letters, 2022.

这篇文章研究俄罗斯制裁的福利影响。其模型包含：

- 44 个经济体；
- 34 个部门；
- bilateral trade linkages；
- multinational production linkages；
- input-output linkages；
- welfare decomposition。

这套材料对本项目非常重要，因为它已经实现了我们需要的结构模型类型。但它本身不能直接成为本项目的代码基础，因为它的应用场景、数据年份、国家设定和冲击设定都围绕 Russia sanctions，而不是 connector economies。

因此，本项目将 `reference/` 视为只读上游材料。新代码、数据构建、配置文件和输出都应放在当前项目自己的目录中，不应直接修改 `reference/` 中的复现包。

### 4.1 Du-Wang 的 MP margin 到底是什么

当前最关键的模型风险，是 Du-Wang 能不能直接承担本项目的 MP channel。核验结果很明确：Du-Wang 的 MP margin 是 **iceberg MP cost**，不是 Tintelnot 式的 fixed-cost entry margin。

论文正文写明，origin country `i` 的企业可以在 production location `ell` 生产，但要面对 `gamma_iell^j >= 1` 的 iceberg MP cost，且 `gamma_ii^j = 1`。企业的 unit cost 里，`gamma_iell^j` 与 trade-cost term `kappa_elln^j` 连乘。复现代码也完全对应这一点：`eqm_update.m` 把 `hgamma`、`hkappa`、工资变化和中间品价格变化一起乘进 `hxi_4d`，再通过 `hpsi_4d` 和 `hlam_3d` 更新 MP share 与 sourcing share。

因此，`hgamma` 应解释为 MP variable cost 的变化，也就是通过 foreign affiliate location 组织生产的有效成本变化。它不应被解释为进入固定成本、affiliate entry threshold、企业数量变化或 plant relocation。复现代码中没有 fixed-cost entry 方程，没有内生 affiliate count，没有 binary entry decision，也没有 plant-level relocation margin。

对本项目的含义如下：

| 路线 | 判断 |
|---|---|
| 在 Du-Wang 上重构情景配置和数据接口 | 推荐作为第一版。它已经包含 trade、MP、IO linkages 和 welfare decomposition。 |
| 用 AMNE、BEA MNE、FDI 或生产侧 moments 约束 `hgamma` | 必须做。MP-cost shock 的大小不能任意设定。 |
| 直接转向 BHLP / Bonadio 风格框架并自行加入 MP 层 | 第一版不推荐。除非放弃 Du-Wang 的 sufficient-statistics 结构，否则建模负担会明显上升。 |
| 改成 Tintelnot 式 fixed-cost entry model | 只有当论文核心变成 affiliate entry 或 plant-count relocation 时才需要，而且需要更强的微观或企业层面证据。 |

结论是：Du-Wang 可以作为 connector welfare accounting 的第一版结构骨架，但解释必须收窄。它能计算 trade-cost 和 MP-cost shock 的福利影响；它不能单独证明企业进入了 connector country，也不能证明工厂发生了物理迁移。真实 production relocation 的证据必须来自经验验证层，然后再作为有依据的 `hgamma` 情景进入模型。

### 4.2 模型边界：intensive margin 与新企业进入

论文不应声称 Du-Wang 模型能解释 Section 301 之后中国企业或其他跨国企业在墨西哥新设工厂。主模型应定位为 **intensive-margin welfare accounting**：它能回答的是，当贸易成本和有效 MP variable cost 在已有国家-部门连接上变化时，生产份额、贸易份额、中间品可得性和福利如何变化。它不能内生解释一个企业是否进入墨西哥、是否新建 affiliate、是否增加 plant count。

项目的两条机制仍然成立，但必须这样表述：

| 机制 | 模型可以解释什么 | 模型外需要补什么 |
|---|---|---|
| Trade rerouting / indirect sourcing | 通过 `htau`、sourcing shares、foreign intermediates 和 IO propagation 解释福利变化。 | 产品层面的贸易数据证明 rerouting 确实发生。 |
| MP relocation / nearshoring | 通过 `hgamma` 下降解释已有或模型中已表示的 MP link 上生产强度向 connector location 调整。 | 新 affiliate、新工厂公告、plant count 或 firm entry 证据。 |

这并不意味着项目不能达到 JIE 水平。它意味着论文必须和读者订清楚契约：结构模型量化 connector access 和 effective MP-cost changes 的福利含义；经验部分验证 nearshoring 是否有 extensive-margin 支持，并用这些证据约束 `hgamma` 情景。

因此，第一版应增加一个模型外的 **extensive-margin evidence section**。这部分可以使用 fDi Markets、BEA MNE、AMNE、FDI、value added、employment 或 investment 数据，说明 Mexico 或其他 connector economies 是否在相关部门出现新项目、affiliate activity 或生产侧扩张。它的作用是验证故事、约束 `hgamma`、设定 sensitivity bounds，而不是把新进入当作 Du-Wang 模型的内生结果。

推荐表述是：

> The structural model captures intensive reallocation across existing MP links. It does not endogenize entry of new affiliates or plants. We therefore treat greenfield FDI and new project announcements as model-external evidence that validates the nearshoring mechanism and helps discipline MP-cost counterfactuals.

只有当论文核心问题改成 affiliate entry 或 plant-count relocation 时，才应转向 Tintelnot-style fixed-cost foreign-investment model。那条路线需要更强的企业、项目或工厂层面数据，也需要新增完整的 entry block，不应作为第一版默认路径。

## 5. 本项目从 `reference` 继承了哪些设定

### 5.1 继承的模型类型

本项目继承 `reference` 中的基本模型环境：

- 多国模型；
- 多部门模型；
- trade linkages；
- multinational production linkages；
- input-output linkages；
- general-equilibrium welfare accounting。

在原始 MATLAB 代码中，模型维度写为：

- `m.N = 44`：经济体数量；
- `m.J = 34`：部门数量；
- `m.JT = 18`：tradable goods sectors 数量。

这些数字目前只作为 reference 设定使用。新项目不应永久硬编码这些数值，因为新的数据可能采用不同国家集合、不同部门聚合或不同时间窗口。后续代码应从 country mapping 和 sector mapping 文件读取维度。

### 5.2 继承的 MATLAB 数据接口

`reference` 复现包把 Stata 清洗后的数据导出到 `tomatlab/` 中，再由 MATLAB 读取。这个接口设计对新项目有直接价值，因为它告诉我们结构模型需要什么类型的输入。

本项目计划保留相似的中间输入结构：

| reference 输入 | 经济含义 | 新项目用途 |
|---|---|---|
| `mpshare_2016.csv` | origin-production location-sector 的 MP share | 衡量 foreign affiliate / MP exposure 和生产转移通道。 |
| `trshare_2018.csv` | origin-destination-sector 的 trade share | 衡量贸易绕行和 sourcing shares。 |
| `X_2018.csv` | destination-sector expenditure | 构造国家-部门支出基准。 |
| `va_2018.csv` | final demand shares 和 value-added shares | 校准最终需求和生产端结构。 |
| `IO_2018.csv` | 国家-部门间 input-output shares | 衡量中间投入传播。 |
| `tariff_2019.csv` | 双边部门关税 | 作为 baseline trade-cost component。 |
| `cal_elasticity.csv` | 部门层面的 `sigma`、`theta`、`rho` | 作为 demand、trade、MP 弹性参数。 |

新项目不应直接复制这些旧 CSV 作为正式数据，而是应使用 OECD ICIO、OECD AMNE、Comtrade 或 BACI 等新数据生成对应格式，并放入 `data/model_inputs/`。

### 5.3 继承的四维 flow 结构

`reference` 模型中最关键的数据对象是：

`X_4d(i, ell, n, j)`

其中：

- `i`：firm origin country；
- `ell`：production country；
- `n`：destination market；
- `j`：sector。

这个四维对象对本项目尤其重要，因为 connector economies 的本质就是第三国到底进入了哪个位置：

- 是作为生产地点 `ell`？
- 是作为贸易路径上的中间出口国？
- 还是只是统计上看起来像新的 supplier？

`main_impute_triflows.m` 和 `impute_tri.m` 提供了如何从 MP shares、trade shares 和 expenditure 推回 `X_4d` 的参考逻辑。后续模型迁移时应保留这个结构。

### 5.4 继承的 equilibrium solver

`reference` 中的 `eqm_iter.m` 和 `eqm_update.m` 是 equilibrium solver 的核心。它们做的事情包括：

- 初始化 wage、price、expenditure changes；
- 在冲击后更新 trade shares 和 MP shares；
- 更新价格、工资、支出、利润和关税收入；
- 迭代到收敛。

新项目会复用这套 solver 的经济结构，但要先重构代码：

- 删除 Russia-specific country indices；
- 删除硬编码路径；
- 让国家、部门、情景从配置文件读入；
- 加入输入维度检查。

### 5.5 继承的 shock 表达方式

`reference` 的反事实情景用三个对象表达冲击：

- `htau`：trade cost changes；
- `hgamma`：MP cost changes；
- `tTar`：tariff levels。

在 Russia sanctions 脚本中，切断某条 link 的做法是把对应 `htau` 或 `hgamma` 设置为非常大的数，例如 `9999`。

新项目会继承“fragmentation 可以表示为 trade cost 和 MP cost 变化”的思想，但不会继承写死在 MATLAB 脚本里的 Russia 情景。未来应通过 `configs/` 中的 scenario 文件定义：

- source bloc；
- destination bloc；
- connector countries；
- sector list；
- baseline year；
- shock year；
- trade-cost shock；
- MP-cost shock。

`reference` 中具体有四个反事实脚本：

| reference 脚本 | shock 设计 | 经济含义 | 输出 |
|---|---|---|---|
| `main_cf_RUS_sanction.m` | 对每个部门，把 Russia 与几乎所有其他经济体之间的双边 `htau` 和 `hgamma` 设为 `9999`；Russia 国内 link 保持为 `1`；China-Russia link 保持为 `1`。 | 同时切断 Russia 的 trade 和 MP 联系，但保留 China 作为未制裁或豁免伙伴。 | `RUS_sanction_TRMP.csv` |
| `main_cf_RUS_sanction_notrade.m` | 与上一个场景相同，但只把 `htau` 设为 `9999`，`hgamma` 保持基准。 | 只切断贸易联系，不直接切断 MP 联系。 | `RUS_sanction_TR.csv` |
| `main_cf_RUS_sanction2.m` | 同时切断 `htau` 和 `hgamma`，但保留 Russia 与一组更宽的外部国家联系：China、Brazil、Indonesia、India、Mexico、ROW、Turkey、Taiwan。 | Russia 被主要制裁集团隔离，但仍可通过一组未制裁或类似 connector 的国家保持 trade 和 MP 联系。 | `RUS_sanction_TRMP2.csv` |
| `main_cf_RUS_sanction_notrade2.m` | 上一场景的 trade-only 版本，只切断 `htau`。 | 保留外部国家联系的贸易制裁场景。 | `RUS_sanction_TR2.csv` |

这些脚本对本项目的价值不在 Russia 本身，而在于它们提供了一个可改造的 counterfactual 结构：直接切断、只切断 trade、同时切断 trade 和 MP、以及保留第三方国家通道。新项目应把这种结构改写为 connector economies 的情景矩阵：

| 新项目场景 | shock 对象 | 目的 |
|---|---|---|
| Baseline | `htau = 1`、`hgamma = 1`、`tTar = baseline tariffs` | 得到一致的冲击前均衡。 |
| Direct fragmentation, no connectors | 提高 source bloc 与 destination bloc 之间的 `htau`，必要时同时提高 `hgamma`。 | 衡量直接脱钩的福利成本。 |
| Trade-only connector access | 直接 bloc-to-bloc link 仍然变贵，但 connector 相关 `htau` 保持开放或成本较低，`hgamma` 不变。 | 单独识别 gross trade rerouting。 |
| MP relocation through connectors | connector 相关 `hgamma` 保持开放或下降，并配合 trade access。 | 衡量真实 production relocation 和 foreign affiliate activity。 |
| Full connector mitigation | 同时允许 trade rerouting 和 MP relocation。 | 衡量 connector economies 能缓解多少 fragmentation 损失。 |
| No-connector stress test | 同时提高 direct bloc links 和 connector links 的 trade/MP barriers。 | 衡量没有第三方调整时的剩余福利成本。 |

因此，本项目后续的 counterfactual 不应再写成“Russia = 38、China = 8”。所有 source bloc、destination bloc、connector countries、sector list、shock intensity 和年份都应从 `configs/` 读取。结构模型输出也应明确分解为 direct fragmentation、connector mitigation、MP relocation 和 IO propagation。

### 5.6 继承的 welfare decomposition

`wel_decomp.m` 是最应优先复用的文件之一。它把 welfare changes 分解为：

| 分解项 | 在本项目中的解释 |
|---|---|
| `GFF` | 外国最终品可得性变化带来的福利变化。 |
| `GFI` | 外国中间品可得性变化带来的福利变化。 |
| `GOF` | offshoring 和 MP access 变化带来的福利变化。 |
| `SEC` | 部门间 input-output linkages 的传播效应。 |
| `MS` | market size effect。 |
| `PT` | profit 和 tariff revenue channel。 |

对 connector economies 题目来说，最重要的可能是 `GFI`、`GOF` 和 `SEC`。如果 connector countries 真的缓解 fragmentation，那么它们应当影响 foreign intermediates 的可得性、跨国生产的可行性，以及投入产出网络中的传播成本。

## 6. `reference` 材料目前不够的地方

### 6.1 它研究的是 Russia sanctions，不是 connector economies

`reference` 中的反事实脚本围绕俄罗斯制裁写成，很多国家直接用固定 index 表达，例如 Russia、China、USA 以及若干 sanctioning countries。这不适合新项目。

新项目需要：

- 外部定义 geopolitical blocs；
- 从数据中识别 connector candidates；
- 允许国家角色随年份、部门和情景变化；
- 避免在 MATLAB 中写死国家 index。

### 6.2 它不能识别贸易绕行

`reference` 模型可以计算给定冲击下的福利变化，但它不告诉我们贸易是否真的通过第三国绕行。

新项目必须增加经验层：

- direct bloc-to-bloc trade changes；
- source bloc 到 connector 的进口变化；
- connector 到 destination bloc 的出口变化；
- sector-level connector exposure；
- 真实生产转移与纯 rerouting 的区分指标。

这需要 Comtrade 或 BACI 这类更细产品层面的 bilateral trade 数据。

### 6.3 它不能区分 production relocation 和 transshipment

`reference` 有 MP shares 和 IO 数据，但它不是为判断第三国是否真实生产扩张而设计的。

新项目需要生产侧证据，例如：

- OECD AMNE foreign affiliate activity；
- ICIO value added 和 gross output；
- 部门层面的生产、就业、投资或 FDI 数据；
- 如果公开数据不够，后续可考虑 firm-level 或 plant-level 数据。

如果没有生产侧验证，项目只能说明贸易路径变化，不能说明 connector countries 是否真实降低 fragmentation 的福利成本。

### 6.4 数据年份不够新

`reference` 使用的是：

- 2016 年 AMNE；
- 2018 年 ICIO / trade / IO；
- 2019 年 tariff；
- 2022 年前的 Russia sanctions baseline。

本项目研究的是更一般的近期 geoeconomic fragmentation，需要新的数据版本，并且要明确区分：

- structural baseline year；
- shock year；
- post-shock descriptive evidence；
- 不同数据源由于发布滞后导致的年份不一致。

### 6.5 它没有 connector-country definition

`reference` 有国家和部门，但没有 connector economy 的定义。新项目必须构造一个可检验的 connector measure。

第一版 connector measure 应至少包含：

1. 从 source bloc 的进口增加；
2. 对 destination bloc 的出口增加；
3. 两类贸易流在部门上的重叠；
4. AMNE、value added 或 gross output 的生产侧支持；
5. 跨年份持续性，而不是单年异常值。

### 6.6 它没有可审查的 scenario config

`reference` 直接在 MATLAB 脚本中写情景。这不利于合作者审查，也不利于做多个情景比较。

新项目应在 `configs/` 中建立配置文件，用来定义：

- bloc membership；
- connector candidate list；
- sector list；
- baseline and shock years；
- shock intensity；
- output naming rule。

### 6.7 它没有 model input validation

`reference` 默认输入顺序和维度正确。新项目从多个数据源重建输入，这样做风险很高。

在任何 MATLAB 运行之前，新项目必须检查：

- 国家顺序；
- 部门顺序；
- 缺失国家或部门；
- country-sector pair 是否完整；
- shares 是否加总正确；
- 所有矩阵和数组维度是否一致；
- connector definitions 是否能映射到模型国家列表。

### 6.8 gravity calibration 可能需要重做

`cal_gravity.do` 提供了 sector-level gravity calibration 模板，但它不一定适用于本项目。

需要重新评估的原因包括：

- 新项目的国家集合可能不同；
- 部门聚合可能不同；
- 时间窗口不同；
- fragmentation shocks 可能来自 sanctions、export controls、policy uncertainty 或 non-tariff barriers，而不只是 tariff；
- connector-country 行为可能对 elasticity assumptions 很敏感。

### 6.9 它没有第一阶段 identification strategy

`reference` 是结构反事实，不是用来证明 connector economies 存在的经验识别设计。

Schulze and Xin (2025) 已经做了相当完整的 connector economies 经验识别。因此，新项目进入结构模型之前仍然需要经验层，但这个经验层的角色应改为验证样本、校准冲击、约束 counterfactual，而不是作为论文主贡献。

新项目必须先回答：

- 哪些国家成为 connector？
- 哪些部门驱动这个现象？
- 新数据是否能复现或扩展 IMF paper 的核心事实？
- Mexico 或其他 North American connector 是否存在该文没有覆盖的机制？
- 哪些经验 moments 可以约束模型中的 `htau` 和 `hgamma` shock size？
- 是否有足够生产侧证据支持 MP relocation scenario？

只有这些校准和验证事实成立，结构模型才值得迁移。

## 7. 第一阶段经验验证与模型校准计划

第一阶段目标不是跑完整结构模型，也不是重复 Schulze and Xin (2025) 已经完成的实证识别，而是判断本项目是否有足够可靠的模型输入和 counterfactual 依据。

需要完成六个输出：

1. **literature benchmark table**：把 Schulze and Xin (2025) 的样本、数据、方法和结论列清楚，明确本项目不重复哪些贡献。
2. **connector ranking table**：按国家和部门识别 connector candidates，并与 IMF paper 的亚洲样本结果对照。
3. **North America extension figure**：重点检查 Mexico 和 Canada 是否存在与亚洲样本不同的 connector 机制。
4. **production-side validation table**：检查贸易增长是否伴随 AMNE、value added、gross output、FDI 或其他生产侧指标增长。
5. **extensive-margin evidence table**：整理 fDi Markets、BEA MNE、AMNE、FDI 或其他生产侧资料中的新项目、新 affiliate、投资和就业证据，明确它们是模型外验证，不是 Du-Wang 的内生结果。
6. **small MATLAB-ready sample**：构造一个小样本，测试新数据能否进入 reference 模型接口。

此外，还需要增加一张 **structural moment table**，把经验事实转成模型输入：direct bloc-to-bloc trade decline、connector exports、connector imports、production-side expansion、FDI 或 foreign-affiliate activity，以及这些事实对应的 `htau` 和 `hgamma` 情景设定。如果这些 moments 不能清楚支持结构反事实，就不应急于迁移完整 MATLAB 模型。

## 8. 数据计划

第一版可以从公开数据开始，但不同问题对数据的要求并不一样。公开数据最能支撑的是贸易绕行事实和一般均衡福利反事实；最弱的是直接证明企业层面的真实生产转移。因此，本项目在数据表述上必须区分“能强验证”“能部分验证”和“需要更强数据”。

### 8.1 公开数据能支撑什么

| 研究对象 | 公开数据是否足够 | 原因 |
|---|---|---|
| 直接集团间贸易下降 | 强 | BACI、UN Comtrade 和美国进口数据可以在产品-国家-年份或产品-国家-月份层面测量美国从中国进口是否下降。 |
| 第三国贸易绕行 | 强 | 同一套产品层面贸易数据可以检验 connector candidates 是否在相同产品或相关部门上同时增加从 source bloc 的进口和对 destination bloc 的出口。 |
| 对中国或东亚中间品的隐藏依赖 | 中到强 | 产品层面进口可以通过 BEC 或行业映射区分中间品、资本品和消费品，从而判断 connector exports 是否伴随对中国或东亚投入品的依赖上升。 |
| 真实生产转移 | 部分足够 | OECD ICIO、OECD Analytical AMNE、BEA MNE、FDI 数据和国家制造业统计可以验证部门层面的产出、增加值、就业、投资或外资企业活动是否扩张。但这些数据不能直接证明某个企业把工厂从中国搬到了越南或墨西哥。 |
| 纯转口、轻度组装与真实本地增加值扩张的区分 | 部分到偏弱 | 如果本地增加值和就业同步上升，可以排除一部分简单转口解释；但没有企业、工厂或 shipment-level 数据时，很难干净地区分重新贴标签、简单组装和深度本地生产。 |
| 一般均衡福利反事实 | 足够支持第一版结构模型 | OECD ICIO 加上贸易份额、弹性参数、关税和 reference 模型中的 welfare decomposition，可以支持 counterfactual。关键是冲击大小要由产品层面的贸易和政策证据约束，而不能任意设定。 |

因此，最稳妥的判断不是“公开数据已经证明真实生产转移”，而是：公开数据足以建立强贸易绕行事实，可以用生产侧总量数据验证这种绕行是否伴随真实生产扩张，并且足以支撑第一版结构福利反事实。若要直接证明企业 relocation，则需要更细的数据。

### 8.2 核心可用数据源

| 数据源 | 在项目中的作用 | 具体用途 |
|---|---|---|
| [OECD ICIO, including Extended ICIO](https://www.oecd.org/en/data/datasets/inter-country-input-output-tables.html) | 国家-部门生产和投入产出结构 | 构造 gross output、value added、final demand、中间投入联系和模型基准。Extended ICIO 对 China 和 Mexico 的 ownership / firm-type 层进行拆分，对本项目特别有用。 |
| [OECD TiVA](https://www.oecd.org/en/data/datasets/trade-in-value-added.html) | 增加值贸易解释 | 检查 gross trade rerouting 是否对应真实 value-added exposure 的变化。 |
| [OECD Analytical AMNE](https://www.oecd.org/en/data/datasets/multinational-enterprises-and-global-value-chains.html) / [AMNE](https://www.oecd.org/en/data/datasets/activity-of-multinational-enterprises.html) | 外资企业活动和跨国生产 | 验证 connector countries 是否在相关部门出现 foreign-affiliate sales、employment、value added 或 output 扩张。这是 2020 年以前约束 `hgamma` 的核心 ownership-split 数据。 |
| [fDi Markets](https://www.fdimarkets.com/) | Greenfield FDI project evidence；使用者已确认可得 | 构造模型外 extensive-margin evidence table：新项目、来源国、目的地、行业、business activity、公告投资额和预期就业。 |
| [BACI](https://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=37) | 产品层面双边贸易 | 构造 connector rankings、rerouting figures、source-bloc imports、destination-bloc exports 和部门重叠指标。BACI 的 HS6 口径比 DOTS 或总量贸易数据更适合映射到汽车、电子、医疗器械、机械和零部件部门。 |
| [UN Comtrade](https://comtradeplus.un.org/) | 产品层面双边贸易交叉核对 | 如果 BACI 的 concordance 或时点口径有问题，可作为 robustness 或 cross-check。 |
| [美国 Census USA Trade Online](https://usatrade.census.gov/) | 高分辨率美国进口证据 | 用美国作为目的国，在月度或 HS10 层面验证中美关税冲击和进口替代。 |
| USTR Section 301 lists、[USITC HTS](https://hts.usitc.gov/)、WITS / TRAINS、WTO 和相关官方关税文件 | 政策冲击度量 | 构造 HS 层面的 tariff 和 policy-cost shocks，尤其是 U.S.-China Section 301 产品和其他 fragmentation episodes。 |
| [BEA U.S. MNE data](https://www.bea.gov/data/intl-trade-investment/activities-us-multinational-enterprises-mnes) | 美国跨国公司海外 affiliate 活动 | 检查美国企业在 connector countries 的 affiliate employment、sales、value added、capital expenditure 或 goods trade 是否扩张。 |
| [BEA direct investment by country and industry](https://www.bea.gov/data/intl-trade-investment/direct-investment-country-and-industry) | FDI 验证 | 检查国家-行业层面的投资存量或流量是否支持 production relocation 解释。 |
| Mexico Secretaria de Economia / DataMexico FDI data | 墨西哥 FDI flow 验证 | 追踪 2021-2024 年 Mexico nearshoring 在来源国和行业层面的趋势。它是 flow measure，不等同于 affiliate output 或 value added。 |
| USITC USMCA automotive rules-of-origin reports | 汽车部门生产整合证据 | 检查 Mexico / Canada 输美汽车是否满足 USMCA preferential rules，有助于区分真实区域生产整合和 rerouting / shallow assembly。 |
| 国家统计机构 | 生产侧验证 | 对墨西哥可看 [INEGI](https://www.inegi.org.mx/)，对越南可看 [GSO](https://www.gso.gov.vn/en/homepage/)；其他候选国家也应补充本国制造业产出、就业、投资或工业指数。 |
| reference replication data | 模型接口 benchmark | 只用于 sanity checks、变量定义和 MATLAB 输入接口测试，不作为本项目正式数据。 |

### 8.3 数据可得性更新评估

| 数据源 | 可得性 | 覆盖范围和当前约束 | 对项目的影响 |
|---|---|---|---|
| OECD ICIO Extended | 免费，直接下载 | 最新 OECD release 到 2022，并包含对 China / Mexico 有用的 ownership / firm-type 拆分 | 非常适合作为 IO 和 ownership-split production baseline；2023 nearshoring 需要用模型外数据补充 |
| OECD Analytical AMNE | 免费，直接下载 | ownership-split AMNE / ICIO 表到 2020 | 是约束 `hgamma` 的最关键结构数据，但缺失 2021-2023 nearshoring 高峰 |
| BEA U.S. MNE Activity | 免费，但部分细表停更且个别国家-行业单元可能 suppressed | BEA activity statistics 可查到 2023 preliminary / 2022 revised；本地已核实 Mexico x Transportation equipment, 2020-2022 可用 | 是 OECD Analytical AMNE 之后美国 MNE 在墨西哥活动的主要补充；还需检查 electronics 和 medical devices 是否 suppressed |
| fDi Markets | 使用者已确认可得 | 2003 年以来的 greenfield FDI project-level database | extensive-margin evidence 的核心来源；用于说明新项目公告，而不是 Du-Wang 模型内生结果 |
| BACI | 免费，直接下载 | HS6 年度双边贸易，当前最新版本覆盖到 2024 | 贸易绕行、connector ranking 和 Section 301 暴露的首选贸易数据 |
| Mexico Secretaria de Economia / DataMexico FDI | 免费政府数据 | 使用者提供的目标口径为 1999-2024 Q4 的季度 FDI flows | 可验证 2021-2024 Mexico nearshoring 的方向和数量级，但不是 activity 或 plant-level measure |
| Section 301 tariff data | 免费公开 | USTR / USITC 的 HS-level tariff lists 和生效变化 | 最干净的 policy-shock 层，用于构造 `htau` |
| USITC USMCA auto reports | 免费法定报告 | 汽车部门 rules-of-origin 证据；具体表格和定义引用前必须复核 | 对区分真实生产整合与 rerouting / shallow assembly 特别有用 |

因此，实际数据瓶颈已经改变。fDi Markets 不再是约束条件。剩下两个关键约束是：第一，OECD Analytical AMNE 到 2020 为止，nearshoring 期必须用 BEA、Mexico FDI 和 fDi Markets 补；第二，BEA 国家-行业单元必须逐部门检查 suppression。

### 8.4 想做到更成熟还需要什么数据

如果目标是 JIE 级别，公开数据版本可以成立，但研究设计必须非常克制：不能用总量数据直接声称 firm-level relocation。更强的版本应尽量补充以下数据层：

| 补充数据 | 为什么重要 |
|---|---|
| Orbis、本地企业注册数据或海关-企业匹配数据 | 直接识别企业、母公司、子公司、行业、所在地、就业、收入，以及企业是否在 connector countries 新进入或扩张。 |
| 工厂或 establishment-level 制造业数据 | 区分真实产能扩张和单纯贸易公司活动。 |
| Panjiva、Datamyne、ImportGenius 等 shipment-level 数据 | 追踪 supplier-consignee links，判断中国供应商是否先发货给 connector-country exporter，再由其发往美国买家。 |
| fDi Markets export 之外的 greenfield investment 后续验证数据，如能取得 | 用于核对已公告项目是否实际投产、取消或延后。 |
| 出口加工区或特殊经济区统计 | 越南、墨西哥等 connector candidates 的生产转移可能集中在出口平台，这类数据有助于验证机制。 |
| rules-of-origin 或海关执法数据 | 帮助区分真实本地生产、最小加工和转口。 |

这些数据不需要一开始全部取得。最低限度的成熟公开数据包应包括：产品层面贸易数据、关税冲击数据、OECD ICIO、OECD Analytical AMNE、BEA MNE 或 FDI 数据，以及每个核心 connector country 至少一个国家层面的生产侧数据源。

### 8.5 推荐的经验标准

第一版严肃经验结果应要求四个事实同时成立，才把一个国家称为 production connector：

1. 美国或欧盟从中国进口的受影响产品下降；
2. 美国或欧盟从 connector country 进口相同产品或相关部门产品上升；
3. connector country 从中国或东亚进口相关中间品上升；
4. connector country 在对应部门出现 production-side expansion，例如 value added、gross output、employment、investment、foreign-affiliate activity 或 FDI 上升。

如果只有前三个事实成立，而第四个事实弱，那么论文应表述为“贸易绕行具有强证据，但生产侧验证有限”。如果四个事实都成立，才可以较有把握地说 connector economies 不只是统计上的贸易节点，而是部分承担了真实生产重配功能。

原始数据应放在 `data/raw/`，中间数据放在 `data/interim/`，分析数据放在 `data/processed/`，MATLAB 输入放在 `data/model_inputs/`。这些数据文件默认不提交到 git，只提交说明文件、代码和小型测试样本。

## 9. 当前项目状态

目前仓库只有项目文档和目录骨架。尚未包含：

- OECD ICIO 或 AMNE 下载数据；
- Comtrade 或 BACI 数据；
- fDi Markets 项目级导出数据；
- 新的 Stata / Python / MATLAB 数据构建脚本；
- 已迁移的 MATLAB model core；
- 可执行的 counterfactual scenarios。

这是有意为之。下一步应先建立文献 benchmark、经验验证和模型校准层，而不是重复一篇已经存在的 connector economies 实证文章。

## 10. 近期下一步

1. 把 Schulze and Xin (2025) 写入 literature map，作为最直接的 empirical benchmark。
2. 只复现模型需要的最低限度事实：connector ranking、value-added moments，以及 Vietnam 结果的可比口径。
3. 做 North America extension，重点检查 Mexico 和可能的 Canada 是否存在亚洲样本之外的 connector 机制。
4. 从 fDi Markets 导出 2017-2024 年 Mexico 和对照 connector economies 的项目级记录，字段至少包括 sector、business activity、母公司和来源国、目的地、capex、jobs 和公告来源。
5. 下载并记录 OECD ICIO Extended、OECD Analytical AMNE / MNE-GVC、BACI、Section 301 tariff lists、Mexico FDI 和 BEA MNE 数据来源、版本和年份覆盖。
6. 检查 BEA 中 Mexico x electronics/computers 和 Mexico x medical devices 是否存在 suppression，并与已完成的 Mexico x transportation equipment 检查保持同一口径。
7. 建立 country mapping 和 sector mapping，并区分 Asian connectors 与 North American connectors。
8. 构造 extensive-margin evidence table，把 fDi Markets 新项目公告、BEA MNE / AMNE affiliate activity、FDI、就业、投资和增加值证据单独列出，明确它们是模型外验证。
9. 构造 structural moment table，把贸易、增加值、FDI 和 affiliate activity 事实转成 `htau` 与 `hgamma` 情景设定。
10. 构造小型 MATLAB-ready sample，测试是否兼容 `reference` 的模型接口。
11. 迁移 `eqm_iter.m`、`eqm_update.m`、`wel_decomp.m` 等模型核心函数，并运行第一组 welfare-counterfactual matrix。

## 11. 进入结构模型的判断标准

只有在以下条件满足后，才进入完整 structural counterfactual 阶段：

- 项目能清楚说明 Schulze and Xin (2025) 已经做了什么，以及本项目新增什么；
- connector rankings 和 value-added moments 足以约束模型 shock；
- direct bloc-to-bloc decline 与 third-country expansion 具有经济意义；
- 至少一个生产侧数据源支持关键 connector countries 存在真实 relocation，或者模型明确把 relocation 作为 scenario 而不是既定事实；
- extensive-margin evidence 与模型内生结果保持分开，只用于验证 nearshoring 叙事和约束 `hgamma`；
- country-sector concordance 透明且可复查；
- 模型输入可以在不硬编码国家 index 的情况下生成；
- welfare channels 可以区分 direct fragmentation、connector mitigation、MP channel 和 IO propagation。

如果这些条件不满足，项目应缩小到特定国家-部门案例，优先考虑 Mexico/North America extension，或者暂时停留在 validation 阶段，不应宣称完整 JMP 贡献。

## 12. References

This project should not cite only broad geoeconomic-fragmentation reports. The working reference stack has four roles: empirical connector facts, structural welfare accounting, MP-margin architecture, and data/policy-shock measurement.

1. Du, Xiayi, and Zi Wang. 2022. "Multinationals, Global Value Chains, and the Welfare Impacts of Economic Sanctions." Economics Letters. Direct source for the first structural model and welfare decomposition.
2. Ramondo, Natalia, and Andres Rodriguez-Clare. 2013. "Trade, Multinational Production, and the Gains from Openness." Journal of Political Economy. Key reference for iceberg MP costs and multinational-production share adjustment.
3. Tintelnot, Felix. 2017. "Global Production with Export Platforms." Quarterly Journal of Economics. Key reference for fixed-cost foreign investment and affiliate-entry models.
4. Bonadio, Barthelemy, Zhen Huo, Andrei A. Levchenko, and Nitya Pandalai-Nayar. 2021. "Global Supply Chains in the Pandemic." Journal of International Economics. Reference point for BHLP-style global supply-chain / IO counterfactual frameworks.
5. Schulze, Tatjana, and Weining Xin. 2025. "Demystifying Trade Patterns in a Fragmenting World." IMF Working Paper WP/25/129. Closest empirical benchmark for connector countries, trade reallocation, and trade rerouting.
6. Freund, Caroline, Aaditya Mattoo, Alen Mulabdic, and Michele Ruta. IMF-CEPR geoeconomic-fragmentation work on U.S.-China tariffs and connector economies. Background evidence on trade diversion, hidden dependence, and third-country export growth.
7. International Monetary Fund and CEPR. Geoeconomic Fragmentation: The Economic Risks from a Fractured World Economy. Policy background and fragmentation framing.
8. Bown, Chad P., plus PIIE / USTR / USITC Section 301 tariff files. Product-level tariff-shock source for `htau` scenarios.
9. OECD ICIO, OECD Analytical AMNE / MNE-GVC, BEA U.S. MNE Activity, CEPII BACI, fDi Markets, Mexico Secretaria de Economia / DataMexico FDI, and USITC USMCA automotive rules-of-origin reports. Data and calibration sources; final citations should record exact release versions, years, and table identifiers.
