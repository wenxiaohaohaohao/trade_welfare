# Connector Economies and the Hidden Cost of Geoeconomic Fragmentation

This repository develops an international-trade paper whose primary publication target is the *Journal of International Economics*. It studies the welfare value of connector economies: countries that expand as intermediaries or production locations when direct economic links between geopolitical blocs weaken.

The project is built from an existing structural reference package but is not a replication project. The reference package gives the core trade + multinational production + input-output model. Recent work already studies connector-country trade, production reallocation, FDI diversion, and trade-versus-MP welfare in broader forms. The intended contribution is therefore narrower: use observable ownership-linked affiliate adjustment to quantify how a trade-only model mismeasures connector economies' fragmentation insurance.

## JIE Project Standard / JIE 项目标准

The binding research-design standard is `docs/JIE_PROJECT_GOAL.md`, and the current-frontier claim boundary is `docs/JIE_GAP_AUDIT_2026_08_13.md`; both are tracked in `data-processing-variables@c46c671` and are not yet present in the current `codex/model` checkout. The organizing question is:

> **Among connector country-sector cells with comparable gross-trade rerouting, how much additional insurance is supplied by ownership-linked incumbent MP adjustment, and when does a trade-only model overstate or understate connector mitigation?**

All subsequent data, empirical, model, calibration, and welfare work must pass four gates: a unique frontier-level intellectual object; a new and auditable empirical fact or object; an MP mechanism disciplined by observable moments; and a first-order welfare result or informative disciplined zero. Additional datasets, countries, sectors, parameters, robustness checks, or model complexity do not count as progress unless they improve the estimand, discipline a first-order margin, or change the welfare conclusion.

Gate 1's **JIE Gap Audit** was completed on 2026-08-13. Gate 2/3 now require a bounded ownership-and-mapping pilot, not automatic full model migration after M6.4. The existing Du–Wang intensive-margin model and Scenario A/B/C design remain candidate testing architectures. They must be retained, redesigned, or replaced according to the JIE Gates rather than protected because of prior investment.

本项目的强制研究设计标准见 `docs/JIE_PROJECT_GOAL.md`，2026-08-13 的前沿对照和唯一 claim boundary 见 `docs/JIE_GAP_AUDIT_2026_08_13.md`；两者均已记录在 `data-processing-variables@c46c671`，但尚未进入当前 `codex/model` checkout。Gate 1 已完成；后续数据、经验识别、模型、calibration 和福利反事实必须服务于 trade-only connector-welfare prediction error，并通过其余 Gates。M6.4 之后不能机械迁移完整模型；下一步是 ownership-conditioned affiliate adjustment 与 parent-host-destination network 的 Gate 2/3 pilot。

## Current Data Notes / 当前数据说明

- BEA U.S. MNE MOFA country-industry tables now have a Batch 5 country-industry panel for 2017-2023 at `data/interim/mne/bea_us_mne_affiliate_country_industry.parquet`, with raw files archived under `data/raw/bea_mne/activities_us_mnes/`. The earlier `Mexico x Transportation equipment` 2020-2022 suppression audit remains the sector-specific North America check; see `data/bea_mne_mexico_transportation_equipment_2020_2022.md`.
- Official Mexico inward-FDI data are now archived and normalized. National quarterly totals and investment types cover 1999Q1-2024Q4; country/sector annual panels cover 1999-2024; detailed quarterly cross-tables cover 2006Q1-2024Q4. See `data/mexico_fdi_usage_note.md`.
- The official Section 301 base lists now generate an HTS10 event panel and a 2014-2024 HS2017 gross statutory exposure panel. The exact September 2024 modern-HTS increases are stored separately to avoid an invalid nomenclature merge. See `data/section301_usage_note.md`.
- fDi Markets is available through the user's access, but it is explicitly excluded from the current data batch. No fDi download or processing is part of the completion status below.
- The current data plan is: validated regular OECD ICIO baselines for IO objects; preserved Extended ICIO archives for a later China/Mexico ownership-split build; OECD Analytical AMNE and BEA U.S. MNE for multinational-production moments; official Mexico FDI for the 2021-2024 financial-flow bridge; and BACI plus Section 301 for product-level trade shocks. fDi Markets remains a later, separate project-level evidence source.
- 已构建 BEA U.S. MNE MOFA 的 Batch 5 country-industry panel，覆盖 2017-2023，输出为 `data/interim/mne/bea_us_mne_affiliate_country_industry.parquet`，原始文件归档在 `data/raw/bea_mne/activities_us_mnes/`。此前 `Mexico x Transportation equipment` 2020-2022 suppression audit 仍作为 North America 的专项行业检查记录；详见 `data/bea_mne_mexico_transportation_equipment_2020_2022.md`。
- Mexico 官方 inward FDI 已完成归档和标准化：全国季度总额和投资类型覆盖 1999Q1-2024Q4，来源国/行业年度面板覆盖 1999-2024，季度交叉明细覆盖 2006Q1-2024Q4；详见 `data/mexico_fdi_usage_note.md`。
- Section 301 官方初始清单已生成 HTS10 政策事件面板和 2014-2024 的 HS2017 gross statutory exposure 面板；2024 年 9 月的现代 HTS 精确调税表单独保存，避免错误跨版本合并；详见 `data/section301_usage_note.md`。
- fDi Markets 虽然可得，但使用者明确要求本批不处理。本批完成状态不包含 fDi 下载或变量构造。
- 当前数据策略是：已用 regular OECD ICIO 构造并验证 IO 基准，Extended ICIO 归档留待后续 China/Mexico ownership-split 构建；用 OECD Analytical AMNE 与 BEA U.S. MNE 构造 multinational-production moments；用 Mexico 官方 FDI 衔接 2021-2024 年金融流量证据；用 BACI 和 Section 301 构造产品层面贸易冲击。fDi Markets 留作以后单独处理的项目级证据。

## Current Project Progress / 当前项目进度（updated 2026-08-16）

| Workstream | Status | Current result / next gate |
|---|---|---|
| Public-data archive and source-specific builds | Complete for the current scope | BACI, U.S. Census imports, Section 301, OECD ICIO, OECD Analytical AMNE, BEA MNE, BEA direct investment, and Mexico official FDI have reproducible interim outputs and build summaries. fDi Markets is excluded from the current scope. |
| OECD ICIO model baselines | Complete for 2017, 2018, and 2022 | MATLAB-ready baseline CSVs exist under `data/model_inputs/icio_baseline_*/`. |
| Cross-source harmonization | Complete through M5.5 for the frozen scope | The validated country-sector-year trade/evidence interface and source-specific production contracts exist; their coverage and comparability limits remain explicit. |
| Empirical connector and production evidence | Complete through M6.3 as descriptive evidence | M6.1 ranking, M6.2 rerouting facts, and M6.3 source-specific production/activity validation are built and validated. They do not by themselves establish causality or pass JIE Gate 2. |
| Structural moments | Complete through M6.4 as observable targets | The Scenario A/B/C registry and value table exist, but all observations remain distinct from final `h_tau`/`h_gamma` parameters. JIE Gate 3 is not yet passed. |
| JIE Gate Audit, model migration, and welfare counterfactuals | Gate 1 complete; M6.5 otherwise pending | The 2026-08-13 audit fixes one headline and two supports. Gate 2 empirical construction, Gate 3 mapping/network discipline, model decision, solver, and Gate 4 welfare comparisons remain pending. |
| Reproducible processed-data release and collaborator handoff | M7 pending | The single full-rebuild entrypoint, final release manifest, Stata `.dta` exports and validation `.do`, collaborator handoff, and final `VERIFIED` audit package have not been completed. |

The historical collaborator-facing update is in `docs/data_and_project_progress_2026_07_19.md`. Current processing status is governed by `data/data_merge_checklist.md` and `docs/data_processing_audit_trail.md`; the research-design standard is `docs/JIE_PROJECT_GOAL.md`.

**Version boundary as of 2026-08-16:** the authoritative M0-M6.4 data-processing and JIE Gate 1 record is `data-processing-variables@c46c671`. The current `codex/model@2df0a06` checkout predates those 24 commits. Before further model work, create the model-pilot line from `c46c671` or integrate that history explicitly; the presence of generated Parquet files in the shared working directory is not a substitute for tracked code, validation, and manifests.

### OECD ICIO Batch 3 Baseline Outputs / OECD ICIO 第三批基准输出

The OECD ICIO 2025 edition raw archive is present locally under `data/raw/oecd_icio/`. The current validated build uses the 2017, 2018, and 2022 regular ICIO matrices because the first structural interface needs country-sector production, value added, final demand, bilateral absorption, and IO shares on the standard country-sector grid. Extended ICIO archives are preserved for later China/Mexico ownership or firm-type split work, but no Extended-derived ownership-split output has been built yet.

本地已经保存 OECD ICIO 2025 edition 原始数据，位置是 `data/raw/oecd_icio/`。当前完成验证的是 regular ICIO 的 2017、2018、2022 三个年度基准，因为第一版接口首先需要标准国家-部门网格上的 production、value added、final demand、bilateral absorption 和 IO shares。Extended ICIO 归档保留供后续 China / Mexico ownership 或 firm-type split 构建，但目前尚未生成 Extended-derived ownership-split 输出。

The reproducible build script is `code/data_build/build_oecd_icio_baseline.py`, with dependencies listed in `code/data_build/requirements-oecd-icio.txt`. It can be rerun with:

```powershell
python -m pip install -r code\data_build\requirements-oecd-icio.txt
python code\data_build\build_oecd_icio_baseline.py --overwrite
```

The script reads the OECD ReadMe workbook to recover row and column labels, processes the 2017, 2018, and 2022 regular ICIO matrices from `2016-2022_SML.zip`, writes cleaned parquet outputs to `data/interim/production/`, and exports MATLAB-ready baseline CSVs to `data/model_inputs/icio_baseline_2017/`, `data/model_inputs/icio_baseline_2018/`, and `data/model_inputs/icio_baseline_2022/`.

脚本会读取 OECD ReadMe workbook 中的 row / column labels，从 `2016-2022_SML.zip` 中处理 2017、2018、2022 三个 regular ICIO 年度矩阵，把清洗后的 parquet 输出写入 `data/interim/production/`，并把 MATLAB-ready baseline CSV 写入 `data/model_inputs/icio_baseline_2017/`、`data/model_inputs/icio_baseline_2018/` 和 `data/model_inputs/icio_baseline_2022/`。

The main intermediate outputs are:

| Output | Contents | Rows |
|---|---|---:|
| `data/interim/production/oecd_icio_output_va_fd.parquet` | Country-sector gross output, value added, final demand, intermediate inputs, exports, imports, and accounting support fields for 2017, 2018, and 2022. | 12,150 |
| `data/interim/production/oecd_icio_io_shares.parquet` | Long-form source-country-sector to destination-country-sector intermediate input shares. | 29,583,977 |
| `data/interim/production/oecd_icio_io_shares_2017.parquet` | 2017 long-form IO shares, kept for year-specific checks and model input manifests. | 9,672,450 |
| `data/interim/production/oecd_icio_io_shares_2018.parquet` | 2018 long-form IO shares, kept for year-specific checks and model input manifests. | 9,740,932 |
| `data/interim/production/oecd_icio_io_shares_2022.parquet` | 2022 long-form IO shares, kept for year-specific checks and model input manifests. | 10,170,595 |

The model input directories contain:

| File | Meaning |
|---|---|
| `X_baseline.csv` | Production-side gross output by `year`, `country_iso3`, and `sector_oecd`. |
| `va_baseline.csv` | Value added by `year`, `country_iso3`, and `sector_oecd`. |
| `IO_baseline.csv` | Wide matrix of intermediate-input shares; rows are source country-sector and columns are destination country-sector. |
| `trshare_baseline.csv` | Trade or absorption shares by origin country, destination country, and OECD sector. |
| `manifest.json` | File paths, schemas, units, and the corresponding long-form IO-share parquet file. |

字段口径如下。`gross_output` 使用生产端 `OUT` row；`gross_output_sales` 保留销售端 `OUT` column，主要用于 row-balance 检查。`value_added` 来自 `VA` row。`final_demand` 是 `HFCE`、`NPISH`、`GGFC`、`GFCF`、`INVNT` 和 `DPABR` 的合计。`intermediate_inputs` 是 destination country-sector 的全球中间投入 column sum。`taxes_less_subsidies` 来自 `TLS` row，保留为单独字段，不混入 value added。`exports` 是某个 origin country-sector 被所有外国 destination countries 吸收的中间需求和最终需求合计；`imports` 是某个 destination country-sector 从所有外国 origin countries 吸收的同一 OECD sector 产品合计。

Validation checks passed after the build. `oecd_icio_output_va_fd.parquet` has 12,150 rows, equal to 3 years times 81 country/ROW units times 50 sectors. The required fields `year`, `country_iso3`, `sector_oecd`, `gross_output`, `value_added`, `final_demand`, `intermediate_inputs`, `exports`, and `imports` are present. For `trshare_baseline.csv`, positive-absorption destination-country-sector groups sum to one up to numerical precision, with maximum error about `4.33e-15`. For the long-form IO shares, summing `input_share` by destination country-sector reconstructs `intermediate_inputs / gross_output` with maximum error about `3.33e-16`. OECD matrix accounting is not exactly balanced at every cell after rounding and statistical adjustments: the maximum production-side residual is about `82.032` million current USD, and the maximum sales-side residual is about `238.606` million current USD; these diagnostics are recorded in `data/interim/production/oecd_icio_build_summary.json`.

构建后的验证已经通过。`oecd_icio_output_va_fd.parquet` 有 12,150 行，等于 3 个年份 × 81 个 country / ROW 单元 × 50 个部门。最低字段 `year`、`country_iso3`、`sector_oecd`、`gross_output`、`value_added`、`final_demand`、`intermediate_inputs`、`exports` 和 `imports` 都存在。`trshare_baseline.csv` 在正吸收的 destination-country-sector 组内加总为 1，最大数值误差约为 `4.33e-15`。long-form IO shares 按 destination country-sector 加总后，可以回推出 `intermediate_inputs / gross_output`，最大误差约为 `3.33e-16`。由于 OECD 矩阵本身存在 rounding 和 statistical adjustment，单元格层面的 accounting 并非完全零残差：生产端最大残差约为 `82.032` million current USD，销售端最大残差约为 `238.606` million current USD；这些诊断结果记录在 `data/interim/production/oecd_icio_build_summary.json`。

## 1. Project In One Paragraph

When direct trade and multinational-production links between geopolitical blocs weaken, third countries can appear to "connect" the blocs. Existing work already shows trade rerouting, domestic production reallocation, affiliate/FDI diversion, and welfare effects from both trade and MP. This project therefore asks whether connector country-sector cells with similar gross-trade adjustment supply different amounts of insurance because their ownership-linked incumbent MP adjustment differs. The empirical layer must discipline the missing MP margin and the model must quantify the prediction error of trade-only connector welfare inference. Scenario A remains the trade-only lower bound, Scenario B the observable-moment-disciplined incumbent-MP comparison, and Scenario C only a separately labeled broad-production upper bound; financial FDI cannot directly calibrate `hgamma`.

## 2. Main Research Question

Among connector country-sector cells with comparable gross-trade rerouting, how much additional insurance against bloc fragmentation is supplied by ownership-linked incumbent multinational-production adjustment, and when does a trade-only model consequently overstate or understate connector mitigation?

The core distinction is:

- **real relocation**: connector countries expand production, foreign affiliate activity, value added, or local sourcing;
- **rerouting**: connector countries expand gross exports or imports but do not show comparable production-side expansion;
- **hidden dependence**: the final destination imports from a connector, but the connector remains highly dependent on inputs from the original source bloc.

## 3. Why This Can Be Competitive For JIE

The project is not just about documenting trade diversion. Schulze and Xin (2025), Shen (2026), Du and Wang (2022), and Xue (2026) jointly make the earlier broad positioning insufficient. The intended contribution must combine four elements:

1. a common country-sector empirical object showing when gross trade and ownership-linked affiliate adjustment diverge;
2. observable-moment discipline of the incumbent MP margin and explicit treatment of the parent-host-destination network;
3. a common-shock comparison that measures the prediction error of trade-only connector welfare inference;
4. transparent bounds, interaction treatment, and a willingness to report a disciplined zero.

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

### 4.0 Model Decision Before The Meeting With Professor Yu

**Decision status as of 2026-07-27: historically frozen until the discussion with Professor Yu; as of 2026-08-13 it remains the first candidate implementation, subject to the higher-order JIE Gate 3 test.**

Before that meeting, the first structural version will use **Du-Wang (2022) as the direct model and computational backbone**. Its theoretical lineage combines the trade-and-multinational-production framework of **Arkolakis, Ramondo, Rodríguez-Clare, and Yeaple (2018)** with a multisector input-output structure **à la Caliendo and Parro (2015)**. The first version will endogenize reallocation along already represented trade and MP links, including input-output propagation, but will **not** endogenize fixed-cost entry of new affiliates or plants.

Accordingly, the Du-Wang-based intensive-margin baseline, the A/B/C scenario design, model inputs, and welfare accounting remain the first implementation candidate. Extensive-margin evidence remains outside the structural model, and Scenario C remains a total MP-adjustment upper-bound proxy rather than an endogenous entry result. A **Tintelnot (2017)-style fixed-cost plant-location block** is not added merely for sophistication. Under the 2026-08-13 JIE contract, full Du-Wang migration now requires an observable-moment-to-MP mapping and a small quantitative pilot. If Du-Wang fails that test, the model boundary must be reopened; if affiliate or plant entry is both empirically supportable and central to the headline welfare result, a later version may augment or restructure the framework using Tintelnot's entry and export-platform mechanism.

### 4.1 Technical Check: How Du-Wang Models The MP Margin

The core model risk is whether Du-Wang can be used directly for this project's MP channel. The check is clear: Du-Wang models MP through an **iceberg MP cost**, not through a Tintelnot-style fixed-cost entry margin.

The paper states that a firm from origin country `i` can produce in country `ell` subject to an iceberg MP cost `gamma_iell^j >= 1`, with `gamma_ii^j = 1`. The firm's unit cost contains `gamma_iell^j` multiplied by the trade-cost term `kappa_elln^j`. The replication code implements the same structure: `eqm_update.m` constructs `hxi_4d` by multiplying `hgamma`, `hkappa`, wage changes, and intermediate-input price changes, then updates the MP and sourcing shares through `hpsi_4d` and `hlam_3d`.

This means `hgamma` should be interpreted as a change in MP variable cost, or a change in the effective cost of producing through a foreign affiliate location. It should **not** be interpreted as an entry fixed cost, an affiliate-entry threshold, or a firm-count relocation object. The reference code has no fixed-cost entry equation, no endogenous affiliate count, no binary entry decision, and no plant-level relocation margin.

The implication for this project is:

| Possible route | Assessment |
|---|---|
| Use Du-Wang with project-specific scenario/config refactoring | Recommended first version. It already has trade, MP, IO linkages, and welfare decomposition. |
| Add a project-specific scenario layer that disciplines the MP margin with AMNE, BEA MNE, and production-side moments | Needed. Direct affiliate evidence anchors Scenario B; ICIO and direct activity can bound Scenario C. Financial FDI is context only and cannot directly calibrate `hgamma`. Any source-host-destination allocation must be observed, restricted, or bounded. |
| Switch immediately to a BHLP/Bonadio-style framework with a new MP layer | Not recommended for the first version unless the project abandons the Du-Wang sufficient-statistics structure. It would increase model-building burden sharply. |
| Build a Tintelnot-style fixed-cost entry model | Only appropriate if the paper's core question becomes affiliate entry or plant-count relocation, which requires stronger micro or firm-level evidence. |

Therefore, Du-Wang is usable as the first structural backbone for connector welfare accounting, but only with a narrow interpretation: it can quantify welfare effects of trade-cost and MP-cost shocks. It cannot by itself prove that firms entered a connector country or that plants physically relocated there. Any claim about real production relocation must come from the empirical validation layer and then enter the model as disciplined `hgamma` scenarios. Scenario C should be described as an upper-bound proxy for total MP adjustment, not as a structural entry-margin estimate.

### 4.2 Model Boundary: Intensive Margin Versus New Entry

The paper should not claim that the Du-Wang model explains new firms entering Mexico after Section 301. The main model should be positioned as **intensive-margin welfare accounting**. It can answer how welfare changes when trade costs and effective MP variable costs change across already represented country-sector links. It cannot endogenously explain a Chinese, U.S., Korean, Japanese, or European firm opening a new plant in Mexico.

The project mechanisms remain valid if they are stated carefully:

| Mechanism | How the model can handle it | What remains outside the model |
|---|---|---|
| Trade rerouting / indirect sourcing | Changes in `htau`, sourcing shares, foreign intermediates, and IO propagation. | Product-level evidence that rerouting actually occurred. |
| MP relocation / nearshoring | Changes in `hgamma` that shift production intensity toward connector locations already represented in the MP-share system. | New affiliate entry, new plant announcements, and plant-count changes. |

This does not make the project nonviable. It changes the paper's contract with the reader. The structural model quantifies the welfare implications of connector access and effective MP-cost changes; the empirical section validates whether the nearshoring narrative has extensive-margin support and disciplines a bounded set of counterfactuals.

The first welfare table should therefore use three named connector scenarios:

| Scenario | Calibration logic | Interpretation |
|---|---|---|
| **Scenario A: trade-only connector lower bound** | Connector-related `htau` remains open or improves, while `hgamma = 1` for the MP margin. | Lower bound for connector value when third countries only reroute trade and MP costs do not improve. |
| **Scenario B: incumbent MP-intensive baseline** | `hgamma` is disciplined by AMNE, BEA MNE, or ownership/affiliate activity moments that mostly reflect already represented MP links. | Preferred baseline for intensive reallocation across existing MP links. |
| **Scenario C: broad production-adjustment upper-bound proxy** | ICIO production and direct affiliate expansion bound a stronger production response; financial FDI and future project evidence remain model-external context. | Upper-bound proxy for broad production adjustment; it does not directly calibrate `hgamma` or identify fixed-cost entry. |

The B-to-C gap can be reported as an extensive-margin-related upper-bound increment. It should not be described as an identified entry-margin welfare contribution, because the model has no fixed-cost entry block.

For a JIE-level paper, this boundary is acceptable only if the empirical and counterfactual discipline is strong. The first version should therefore add an explicit **extensive-margin evidence section outside the model**. Direct BEA MNE/AMNE activity and ICIO production can validate or bound production adjustment; financial FDI and any future project evidence remain narrative/extensive-margin support. They must not be converted directly into `hgamma` or described as entry generated by Du-Wang.

The recommended wording is:

> The structural model captures intensive reallocation across existing MP links. It does not endogenize entry of new affiliates or plants. We therefore treat greenfield FDI, new project announcements, and production-side expansion as model-external evidence that validates the nearshoring mechanism and disciplines a set of MP-cost counterfactuals. Scenario C is an upper-bound proxy for total MP adjustment, not a structural estimate of entry-margin welfare.

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

For the new connector-economy project, these scripts should be treated as a scenario template rather than a literal policy design. The Russia index `38`, China index `8`, and the hard-coded exempt-country list must be replaced by external country-group configuration files. The natural project-level counterfactual matrix should compare direct fragmentation with a disciplined A/B/C connector bound:

| New scenario | Shock object | Purpose |
|---|---|---|
| Baseline | `htau = 1`, `hgamma = 1`, `tTar = baseline tariffs` | Coherent pre-shock model equilibrium. |
| `NoConnector`: direct fragmentation with connector adjustment disabled | Increase `htau` and possibly `hgamma` on source-bloc to destination-bloc links while disabling connector-specific trade and MP adjustment. | Unique core fragmentation counterfactual for measuring the loss before connector insurance. |
| Scenario A: trade-only connector lower bound | Keep or reduce connector-related `htau` while direct bloc links remain costly; set connector MP margin to `hgamma = 1`. | Isolates gross trade rerouting through third countries and gives the lower bound for connector welfare value. |
| Scenario B: incumbent MP-intensive baseline | Use AMNE, BEA MNE, and ownership/affiliate activity moments to discipline connector-related `hgamma`. | Preferred baseline for intensive reallocation across existing MP links. |
| Scenario C: broad production-adjustment upper-bound proxy | Use ICIO production and direct affiliate expansion to bound a stronger production response. Financial FDI remains context; fDi Markets is outside the active batch. | Broad-production upper bound; not a calibrated `hgamma` or structural entry model. |
| Extreme connector-barrier robustness | Raise both direct-bloc and connector-bloc barriers beyond the core `NoConnector` contract. | More severe barrier robustness; not a second no-connector baseline. |

The first structural version should report welfare changes for each scenario and decompose them into direct fragmentation losses, connector mitigation, MP-intensive reallocation, the Scenario C upper-bound increment, and input-output propagation. The reference package can already compute welfare decomposition after a shock; what it cannot do is define connector countries, validate whether the connector channel is real rather than pure rerouting, or structurally identify fixed-cost entry.

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

Without this layer, the project would risk becoming a gross-trade rerouting exercise rather than a JIE-level contribution.

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
- Is there production-side evidence strong enough to justify Scenario B, Scenario C, or only Scenario A?

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

The purpose is to determine whether the structural model should report only Scenario A, add Scenario B, or also include Scenario C as an upper-bound proxy.

### 7.4 Small MATLAB-Ready Sample

Build a small sample with a limited country-sector set and export MATLAB-ready inputs similar to the reference `tomatlab/` files. This sample should test the interface before migrating the full model.

### 7.5 Structural Moment Table

Create a table that translates empirical facts into model moments:

- observed decline in direct bloc-to-bloc trade;
- observed increase in connector exports to the destination bloc;
- observed increase in connector imports from the source bloc;
- production-side expansion where available;
- FDI or foreign-affiliate activity where available;
- implied scenario choices for `htau` and `hgamma`;
- assignment of each moment to Scenario A, Scenario B, or Scenario C.

This table is the bridge between the existing empirical literature and the new welfare counterfactual.

### 7.6 Extensive-Margin Evidence Table

Create a separate table for project-level or firm-entry evidence. This table should not be folded into the Du-Wang model as an endogenous entry outcome. Its role is to validate the nearshoring narrative and discipline MP-cost scenarios.

The table should include:

- greenfield project counts and announced investment by host country, origin country, sector, and year;
- BEA MNE or AMNE affiliate activity where available;
- FDI, employment, value added, or investment indicators in the same sectors;
- a flag for whether the evidence supports an MP-intensive scenario, a trade-only scenario, or only a narrative motivation.

The model-facing output is not an entry equation. It is a documented mapping or bound with explicit failure conditions. Scenario B should be tied to incumbent or already represented MP activity; Scenario C should use ICIO production and direct affiliate expansion only as a broad-production upper bound. Financial FDI remains separate scenario context and must not directly determine `hgamma`.

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
| [OECD Analytical AMNE](https://www.oecd.org/en/data/datasets/multinational-enterprises-and-global-value-chains.html) / [AMNE](https://www.oecd.org/en/data/datasets/activity-of-multinational-enterprises.html) | Foreign-affiliate activity and multinational production | The current local build covers the 2008-2023 intersection and is the main ownership-split source for Scenario B. Affiliate employment is unavailable, and parent-country value added, exports, and imports are allocated using bilateral affiliate-output shares. |
| [fDi Markets](https://www.fdimarkets.com/) | Optional future greenfield FDI project evidence | Deferred by user instruction. If opened as a separate later batch, it may add project-level source/destination, sector, capex, and expected-jobs evidence for Scenario C. |
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
| OECD ICIO regular and Extended | Free, direct download | Regular ICIO baselines are built and validated for 2017, 2018, and 2022; Extended archives are preserved but not yet processed into ownership-split outputs | Regular tables provide the current IO baseline; Extended-derived China/Mexico ownership splits remain a separate future build |
| OECD Analytical AMNE | Free, direct download | Current local 2026-release build covers the 2008-2023 usable intersection, with bilateral-output raw coverage through 2024 | Most important structural source for Scenario B `hgamma`; employment is unavailable, and parent-level value added/trade fields are allocated rather than directly observed bilateral cells |
| BEA U.S. MNE Activity | Free, but selected detailed tables have discontinuities and some cells may be suppressed | Batch 5 local panel covers 2017-2023 for majority-owned foreign affiliates by country and industry, with employment, sales, value added, capital expenditures, and affiliate-side goods trade fields | Main bridge for U.S.-MNE affiliate activity in Mexico, Canada, Vietnam, and other connector countries; use suppression flags before sector-level interpretation |
| fDi Markets | Deferred by user instruction | No local export or constructed variables in the current batch | Optional later project-level evidence for Scenario C; it is not a current input or completed asset |
| BACI | Free, direct download | HS6 bilateral annual trade; latest release currently listed through 2024 | Preferred trade source for rerouting, connector rankings, and sector-level exposure to Section 301 shocks |
| Mexico Secretaria de Economia / DataMexico FDI | Free government data | National quarter/type panels cover 1999Q1-2024Q4; country/sector annual panels cover 1999-2024; detailed quarterly cross-tables cover 2006Q1-2024Q4 | Locally complete for the published vintage; confidential detail remains null and FDI is not an activity or plant-level measure |
| Section 301 tariff data | Free public data | Official Lists 1/2/3/4A, 2014-2024 gross HS2017 exposure, and a separate exact September 2024 modern-HTS table | Clean gross policy-shock layer for `htau`; not a realized-duty measure after exclusions |
| USITC USMCA auto reports | Free statutory reports | Auto-sector rules-of-origin evidence; exact table references must be verified before citation | Useful for the auto-sector distinction between genuine production integration and rerouting/shallow assembly |

The practical data bottleneck has changed. Official Mexico FDI and the gross Section 301 policy layer are now locally usable. Remaining limits are substantive rather than download failures: OECD Analytical AMNE and BEA have different activity concepts and time coverage; BEA and Mexico FDI detail can be suppressed; and FDI financial flows do not prove plant entry or production relocation. fDi Markets is outside the current batch by user instruction.

### Batch 4: OECD Analytical AMNE Affiliate Activity And MP Shares

Batch 4 converts the locally downloaded OECD Analytical AMNE files into two project-facing parquet outputs:

| Output | Role | Row scope |
|---|---|---|
| `data/interim/mne/oecd_amne_affiliate_activity.parquet` | Positive foreign-affiliate activity panel for empirical validation and Scenario B `hgamma` discipline. | Foreign parent country, host country, OECD sector, and year cells with strictly positive affiliate output. |
| `data/interim/mne/oecd_amne_mp_shares.parquet` | Model-facing MP-share panel. | Full foreign parent-host-sector-year universe, including zero-output links, so country-sector merges do not drop zero MP links. |

The build script is `code/data_build/build_oecd_amne.py`. It reads `aamne-bilateral-output.csv` and `aamne-mne-xvem.csv` from `data/raw/oecd_amne/analytical_amne/`, writes outputs to `data/interim/mne/`, and leaves raw files unchanged. Regenerate the outputs with:

```powershell
python code\data_build\build_oecd_amne.py --project-root . --overwrite
```

Core construction:

| Field | Construction |
|---|---|
| `affiliate_output` | Off-diagonal parent-host-sector output from `aamne-bilateral-output.csv`, in current million USD. Domestic diagonal cells are excluded. |
| `affiliate_value_added` | Foreign-owned XVEM aggregate `GVA` allocated to parent countries by parent affiliate-output share within each host-sector-year. |
| `affiliate_exports` | Foreign-owned XVEM aggregate `EXGR` allocated by parent affiliate-output share. |
| `affiliate_imports` | Foreign-owned XVEM aggregate `IMGR` allocated by parent affiliate-output share; OECD describes this as intermediate-input imports by firms. |
| `affiliate_employment` | Required column retained as null because these OECD Analytical AMNE files do not provide employment. Use BEA MNE or national data for current employment evidence; fDi Markets jobs would require a separate future batch. |
| `ownership_type` | `F`, meaning foreign-owned firms. |

The two model-facing variables are:

```text
MPEexpansion_{c,s,t} = ForeignAffiliateOutput_{c,s,t} - ForeignAffiliateOutput_{c,s,t-1}
ForeignAffiliateShare_{c,s,t} = ForeignAffiliateOutput_{c,s,t} / GrossOutput_{c,s,t}
```

In the parquet outputs, these are stored as `mpe_expansion` and `foreign_affiliate_share`. The file also keeps `mp_output_share`, the parent-specific affiliate output divided by host-sector gross output, and `parent_affiliate_output_share`, the weight used to allocate value added, exports, and imports across parent countries.

The important limitation is that parent-country output is directly observed in `aamne-bilateral-output.csv`, but parent-country value added, exports, and imports are not. Those three fields are allocated from the host-sector foreign-owned aggregate in `aamne-mne-xvem.csv`. They are valid as documented Scenario B discipline variables, but should not be described as directly reported parent-country AMNE value added or trade cells.

Current validation:

| Check | Result |
|---|---|
| Years | 2008-2023 |
| Host economies | 81 |
| Parent economies | 81 |
| Sectors in `oecd_amne_mp_shares.parquet` | 41 |
| Positive-affiliate sectors in `oecd_amne_affiliate_activity.parquet` | 39; `O84` and `T97T98` have zero foreign-owned `GO` in the raw XVEM file. |
| Rows in `oecd_amne_affiliate_activity.parquet` | 1,260,053 |
| Rows in `oecd_amne_mp_shares.parquet` | 4,250,880 |
| `foreign_affiliate_share` formula residual | 0 |
| `mpe_expansion` year-over-year residual | 0 |
| Allocated value added, exports, and imports summed back to XVEM foreign-owned aggregates | Floating-point precision residual only. |
| Bilateral output versus XVEM foreign-owned `GO` | Maximum absolute difference is about 0.113 million USD, consistent with small rounding differences across OECD files. |

Interpretation for the paper: the AMNE outputs support incumbent MP-intensive evidence and disciplined `hgamma` scenarios. They can show whether foreign-affiliate output and ownership-split activity expand in connector host countries and sectors. They do not prove firm-level relocation, plant entry, or new affiliate entry; those claims must stay in the model-external evidence layer and be combined with BEA, FDI, or national production sources. fDi Markets can be considered only in a separate future batch.

### Official Section 301 And Mexico FDI Batches

The Section 301 batch uses 10,115 official base-list rows and action-date USITC HTS files to build `data/interim/policy/section301_hts10_list_panel.parquet` (32,357 unique event rows). It then combines China-origin 2017 Census HTS10 weights with a dedicated CEPII BACI HS2017 U.S.-import denominator to build `data/interim/policy/section301_hs6_exposure.parquet` (55,308 HS6-year rows for 2014-2024). The exposure is a gross statutory schedule: List 4B is excluded because it never took effect, while historical product exclusions are not applied as realized customs-duty adjustments. The September 2024 four-year-review rates are stored in the separate 367-row `data/interim/policy/section301_2024_review_codes.parquet` because those modern HTS codes cannot be safely merged to a 2017 denominator by truncating them to HS6. Complete commands, source hashes, formulas, code aliases, and interpretation limits are in `data/section301_usage_note.md`.

Mexico official inward FDI is downloaded from Secretaría de Economía's datos.gob.mx files and Data México API. Nine parquet outputs under `data/interim/fdi/` cover national totals, investment types, source countries, SCIAN sectors, states, and their available cross-tables. National quarterly coverage is 1999Q1-2024Q4; detailed quarterly cross-tables begin in 2006. Official `C` cells remain null with `confidential_flag=true`, and `Total general` source-country rows are flagged to prevent double counting. The 2024 national total is USD 36,872.421 million. See `data/mexico_fdi_usage_note.md` for all paths, row counts, fields, and reconciliation gaps.

Section 301 本批构造的是 gross statutory exposure，不是扣除历次 exclusions 后的实际缴税额。Mexico FDI 本批保留官方保密值为空，不能把 `C` 当作 0，也不能把 country/sector 明细强行加总到全国总额。fDi Markets 明确不在本批处理范围内。

### 8.3.1 BEA U.S. MNE Batch 5: Affiliate Country-Industry Panel

Batch 5 uses BEA **Activities of U.S. Multinational Enterprises**, specifically majority-owned foreign affiliates of U.S. MNEs. The release page is `https://www.bea.gov/news/2025/activities-us-multinational-enterprises-2023`; the downloadable comprehensive table path is `https://www.bea.gov/international/di1usdop`.

The current local build covers **2017-2023**. This is the correct window for the current project because it gives a pre-Section-301 baseline, the tariff-war period, the COVID disruption years, and the 2021-2023 nearshoring period. If the project later needs years before 2017, those earlier BEA annual files should be downloaded and validated as a separate extension.

Local files:

| Item | Path |
|---|---|
| Build script | `code/data_build/build_bea_us_mne_affiliate_country_industry.py` |
| Raw XLS archive | `data/raw/bea_mne/activities_us_mnes/` |
| Raw-file manifest | `data/raw/bea_mne/metadata/bea_us_mne_activities_manifest.json` |
| Clean panel | `data/interim/mne/bea_us_mne_affiliate_country_industry.parquet` |
| Usage note | `data/bea_us_mne_affiliate_country_industry_usage_note.md` |

Core variables:

| Variable | BEA table | Unit | Meaning |
|---|---|---|---|
| `year` | All source tables | Calendar year | Observation year, currently 2017-2023. |
| `affiliate_country` | All source tables | Text | BEA affiliate country or area row. Use `bea_area_type` to separate country rows from aggregate geography rows. |
| `industry` | All source tables | Text | BEA industry of affiliate. |
| `employment` | Table II.G 1 | Thousands of employees | Employment of majority-owned foreign affiliates. |
| `sales` | Table II.D 3 | Millions of dollars | Sales by majority-owned foreign affiliates. |
| `value_added` | Table II.F 3 | Millions of dollars | Value added of majority-owned foreign affiliates. |
| `capital_expenditures` | Table II.C 4 | Millions of dollars | Expenditures for property, plant, and equipment by affiliates. |
| `goods_exports_to_us` | Table II.H 11 | Millions of dollars | U.S. imports of goods shipped by affiliates; read from the affiliate side as goods exported to the United States. |
| `goods_imports_from_us` | Table II.H 3 | Millions of dollars | U.S. exports of goods shipped to affiliates; read from the affiliate side as goods imported from the United States. |

BEA suppression is handled explicitly. `(D)` cells are missing, not zero. Employment size-range codes `A/F/G/H/I/J/K/L/M` are also treated as suppressed numeric values. `(*)` is a rounded small value and is stored as `0.0` with a small-value flag. Each core variable has companion `*_raw_code`, `*_suppressed`, and `*_small_value` fields so sector-country moments can be checked before they are used to discipline `hgamma`.

### 8.4 What Additional Data Would Make The Project More Mature

For a JIE-level paper, the public-data version is feasible only if the research design is disciplined. The project should not overclaim firm-level relocation from aggregate evidence. The strongest version would add one or more of the following data layers:

| Additional data | Why it matters |
|---|---|
| Firm-level data such as Orbis, local business registries, or customs-linked firm data | Directly identifies firms, ownership, subsidiaries, industry, location, employment, revenue, and possibly entry or expansion in connector countries. |
| Plant-level or establishment-level manufacturing data | Separates genuine capacity expansion from simple trading-company activity. |
| Shipment-level data such as Panjiva, Datamyne, or ImportGenius | Tracks supplier-consignee links and can show whether Chinese suppliers ship to connector-country exporters that then ship to U.S. buyers. |
| Greenfield investment project data, if a separate batch is later opened | Improves validation of announced projects, cancellations, and follow-up operation status. |
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
| `docs/JIE_PROJECT_GOAL.md` | Binding JIE publication standard, four Gates, referee tests, and decision contract. |
| `docs/research_design.md` | Research question, mechanism, feasibility tests, and risks. |
| `docs/reference_model_map.md` | Detailed map from reference code to future model-core code. |
| `docs/data_source_log.md` | Data-source registry and download log. |
| `docs/phase1_feasibility_memo_template.md` | Template for deciding whether the project has enough first-stage signal. |
| `configs/` | Active country, sector, time-window, source-version, and Census mapping definitions; executable scenario files remain pending. |
| `code/data_build/` | Reproducible builders for the current trade, policy, production, MNE, and FDI data layers. |
| `code/analysis/` | Project-document utility plus the future location for connector rankings, figures, and production-side validation. |
| `code/model_core/` | Future MATLAB model code migrated from the reference package. |
| `data/` | Data documentation and ignored data folders. |
| `output/` | Regenerable tables, figures, logs, and memos. |
| `reference/` | Local read-only reference materials; ignored by git. |

## 10. Current Status

The current public-data engineering stage is substantially complete. Reproducible Python builders and validated interim outputs now exist for BACI, U.S. Census imports, Section 301, OECD ICIO, OECD Analytical AMNE, BEA U.S. MNE activity, BEA direct investment, and Mexico official FDI. OECD ICIO baseline CSVs are available for 2017, 2018, and 2022.

The validated data workflow is complete through M6.4. Gate 1 was completed in `docs/JIE_GAP_AUDIT_2026_08_13.md`; the surviving headline is the observable-MP-disciplined prediction error of trade-only connector welfare models. Gate 2, Gate 3, Gate 4, the remainder of M6.5, final moment-to-MP mapping, trilateral-network treatment, model decision, shock arrays, MATLAB equilibrium/welfare code, and counterfactual results remain unfinished. M7 reproducible release and handoff are also pending. Therefore, the accurate status is: **core data engineering and the empirical moment bank are complete and validated; the end-to-end data stage is not yet complete or model-ready**. fDi Markets is explicitly outside the current batch.

## 11. Immediate Next Steps

1. Canonicalize the Gate 2 same-window trade/AMNE affiliate-share-and-level object and its measurement uncertainties.
2. Add the targeted ownership-conditioned incumbent parent-host AMNE transformation; keep entry/exit separate.
3. Complete the Gate 3 mapping from admissible moments to `hgamma`, an MP elasticity, or a transparent bound, and observe/restrict/bound the parent-host-destination network when the mechanism requires it.
4. Freeze one core `NoConnector` shock contract and the comparable `TradeConnector`, `Trade+MPConnector`, and conditional `FullNetworkAdjustment` contracts.
5. Only after Gates 1-3 support it, build a small model pilot to test mechanism relevance, numerical validity, and the potential Gate 4 welfare separation. Do not begin full Du-Wang migration mechanically.
6. After the M6.5 decision, complete M7 full-rebuild, version-freeze, Stata handoff, and final audit artifacts before declaring the data stage complete or beginning full model migration.

## 12. Decision Rule For Moving To Structural Counterfactuals

Move beyond a small model pilot only after M6.5 records explicit evidence for Gate 1 (frontier-level intellectual object), Gate 2 (new auditable empirical fact/object), and Gate 3 (observable-moment discipline of the first-order MP margin), and after the Gate 4 pilot design has unique, comparable shock contracts and numerical acceptance tests. M6.1-M6.4 validation PASS does not satisfy these Gates by itself.

At that decision, answer the Novelty, Discipline, and Quantitative-payoff referee tests in `docs/JIE_PROJECT_GOAL.md`. If any answer is missing, choose a targeted missing input, pause, model switch, or narrower claim—not unrelated data expansion or arbitrary `hgamma` calibration.

---

# 中文版项目介绍

## 双语维护规则

从本节加入开始，根目录 `README.md` 同时包含英文版和中文版项目说明。以后如果更新项目定位、研究问题、数据来源、模型复用规则、目录结构、下一步计划或进入结构模型的判断标准，必须同时更新英文部分和中文部分，避免合作者看到两个版本时得到不一致的信息。

## 1. 项目一句话

本项目研究 geoeconomic fragmentation 背景下 trade-only connector welfare inference 的误差：当两个地缘政治集团之间的直接贸易和跨国生产联系变弱时，具有相似 gross-trade rerouting 的第三方 country-sector cells，是否因为 ownership-linked incumbent MP adjustment 不同而提供不同的 fragmentation insurance。Scenario A 是 trade-only 下界，Scenario B 是由 direct affiliate activity 约束的 incumbent-MP 比较，Scenario C 只能是单独标记的 broad-production 上界；financial FDI 不能直接校准 `hgamma`。

本项目不是对现有文献的简单复现。`reference/` 中的 Du and Wang (2022) 复现包提供了一个非常有用的结构模型框架：多国、多部门、同时包含 trade、multinational production 和 input-output linkages。但最新的 IMF Working Paper 已经覆盖了相当一部分 connector economies 的实证识别。因此，本项目不能把“区分生产转移和贸易绕行”作为主贡献，而应把它作为模型校准和验证的事实基础。

## 2. 核心研究问题

本项目的主问题是：

> 在 gross-trade rerouting 相近的 connector country-sector cells 中，ownership-linked incumbent MP adjustment 额外提供多少 bloc-fragmentation insurance？忽略这一 margin 的 trade-only model 会在什么条件下高估或低估 connector mitigation？

这里需要严格区分三种现象：

- **真实生产转移**：connector countries 的生产、foreign affiliate activity、value added、本地采购或就业同步增加。
- **贸易绕行**：connector countries 的进口或出口增加，但没有相应的本地生产扩张证据。
- **隐藏依赖**：最终目的国表面上从 connector country 进口，但 connector country 本身仍高度依赖原始来源集团的中间投入。

如果不能区分这三类现象，项目很容易退化为一个 gross trade diversion 的描述性研究。更重要的是，Schulze and Xin (2025) 已经系统做了这一区分，所以本项目必须把贡献推进到结构福利反事实。

## 3. 为什么这个题目有 JIE 潜力

这个题目不是简单地问“贸易是否转移到第三国”。Schulze and Xin (2025)、Shen (2026)、Du and Wang (2022) 和 Xue (2026) 共同使原来的宽定位不再充分。本项目的潜在贡献必须同时包含四个层面：

1. **同单位经验事实**：在同一 country-sector 和同一窗口比较 gross trade 与 ownership-linked affiliate adjustment。
2. **MP discipline**：用 direct affiliate activity 约束 incumbent MP margin，并明确处理 parent-host-destination network。
3. **预测误差**：在共同 shock 和 closure 下量化 trade-only connector welfare inference 的方向和大小。
4. **可信边界**：报告参数、网络和 interaction bounds，并接受 data-disciplined zero。

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

### 4.0 与俞老师讨论前的模型决定

**截至 2026-07-27，本决定曾作为与俞老师讨论前的模型冻结点；自 2026-08-13 起，它仍是第一候选实现，但必须服从更高层级的 JIE Gate 3 检验。**

见俞老师之前，第一版结构模型确定为：以 **Du-Wang（2022）作为直接模型和计算骨架**。其理论来源是 **Arkolakis、Ramondo、Rodríguez-Clare and Yeaple（2018）**的 trade–multinational-production 框架，以及 **Caliendo and Parro（2015）**式的多部门投入产出结构。第一版内生计算已有 trade 和 MP links 上的重新配置及 IO propagation，但**不内生化新 affiliate 或新 plant 的 fixed-cost entry**。

因此，Du-Wang-based intensive-margin baseline、A/B/C 情景、模型输入和福利核算仍是第一候选实现。Extensive-margin evidence 继续放在结构模型之外，Scenario C 仍是 total MP-adjustment upper-bound proxy，不解释为 endogenous entry result。不能仅为提高复杂度而加入 **Tintelnot（2017）式 fixed-cost plant-location block**。根据 2026-08-13 生效的 JIE contract，完整迁移 Du-Wang 前必须完成 observable-moment-to-MP mapping 和小型 quantitative pilot；如果 Du-Wang 无法通过该检验，就必须重新讨论模型边界。只有 affiliate 或 plant entry 同时有经验支持且决定 headline welfare result 时，后续版本才考虑用 Tintelnot 的 entry 与 export-platform mechanism 扩展或重构。

### 4.1 Du-Wang 的 MP margin 到底是什么

当前最关键的模型风险，是 Du-Wang 能不能直接承担本项目的 MP channel。核验结果很明确：Du-Wang 的 MP margin 是 **iceberg MP cost**，不是 Tintelnot 式的 fixed-cost entry margin。

论文正文写明，origin country `i` 的企业可以在 production location `ell` 生产，但要面对 `gamma_iell^j >= 1` 的 iceberg MP cost，且 `gamma_ii^j = 1`。企业的 unit cost 里，`gamma_iell^j` 与 trade-cost term `kappa_elln^j` 连乘。复现代码也完全对应这一点：`eqm_update.m` 把 `hgamma`、`hkappa`、工资变化和中间品价格变化一起乘进 `hxi_4d`，再通过 `hpsi_4d` 和 `hlam_3d` 更新 MP share 与 sourcing share。

因此，`hgamma` 应解释为 MP variable cost 的变化，也就是通过 foreign affiliate location 组织生产的有效成本变化。它不应被解释为进入固定成本、affiliate entry threshold、企业数量变化或 plant relocation。复现代码中没有 fixed-cost entry 方程，没有内生 affiliate count，没有 binary entry decision，也没有 plant-level relocation margin。

对本项目的含义如下：

| 路线 | 判断 |
|---|---|
| 在 Du-Wang 上重构情景配置和数据接口 | 推荐作为第一版。它已经包含 trade、MP、IO linkages 和 welfare decomposition。 |
| 用 AMNE、BEA MNE 和生产侧 moments 约束 MP margin | 必须做。Direct affiliate activity 主要约束 Scenario B；ICIO 与 direct production activity 可界定 Scenario C。Financial FDI 只作 context，不能直接校准 `hgamma`；三边网络必须被观测、限制或界定。 |
| 直接转向 BHLP / Bonadio 风格框架并自行加入 MP 层 | 第一版不推荐。除非放弃 Du-Wang 的 sufficient-statistics 结构，否则建模负担会明显上升。 |
| 改成 Tintelnot 式 fixed-cost entry model | 只有当论文核心变成 affiliate entry 或 plant-count relocation 时才需要，而且需要更强的微观或企业层面证据。 |

结论是：Du-Wang 可以作为 connector welfare accounting 的第一版结构骨架，但解释必须收窄。它能计算 trade-cost 和 MP-cost shock 的福利影响；它不能单独证明企业进入了 connector country，也不能证明工厂发生了物理迁移。真实 production relocation 的证据必须来自经验验证层，然后再作为有依据的 `hgamma` 情景进入模型。Scenario C 必须写成 total MP adjustment 的 upper-bound proxy，不能写成结构识别出来的 entry-margin welfare estimate。

### 4.2 模型边界：intensive margin 与新企业进入

论文不应声称 Du-Wang 模型能解释 Section 301 之后中国企业或其他跨国企业在墨西哥新设工厂。主模型应定位为 **intensive-margin welfare accounting**：它能回答的是，当贸易成本和有效 MP variable cost 在已有国家-部门连接上变化时，生产份额、贸易份额、中间品可得性和福利如何变化。它不能内生解释一个企业是否进入墨西哥、是否新建 affiliate、是否增加 plant count。

项目的两条机制仍然成立，但必须这样表述：

| 机制 | 模型可以解释什么 | 模型外需要补什么 |
|---|---|---|
| Trade rerouting / indirect sourcing | 通过 `htau`、sourcing shares、foreign intermediates 和 IO propagation 解释福利变化。 | 产品层面的贸易数据证明 rerouting 确实发生。 |
| MP relocation / nearshoring | 通过 `hgamma` 下降解释已有或模型中已表示的 MP link 上生产强度向 connector location 调整。 | 新 affiliate、新工厂公告、plant count 或 firm entry 证据。 |

这并不意味着项目不能达到 JIE 水平。它意味着论文必须和读者订清楚契约：结构模型量化 connector access 和 effective MP-cost changes 的福利含义；经验部分验证 nearshoring 是否有 extensive-margin 支持，并用这些证据约束 `hgamma` 的情景区间。

第一组 welfare table 应使用三个命名情景：

| Scenario | 校准逻辑 | 解释 |
|---|---|---|
| **Scenario A: trade-only connector lower bound** | connector 相关 `htau` 保持开放或下降，但 MP margin 保持 `hgamma = 1`。 | 只允许贸易绕行，给出 connector welfare value 的下界。 |
| **Scenario B: incumbent MP-intensive baseline** | 用 AMNE、BEA MNE、ownership / affiliate activity moments 约束 connector 相关 `hgamma`。 | 基准情景，解释已有或模型中已表示的 MP links 上的 intensive reallocation。 |
| **Scenario C: broad production-adjustment upper-bound proxy** | 用 ICIO production 和 direct affiliate expansion 界定更强的 production response；financial FDI 和以后可能的 project evidence 只作模型外 context。 | Broad-production 上界；不直接校准 `hgamma`，也不声称模型内生 fixed-cost entry。 |

B 到 C 的差值可以报告为 extensive-margin-related upper-bound increment，但不能称为识别出来的 entry-margin welfare contribution，因为模型没有 fixed-cost entry block。

因此，第一版应增加一个模型外的 **extensive-margin evidence section**。BEA MNE、AMNE、value added、employment 和 capex 用于核对 direct activity；FDI 与以后可能的 project evidence 只作金融或 entry-context 证据。Scenario C 由 ICIO 与 direct affiliate activity 界定 broad-production 上界，不能把 FDI 直接变成 `hgamma`，也不能把新进入写成 Du-Wang 的内生结果。

推荐表述是：

> The structural model captures intensive reallocation across existing MP links. It does not endogenize entry of new affiliates or plants. We therefore treat greenfield FDI, new project announcements, and production-side expansion as model-external evidence that validates the nearshoring mechanism and disciplines a set of MP-cost counterfactuals. Scenario C is an upper-bound proxy for total MP adjustment, not a structural estimate of entry-margin welfare.

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

这些脚本对本项目的价值不在 Russia 本身，而在于它们提供了一个可改造的 counterfactual 结构：直接切断、只切断 trade、同时切断 trade 和 MP、以及保留第三方国家通道。新项目应把这种结构改写为 direct fragmentation 加 A/B/C connector bounds 的情景矩阵：

| 新项目场景 | shock 对象 | 目的 |
|---|---|---|
| Baseline | `htau = 1`、`hgamma = 1`、`tTar = baseline tariffs` | 得到一致的冲击前均衡。 |
| `NoConnector`：direct fragmentation 且关闭 connector adjustment | 提高 source bloc 与 destination bloc 之间的 `htau`，必要时同时提高 `hgamma`，并关闭 connector-specific trade/MP adjustment。 | 唯一核心碎片化基准，衡量连接机制介入前的直接脱钩福利成本。 |
| Scenario A: trade-only connector lower bound | 直接 bloc-to-bloc link 仍然变贵，但 connector 相关 `htau` 保持开放或成本较低，connector MP margin 设为 `hgamma = 1`。 | 单独识别 gross trade rerouting，并给出 connector welfare value 的下界。 |
| Scenario B: incumbent MP-intensive baseline | 用 AMNE、BEA MNE 和 ownership / affiliate activity moments 约束 connector 相关 `hgamma`。 | 基准情景，衡量已有 MP links 上的 intensive production reallocation。 |
| Scenario C: broad production-adjustment upper-bound proxy | 用 ICIO production 和 direct affiliate expansion 界定更强的 production response；financial FDI 与 fDi Markets 不直接校准 `hgamma`。 | Broad-production 上界；不声称有结构 entry model。 |
| Extreme connector-barrier robustness | 在核心 `NoConnector` contract 之外，进一步提高 direct bloc links 和 connector links 的 trade/MP barriers。 | 更严重的 barrier robustness，不作为第二个 no-connector 基准。 |

因此，本项目后续的 counterfactual 不应再写成“Russia = 38、China = 8”。所有 source bloc、destination bloc、connector countries、sector list、shock intensity 和年份都应从 `configs/` 读取。结构模型输出也应明确分解为 direct fragmentation、Scenario A trade-only mitigation、Scenario B incumbent MP-intensive reallocation、Scenario C upper-bound increment 和 IO propagation。

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
- 是否有足够生产侧证据支持 Scenario B、Scenario C，还是只能支持 Scenario A？

只有这些校准和验证事实成立，结构模型才值得迁移。

## 7. 第一阶段经验验证与模型校准计划

第一阶段目标不是跑完整结构模型，也不是重复 Schulze and Xin (2025) 已经完成的实证识别，而是判断本项目是否有足够可靠的模型输入和 counterfactual 依据。

需要完成六个输出：

1. **literature benchmark table**：把 Schulze and Xin (2025) 的样本、数据、方法和结论列清楚，明确本项目不重复哪些贡献。
2. **connector ranking table**：按国家和部门识别 connector candidates，并与 IMF paper 的亚洲样本结果对照。
3. **North America extension figure**：重点检查 Mexico 和 Canada 是否存在与亚洲样本不同的 connector 机制。
4. **production-side validation table**：检查贸易增长是否伴随 AMNE、value added、gross output、FDI 或其他生产侧指标增长。
5. **extensive-margin evidence table**：当前整理 BEA MNE、AMNE、FDI 或其他生产侧资料中的 affiliate、投资和就业证据，明确它们是模型外验证，不是 Du-Wang 的内生结果。fDi Markets 本批不进入该表。
6. **small MATLAB-ready sample**：构造一个小样本，测试新数据能否进入 reference 模型接口。

此外，还需要一张 **structural moment table** 区分 observed moments 与模型参数：direct bloc-to-bloc trade decline、connector exports/imports、direct production/foreign-affiliate activity 可以成为 calibration 或 validation targets；FDI 只能作为 financial scenario support。只有明确的 moment-to-`htau`/MP-object mapping、网络边界和失败条件存在时，才可以进入小型 MATLAB pilot。

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
| [OECD Analytical AMNE](https://www.oecd.org/en/data/datasets/multinational-enterprises-and-global-value-chains.html) / [AMNE](https://www.oecd.org/en/data/datasets/activity-of-multinational-enterprises.html) | 外资企业活动和跨国生产 | 当前本地可用交集覆盖 2008-2023，是约束 Scenario B `hgamma` 的核心 ownership-split 数据。affiliate employment 不可得，parent-country 的 value added、exports 和 imports 按 bilateral affiliate-output share 分配。 |
| [fDi Markets](https://www.fdimarkets.com/) | 以后可选的 greenfield FDI project evidence | 按使用者要求暂缓。以后如单独开启新批次，可补充 Scenario C 所需的项目来源地、目的地、行业、capex 和预期就业证据。 |
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
| OECD ICIO regular 和 Extended | 免费，直接下载 | regular ICIO 已完成 2017、2018、2022 基准构建和验证；Extended 归档已保留，但尚未生成 ownership-split 输出 | regular tables 是当前 IO baseline；China/Mexico Extended ownership split 仍是后续独立构建任务 |
| OECD Analytical AMNE | 免费，直接下载 | 当前本地 2026 release 构建的可用交集为 2008-2023，bilateral output 原始覆盖到 2024 | 是约束 Scenario B `hgamma` 的最关键结构数据；employment 不可得，parent-level value added 和 trade 是分配值而非直接报告的 bilateral cells |
| BEA U.S. MNE Activity | 免费，但部分细表停更且个别国家-行业单元可能 suppressed | Batch 5 本地面板覆盖 2017-2023，口径为 majority-owned foreign affiliates 的 country-industry activity，包括 employment、sales、value added、capital expenditures 和 affiliate-side goods trade | 是 Mexico、Canada、Vietnam 及其他 connector countries 的 U.S.-MNE affiliate activity 桥接数据；行业解释前必须查看 suppression flags |
| fDi Markets | 按使用者要求暂缓 | 当前没有本地导出或构造变量 | 以后可作为 Scenario C 的项目级补充证据；不是当前输入或已完成资产 |
| BACI | 免费，直接下载 | HS6 年度双边贸易，当前最新版本覆盖到 2024 | 贸易绕行、connector ranking 和 Section 301 暴露的首选贸易数据 |
| Mexico Secretaria de Economia / DataMexico FDI | 免费政府数据 | 全国季度/投资类型覆盖 1999Q1-2024Q4，来源国/行业年度覆盖 1999-2024，季度交叉明细覆盖 2006Q1-2024Q4 | 当前官方 vintage 已完整保存；保密明细为空，且 FDI 不是 activity 或 plant-level measure |
| Section 301 tariff data | 免费公开 | 官方 List 1/2/3/4A、2014-2024 gross HS2017 exposure，以及单独的 2024 年 9 月现代 HTS 精确调税表 | 用于构造 `htau` 的 gross policy-shock 层；不是扣除 exclusions 后的 realized-duty measure |
| USITC USMCA auto reports | 免费法定报告 | 汽车部门 rules-of-origin 证据；具体表格和定义引用前必须复核 | 对区分真实生产整合与 rerouting / shallow assembly 特别有用 |

因此，实际数据瓶颈已经改变。Mexico 官方 FDI 与 Section 301 gross policy layer 已经可以本地使用。剩余限制主要是统计口径而不是下载失败：OECD AMNE 与 BEA 的 activity 概念和时间覆盖不同；BEA 与 Mexico FDI 明细存在 suppression；FDI 金融流量本身不能证明 plant entry 或 production relocation。fDi Markets 按使用者要求不在本批处理范围内。

### Batch 4：OECD Analytical AMNE affiliate activity 与 MP shares

Batch 4 把本地下载的 OECD Analytical AMNE 文件转换成两个项目可直接使用的 parquet 输出：

| 输出 | 作用 | 行口径 |
|---|---|---|
| `data/interim/mne/oecd_amne_affiliate_activity.parquet` | 正值 foreign-affiliate activity panel，用于经验验证和 Scenario B 的 `hgamma` 约束。 | parent country、host country、OECD sector、year 层面，且 `affiliate_output` 严格大于 0。 |
| `data/interim/mne/oecd_amne_mp_shares.parquet` | 面向模型的 MP-share panel。 | 完整 foreign parent-host-sector-year universe，包括 zero-output links，避免后续 country-sector 合并时丢掉零 MP link。 |

构建脚本是 `code/data_build/build_oecd_amne.py`。脚本读取 `data/raw/oecd_amne/analytical_amne/` 下的 `aamne-bilateral-output.csv` 和 `aamne-mne-xvem.csv`，输出到 `data/interim/mne/`，不修改 raw 文件。重新生成命令为：

```powershell
python code\data_build\build_oecd_amne.py --project-root . --overwrite
```

核心字段构造如下：

| 字段 | 构造方式 |
|---|---|
| `affiliate_output` | 来自 `aamne-bilateral-output.csv` 的 off-diagonal parent-host-sector output，单位为 current million USD；domestic diagonal cells 被排除。 |
| `affiliate_value_added` | `aamne-mne-xvem.csv` 中 foreign-owned aggregate `GVA`，按同一 host-sector-year 内 parent affiliate-output share 分摊到 parent country。 |
| `affiliate_exports` | foreign-owned aggregate `EXGR`，按 parent affiliate-output share 分摊。 |
| `affiliate_imports` | foreign-owned aggregate `IMGR`，按 parent affiliate-output share 分摊；OECD 说明该指标是 firms 的 intermediate-input imports。 |
| `affiliate_employment` | 保留为必需字段，但本批 OECD Analytical AMNE 文件没有 employment，因此该列为空；当前 employment 证据应来自 BEA MNE 或国家统计数据。fDi Markets jobs 需要以后单独开批次。 |
| `ownership_type` | 固定为 `F`，表示 foreign-owned firms。 |

两个模型变量的定义是：

```text
MPEexpansion_{c,s,t} = ForeignAffiliateOutput_{c,s,t} - ForeignAffiliateOutput_{c,s,t-1}
ForeignAffiliateShare_{c,s,t} = ForeignAffiliateOutput_{c,s,t} / GrossOutput_{c,s,t}
```

在 parquet 中分别保存为 `mpe_expansion` 和 `foreign_affiliate_share`。同时保留 `mp_output_share`，即 parent-specific affiliate output 除以 host-sector gross output；也保留 `parent_affiliate_output_share`，即分摊 value added、exports、imports 时使用的 parent 权重。

这个构造有一个必须说明的限制：`aamne-bilateral-output.csv` 直接给出 parent-country output，但不直接给出 parent-country value added、exports、imports。后三个字段来自 `aamne-mne-xvem.csv` 的 host-sector foreign-owned aggregate，并按 parent output share 分摊。因此它们可以作为有记录的 Scenario B 校准变量使用，但不能写成 OECD 直接报告的 parent-country AMNE value added 或 trade cells。

当前本地构建的验证结果：

| 检查项 | 结果 |
|---|---|
| 年份 | 2008-2023 |
| host economies | 81 |
| parent economies | 81 |
| `oecd_amne_mp_shares.parquet` 覆盖的 sector | 41 |
| `oecd_amne_affiliate_activity.parquet` 中有正值 affiliate output 的 sector | 39；`O84` 和 `T97T98` 在 raw XVEM 的 foreign-owned `GO` 中全为 0。 |
| `oecd_amne_affiliate_activity.parquet` 行数 | 1,260,053 |
| `oecd_amne_mp_shares.parquet` 行数 | 4,250,880 |
| `foreign_affiliate_share` 公式残差 | 0 |
| `mpe_expansion` 年度差分残差 | 0 |
| 分摊后的 value added、exports、imports 加总回 XVEM foreign-owned aggregates | 只有浮点精度误差。 |
| bilateral output 与 XVEM foreign-owned `GO` 的差异 | 最大绝对差约 0.113 million USD，符合 OECD 文件之间的小幅 rounding differences。 |

论文解释上，这批 AMNE 输出支持 incumbent MP-intensive evidence 和有约束的 `hgamma` scenario。它能说明 connector host country-sector 是否出现 foreign-affiliate output 和 ownership-split activity 扩张。它不能单独证明 firm-level relocation、plant entry 或 new affiliate entry；这些 extensive-margin 结论必须保留在模型外证据层，并结合 BEA、FDI 或国家生产统计数据。fDi Markets 只能在以后单独开启的新批次中考虑。

### 8.3.1 BEA U.S. MNE Batch 5：affiliate country-industry panel

Batch 5 使用 BEA **Activities of U.S. Multinational Enterprises**，口径是美国跨国企业的 majority-owned foreign affiliates。发布页是 `https://www.bea.gov/news/2025/activities-us-multinational-enterprises-2023`，可下载 comprehensive tables 的入口是 `https://www.bea.gov/international/di1usdop`。

当前本地面板覆盖 **2017-2023**。这个时间段足够覆盖 Section 301 前基准、贸易战阶段、COVID 冲击期，以及 2021-2023 年 nearshoring 高峰。若之后需要 2017 年以前的数据，应作为单独扩展继续下载并验证，不应直接混入当前已完成的 Batch 5。

本地文件：

| 项目 | 路径 |
|---|---|
| 构建脚本 | `code/data_build/build_bea_us_mne_affiliate_country_industry.py` |
| 原始 XLS 归档 | `data/raw/bea_mne/activities_us_mnes/` |
| 原始文件 manifest | `data/raw/bea_mne/metadata/bea_us_mne_activities_manifest.json` |
| 清洗后面板 | `data/interim/mne/bea_us_mne_affiliate_country_industry.parquet` |
| 使用说明 | `data/bea_us_mne_affiliate_country_industry_usage_note.md` |

核心变量：

| 变量 | BEA 表 | 单位 | 含义 |
|---|---|---|---|
| `year` | 所有来源表 | 年 | 当前覆盖 2017-2023。 |
| `affiliate_country` | 所有来源表 | 文本 | BEA 的 affiliate country 或 area 行；使用 `bea_area_type` 区分国家行和区域汇总行。 |
| `industry` | 所有来源表 | 文本 | BEA affiliate industry。 |
| `employment` | Table II.G 1 | 千人 | majority-owned foreign affiliates 的就业。 |
| `sales` | Table II.D 3 | 百万美元 | affiliates 的销售额。 |
| `value_added` | Table II.F 3 | 百万美元 | affiliates 的增加值。 |
| `capital_expenditures` | Table II.C 4 | 百万美元 | affiliates 的 property, plant, and equipment 支出，作为资本支出指标。 |
| `goods_exports_to_us` | Table II.H 11 | 百万美元 | 美国从 affiliates 进口的 goods；从 affiliate 角度解释为对美国出口。 |
| `goods_imports_from_us` | Table II.H 3 | 百万美元 | 美国出口给 affiliates 的 goods；从 affiliate 角度解释为从美国进口。 |

BEA suppression 已显式处理。`(D)` 不是 0，而是缺失值；employment 表里的 `A/F/G/H/I/J/K/L/M` size-range codes 也被视为 suppressed numeric cells。`(*)` 表示小到四舍五入后低于报告单位的一半，数值字段记为 `0.0`，并用 small-value flag 标记。每个核心变量都有对应的 `*_raw_code`、`*_suppressed`、`*_small_value` 字段，使用这些 country-industry moments 约束 `hgamma` 前必须先检查 suppression。

### 8.4 想做到更成熟还需要什么数据

如果目标是 JIE 级别，公开数据版本可以成立，但研究设计必须非常克制：不能用总量数据直接声称 firm-level relocation。更强的版本应尽量补充以下数据层：

| 补充数据 | 为什么重要 |
|---|---|
| Orbis、本地企业注册数据或海关-企业匹配数据 | 直接识别企业、母公司、子公司、行业、所在地、就业、收入，以及企业是否在 connector countries 新进入或扩张。 |
| 工厂或 establishment-level 制造业数据 | 区分真实产能扩张和单纯贸易公司活动。 |
| Panjiva、Datamyne、ImportGenius 等 shipment-level 数据 | 追踪 supplier-consignee links，判断中国供应商是否先发货给 connector-country exporter，再由其发往美国买家。 |
| Greenfield investment project data，如以后单独开启批次 | 用于核对已公告项目是否实际投产、取消或延后。 |
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

当前公开数据工程阶段已经基本完成。BACI、U.S. Census imports、Section 301、OECD ICIO、OECD Analytical AMNE、BEA U.S. MNE、BEA direct investment 和 Mexico 官方 FDI 都已有可重复运行的 Python 构建脚本、interim 输出和 build summary。OECD ICIO 还已经生成 2017、2018、2022 三套 MATLAB-ready baseline CSV。

当前 validated data workflow 已完成到 M6.4。Gate 1 已在 `docs/JIE_GAP_AUDIT_2026_08_13.md` 中完成；唯一保留的 headline 是用 observable MP discipline 量化 trade-only connector welfare model 的预测误差。Gate 2、Gate 3、Gate 4、M6.5 其余部分、最终 moment-to-MP mapping、三边网络处理、模型选择、shock arrays、MATLAB equilibrium/welfare code 和 counterfactual results 尚未完成。M7 的全流程重建、版本冻结、Stata handoff 和最终审计交付也尚未完成。因此，准确状态是：**核心数据工程和 empirical moment bank 已完成并验证，但端到端数据阶段尚未全部完成，也还不是 model-ready release**。fDi Markets 明确不在当前批次范围内。

截至 2026-08-16，权威的 M0-M6.4 数据处理与 JIE Gate 1 记录位于 `data-processing-variables@c46c671`；当前 `codex/model@2df0a06` checkout 比它少 24 个 commits。后续模型工作应从 `c46c671` 建立 model-pilot line，或明确整合该段历史，不能只依赖共享工作目录中已经生成但缺少当前分支代码与 validation 对应关系的 Parquet 文件。

## 10. 近期下一步

1. 将 Gate 2 的同窗口 trade/AMNE affiliate share-and-level object 写成 canonical code 和 validation，并冻结 measurement uncertainty。
2. 增加定向的 ownership-conditioned incumbent parent-host AMNE transformation；entry/exit 单独报告。
3. 完成 Gate 3 的 observable moments 到 `hgamma`、MP elasticity 或透明 bounds 的 mapping；机制需要时，必须观测、限制或界定 parent-host-destination network。
4. 固定唯一核心 `NoConnector` shock contract，以及可比较的 `TradeConnector`、`Trade+MPConnector` 和有条件的 `FullNetworkAdjustment` contracts。
5. 只有 Gate 1-3 有支持时，才构造小型 model pilot，检验机制 relevance、数值有效性和 Gate 4 welfare separation；不能机械开始完整 Du-Wang 迁移。
6. M6.5 作出决定后，完成 M7 的 full rebuild、版本冻结、Stata handoff 和最终审计交付；在此之前不能宣布整个数据阶段完成，也不能开始完整模型迁移。

## 11. 进入结构模型的判断标准

只有 M6.5 对 Gate 1（frontier-level intellectual object）、Gate 2（新的可审计 empirical fact/object）和 Gate 3（observable moments 对 first-order MP margin 的可信约束）给出明确支持，而且 Gate 4 pilot 已有唯一、可比较的 shock contracts 和数值验收标准，才进入小型结构试验。M6.1-M6.4 的 validation PASS 本身不能替代这些判断。

作出决定时必须书面回答 `docs/JIE_PROJECT_GOAL.md` 中的 Novelty、Discipline 和 Quantitative-payoff referee tests。任何一项答不出来，就选择定向补一个关键输入、pause、model switch 或收窄主张，不能以增加无关数据或任意设定 `hgamma` 代替。

## 12. References

This project should not cite only broad geoeconomic-fragmentation reports. The working reference stack has four roles: empirical connector facts, structural welfare accounting, MP-margin architecture, and data/policy-shock measurement.

1. Du, Xiayi, and Zi Wang. 2022. "Multinationals, Global Value Chains, and the Welfare Impacts of Economic Sanctions." Economics Letters. Direct source for the first structural model and welfare decomposition.
2. Arkolakis, Costas, Natalia Ramondo, Andrés Rodríguez-Clare, and Stephen Yeaple. 2018. "Innovation and Production in the Global Economy." American Economic Review 108 (8): 2128–2173. DOI: 10.1257/aer.20141743. Core trade-and-multinational-production foundation.
3. Caliendo, Lorenzo, and Fernando Parro. 2015. "Estimates of the Trade and Welfare Effects of NAFTA." Review of Economic Studies 82 (1): 1–44. DOI: 10.1093/restud/rdu035. Core multisector, intermediate-input, and input-output-linkage foundation.
4. Ramondo, Natalia, and Andres Rodriguez-Clare. 2013. "Trade, Multinational Production, and the Gains from Openness." Journal of Political Economy. Key reference for iceberg MP costs and multinational-production share adjustment.
5. Tintelnot, Felix. 2017. "Global Production with Export Platforms." Quarterly Journal of Economics. Key reference for a possible second-version fixed-cost foreign-investment and affiliate-entry model.
6. Bonadio, Barthelemy, Zhen Huo, Andrei A. Levchenko, and Nitya Pandalai-Nayar. 2021. "Global Supply Chains in the Pandemic." Journal of International Economics. Reference point for BHLP-style global supply-chain / IO counterfactual frameworks.
7. Schulze, Tatjana, and Weining Xin. 2025. "Demystifying Trade Patterns in a Fragmenting World." IMF Working Paper WP/25/129. Closest empirical benchmark for connector countries, trade reallocation, and trade rerouting.
8. Freund, Caroline, Aaditya Mattoo, Alen Mulabdic, and Michele Ruta. 2024. "Is US Trade Policy Reshaping Global Supply Chains?" Journal of International Economics 152: 104011. DOI: 10.1016/j.jinteco.2024.104011. Connector trade and supply-chain benchmark.
9. Shen, Lu. 2026. Journal of International Economics 161: 104264. DOI: 10.1016/j.jinteco.2026.104264. China-connector-U.S. GVC paths and fragmentation-welfare mitigation.
10. Wang, Zi. 2021. "Headquarters Gravity: How Multinationals Shape International Trade." Journal of International Economics 131: 103477. DOI: 10.1016/j.jinteco.2021.103477. Identification boundary for the parent-host-destination network.
11. Xue, Sifan. 2026. "Trade Wars with FDI Diversion." January working paper. Closest current threat to a broad trade-versus-MP welfare claim; version-dependent results require re-verification.
12. International Monetary Fund and CEPR. Geoeconomic-fragmentation policy and quantitative background.
13. Bown, Chad P., plus PIIE / USTR / USITC Section 301 tariff files. Product-level tariff-shock source for `htau` scenarios.
14. OECD ICIO, OECD Analytical AMNE / MNE-GVC, BEA U.S. MNE Activity, CEPII BACI, Mexico Secretaria de Economia / DataMexico FDI, and USITC USMCA automotive rules-of-origin reports. Current data and calibration sources; fDi Markets remains outside the active batch. Final citations should record exact release versions, years, and table identifiers.

The full current-frontier matrix and source links are in `docs/JIE_GAP_AUDIT_2026_08_13.md`.
