# Connector Economies 项目数据整理与合并审计档案

## Material Passport

- Origin Skill: `academic-research-suite/experiment-agent`
- Origin Mode: `validate`
- Origin Date: `2026-07-27`
- Verification Status: `ANALYZED`
- Version Label: `data_processing_audit_v1.0.0`
- Working Branch: `data-processing-variables`
- Frozen Upstream Commit Recorded by M0: `2df0a0628343c9abca6b3e26d893db351ec22b94`
- M0-M2 Evidence Snapshot Date: `2026-07-19`
- Current Completed Processing Stage: `M0-M4.3`
- Next Stage: `M4.4`，尚未开始且须等待用户确认
- Audience: 项目合作者和内部复核人员
- Publication Status: 内部严格审查材料，不是投稿附件

## 0. 文档目的、范围和使用方式

这是一份持续维护的内部数据审计档案。它不以压缩叙述或展示研究结果为目标，而是回答下列问题：每张数据表从哪里来、经过了什么转换、为什么采用该规则、主键和粒度是什么、哪些值可以加总、哪些值不能加总、哪些异常被保留、每一步如何验证、当前还有哪些限制，以及合作者如何从现有文件复核全过程。

本版记录两层流程：

1. `source -> raw -> interim`：主要公开数据的下载、归档、单库清洗和标准化；
2. `interim -> processed`：M0 输入冻结、M1 concordance、M2 产品冲击与贸易底表、M3.1 connector-sector-year 年度聚合、M3.2 完整窗口和增长变量、M3.3 small-base/异常增长/敏感性诊断、M3.4 replacement/source-input/exposure-overlap/产品共变指标、M3.5 完整 connector/comparator 共同面板、M3.6 alternative-window/source-bloc/exposure-definition sensitivity inputs、M4.1 ICIO source/analysis production long，以及 M4.2 AMNE parent-host source detail/host-analysis totals long。

M3.1-M4.3 已执行并在冻结输入上完成确定性重建；M4.4-M7 尚未执行。本档案已为后续阶段预留固定结构。以后每完成一个 checklist 项目，必须在同一工作批次内更新本档案和 PDF，才允许打勾。仅有代码、仅有输出、仅有口头说明或尚未解释的 many-to-many join，都不构成完成。

本档案与 `docs/variable_construction_catalog.md` 配套使用。前者回答“数据经历了什么处理、凭什么相信处理正确”，后者回答“每个变量怎样构造、用于什么、允许怎样解释以及如何交给 Stata”。两份材料必须使用同一阶段状态和同一输出证据；若不一致，以实际数据、validation 和 build summary 为准，并在当次工作中修正文档。

### 0.1 本版能够证明什么

- 能证明当前 M0-M4.3 的输入身份、处理规则、输出文件、主键、行数和已执行 validation 均有本地证据。
- 能证明当前 processed 输出的 SHA256 与对应 validation JSON 记录一致。
- 能证明已知的 missing、suppressed、confidential、aggregate、allocated、proxy 和 non-additive 字段没有在 M0-M2 中被静默改成普通零值或普通国家记录。
- 能证明 Section 301 的口径是 gross statutory initial-action exposure，而不是 realized duties。
- 能证明 M3.1 的 1,001 行 connector-sector-year 输出在两个冻结输入上可确定性重建，四条流总量守恒、policy 公式复算和 Stata alias 合同均通过。
- 能证明 M3.2 的 273 行 long window 和 91 行 comparison 输出在冻结的 M3.1/时间窗口输入上可确定性重建，4/2/5 年窗口完整，level/coverage/policy/growth 公式和两个 Stata alias 合同均通过。
- 能证明 M3.3 的 364 行 flow diagnostics 在冻结的 M3.2 comparison 输入上可确定性重建，small-base、robust-z、mechanical extreme、winsorized sensitivity、raw-value preservation 和 Stata alias 合同均通过。
- 能证明 M3.4 的 55,081 行产品窗口、91 行部门重组指标和 91 行产品共变表在冻结的 M2/M3.2/M3.3 inputs 上可确定性重建，replacement、source ratio、exposure missing、产品共变和 Stata alias 合同均通过。
- 能证明 M3.5 的 91 行完整 connector-sector 共同面板由两张同粒度 M3.4 表 one-to-one 合并，13 × 7 网格、21/49/21 分组、全部原字段、设计性 missing、no-selection flags 和 152 个 Stata aliases 均通过 validation。
- 能证明 M3.6 的 1,092/182/364 行 sensitivity interfaces 在冻结输入上可确定性重建，window/source-bloc/exposure-definition 的公式、nested/self-trade/missing 状态和 56/64/47 个 Stata aliases 均通过 validation。
- 能证明 M4.1 的 85,050 行 ICIO source-sector audit long 与 10,080 行 analysis-sector long 在冻结 ICIO/country/sector inputs 上可确定性重建；全部 source cells、负 accounting cells、ROW/excluded partition、source-to-analysis reconciliation、7 个 metrics、54/43 个 Stata aliases 和两个输出 hash 均通过 validation。
- 能证明 M4.2 的 7,560,318 行 AMNE parent-host source-detail long 与 53,760 行 host-analysis-sector long 在冻结 activity/MP-share/country/sector inputs 上可确定性重建；positive/zero-link universe、direct/allocated/derived/unavailable 状态、ROW parent/host 规则、166 个负 allocated VA、employment unavailable、bilateral-XVEM reconciliation、71/56 个 Stata aliases 和两个输出 hash 均通过 validation。

### 0.2 本版不能证明什么

- 本次没有从 raw 端完整重跑所有 M0-M2 大型 builder，因此整份 Material Passport 继续使用 `ANALYZED`；M3.1-M4.3 本身均在各自冻结输入上两次构建并比较输出 SHA256，单模块 validation 为 `VERIFIED`。
- M4.4-M7 尚未完成。M4.1-M4.3 只提供 ICIO aggregate、AMNE affiliate-activity 与 BEA majority-owned affiliate activity 专源接口，尚未构造 BEA FDI/Mexico 跨来源 production integration、connector ranking、structural moments 或 welfare counterfactual。
- FDI 只能作为 financial-flow/position evidence，不能单独证明 plant entry 或 production relocation。
- BACI 和 Census 的贸易模式不能单独证明 connector 本地生产增加。

## 1. 审计治理和证据优先级

### 1.1 证据优先级

出现口径冲突时，按以下顺序判断：

1. 实际 Parquet schema、唯一键、观测期和数值；
2. `data/validation/*.json` 中的机器可读结果和 SHA256；
3. 同名 `data/validation/*.md` 人类可读报告；
4. `configs/*.yaml` 中冻结的处理规则；
5. `code/data_processing/*.py` 和 `code/data_build/*.py`；
6. README、usage note 和历史进度说明。

原因是历史说明可能在数据重建后没有同步更新，而实际文件、validation 和冻结配置共同构成当前可复核的处理合同。本次核对即发现：Mexico 全国季度表覆盖到 2024Q4，但当前五张详细季度交叉表仅覆盖到 2024Q2；M1 time validation 与实际 Parquet 一致，旧说明中“详细表到 2024Q4”的说法需要纠正。

### 1.2 状态定义

| 状态 | 定义 | 是否允许进入下游 |
|---|---|---|
| `PASS` | 所有硬性检查通过 | 可以，但仍须遵守 expected limitations |
| `PASS_WITH_EXPECTED_LIMITATIONS` | 主键、类型和硬性规则通过，同时存在已解释的来源限制 | 可以，限制必须进入下游合同 |
| `ANALYZED` | 已审查现有证据，但本轮未从最上游完整重跑 | 可以用于内部审计，不等同于全流程重现 |
| `VERIFIED` | 在固定输入和环境下成功重跑并完成输出比较 | 可以作为复现验证 |
| `BLOCKED` | 存在未解决的输入、规则或验证障碍 | 不允许继续相关下游步骤 |

### 1.3 数据目录边界

- `data/raw/`、`archive/`、`legacy/`、`_staging*`：只读。不能因为名称像临时目录而删除、移动、覆盖或清理。
- `data/interim/`：source-specific 标准化输出，继续保留原始来源的粒度、单位和 flags。
- `data/processed/`：跨库 concordance、harmonized panel、变量和合作者交付数据。
- `code/data_build/`：下载与 raw-to-interim。
- `code/data_processing/`：interim-to-processed、变量构造、验证和 Stata handoff。
- `data/validation/`：机器可读 JSON 与人类可读 Markdown 验证证据。
- `output/pdf/`：本档案正式 PDF；PDF 中间渲染文件写入 `tmp/pdfs/`。

任何大型中间文件、日志和缓存必须留在项目所在 F 盘；不把正式输出和大型临时文件写到 C 盘。

## 2. 端到端数据架构和当前状态

```text
官方/公开来源
    -> versioned raw archive (只读)
    -> source-specific builder
    -> data/interim/ + build summary + usage note
    -> M0 input freeze + quality audit + sample freeze
    -> M1 country/time/product/sector concordances
    -> M2 product treatment + connector trade + Census timing interface
    -> M3.1 connector-sector-year年度聚合                [已完成]
    -> M3.2完整窗口、变化和机械增长变量                  [已完成]
    -> M3.3 small-base、异常增长和敏感性诊断             [已完成]
    -> M3.4 replacement、source-input、overlap、共变      [已完成]
    -> M3.5 完整13×7共同connector/comparator面板         [已完成]
    -> M3.6 exposure/source/window sensitivity inputs   [已完成]
    -> M4.1 ICIO source/analysis production long        [已完成]
    -> M4.2 AMNE parent-host/host production long       [已完成]
    -> M4.4-M4.7 remaining production sources/merge     [未开始]
    -> M5 trade-production evidence merge               [未开始]
    -> M6 ranking/rerouting/moments/model decision       [未开始]
    -> M7 full rebuild + release + Stata handoff         [未开始]
```

| 阶段 | 状态 | 主要交付 | 当前判断 |
|---|---|---|---|
| source-specific download/build | 已完成当前核心公开数据范围 | 八个核心 interim 接口及 source-specific summaries | 国家统计补充项暂缓；fDi Markets 排除 |
| M0 | 已完成 | input manifest、quality audit、analysis sample v1 | 八个输入冻结，硬性失败 0 |
| M1 | 已完成 | country/time/HS/product-sector/source-sector concordances | 所有 source code 有显式状态 |
| M2 | 已完成 | treatment、trade legs、merged trade、Census 月/年表、2024 exact HTS extension | 所有自然键无重复；金额守恒 |
| M3.1 | 已完成 | 1,001 行 connector-sector-year annual trade/treatment panel | validation PASS；确定性 hash 一致 |
| M3.2 | 已完成 | 273 行 long window 与 91 行 comparison/growth panel | validation PASS；两张确定性 hash 一致 |
| M3.3 | 已完成 | 364 行 flow-level small-base、异常增长与 winsorized sensitivity diagnostics | validation PASS；确定性 hash 一致 |
| M3.4 | 已完成 | 55,081 行产品窗口、91 行部门重组指标、91 行产品共变 | validation PASS；三张确定性 hash 一致 |
| M3.5 | 已完成 | 91 行、152 列完整 connector/comparator 共同面板 | validation PASS；13 × 7 全保留；确定性 hash 一致 |
| M3.6 | 已完成 | 1,092 行 time-window、182 行 source-bloc、364 行 exposure-definition sensitivity inputs | validation PASS；三张确定性 hash 一致；未构造 ranking |
| M4.1 | 已完成 | 85,050 行 ICIO source-sector audit long、10,080 行 analysis-sector long | validation PASS；负 accounting cells/ROW/excluded 状态保留；两张确定性 hash 一致 |
| M4.2 | 已完成 | 7,560,318 行 AMNE parent-host source detail、53,760 行 host-analysis totals | validation PASS；direct/allocated/unavailable、zero links、ROW 和 reconciliation 状态保留；两张确定性 hash 一致 |
| M4.4-M6 | 未开始 | remaining production sources、integrated evidence、ranking/moments | 不得提前声称跨来源 production 或 ranking 结果 |
| M7 | 未开始 | full rebuild、release、Stata package | 最终交付门槛 |

## 3. source -> raw -> interim：单库数据整理过程

这一部分记录进入 M0 之前已经完成的来源处理。它的目的不是重写每个 builder 的全部代码，而是固定每个来源的归档、标准化接口、关键转换和不可忽略的解释边界。详细下载 URL、raw 文件、查询参数和构建统计继续以 `configs/data_versions.yaml`、`docs/data_source_log.md`、各 build summary 和 usage note 为准。

### 3.1 CEPII BACI HS2012 主贸易面板

- 来源/版本：CEPII BACI HS2012 Version 202601。
- raw：`data/raw/BACI_HS12_V202601/`。
- builder：`code/data_build/build_baci_batch1.py`。
- interim：`data/interim/trade/baci_hs6_panel.parquet`。
- 粒度：`year × exporter_iso3 × importer_iso3 × hs6`。
- 覆盖：2014-2024；123,313,077 行。
- 核心处理：HS6 固定为字符串；BACI 贸易额从 thousand USD 转为 current USD；quantity 单位固定记录为 metric tons；保留 `source_file`。
- 关键边界：quantity 缺失不影响 value-based 主分析；BACI `S19/Other Asia, nes` 只有在项目配置中作为 TWN proxy 使用，不能描述为直接 Taiwan-only 数据。

### 3.2 BACI HS2017 Section 301 分母

- 来源/版本：CEPII BACI HS2017 Version 202601。
- raw：`data/raw/BACI_HS17_V202601/BACI_HS17_V202601.zip`。
- builder：`code/data_build/build_baci_hs17_us_imports_2017.py`。
- interim：`data/interim/trade/baci_hs17_us_imports_2017.parquet`。
- 目的：为 Section 301 建立 2017 年 China imports 和 total U.S. imports 分母，而不是替代主 HS2012 贸易面板。
- 校验：ZIP CRC 通过；ZIP SHA256 为 `16aaa22d3b000cc87744c2c28ac97ce44394c3adf315ec259451d5bb4fcae609`；输出 5,384 个 HS2017 产品；U.S. imports 合计 USD 2,274,243,094,334，其中 China USD 492,682,263,643。
- 特殊处理：BACI 对 2710 使用 `271000` 聚合码；后续桥接保留这一明确的 CEPII collapse。

### 3.3 U.S. Census 月度进口

- 来源：U.S. Census International Trade API。
- raw：`data/raw/us_census/hs10_monthly_imports/`、`data/raw/us_census/hs6_monthly_imports/` 和 metadata。
- builder：`code/data_build/download_us_census_imports.py`。
- validator：`code/data_build/validate_us_census_imports.py`。
- interim：`data/interim/trade/us_imports_hs10_monthly.parquet` 和 `us_imports_hs6_monthly.parquet`。
- 覆盖：2014-2024，15 个配置来源经济体；HS10 12,132,098 行，HS6 5,017,364 行。
- 核心处理：保留 import value、customs value、duties、dutiable value、商品描述和 raw source file provenance；HS6 自然键为 `year, month, origin_iso3, hs6`。
- 关键边界：这不是 all-origin U.S. imports。HS6 quantity 当前全部为 0 且 unit 为 `-`，是结构性不可用占位，不是经济零数量。

### 3.4 Section 301 官方政策数据

- 官方依据：USTR、Federal Register、USITC HTS 和 CBP 材料；不依赖第三方清洗表。
- raw：`data/raw/ustr_section301/`，保持只读。
- builders：`build_ustr_section301_notice_codes.py`、`build_ustr_section301.py`、`build_ustr_section301_2024_review_codes.py`。
- interim：
  - `section301_hts10_list_panel.parquet`：32,357 个 HTS10 event rows；
  - `section301_hs6_exposure.parquet`：55,308 个 HS2017-year rows；
  - `section301_2024_review_codes.parquet`：367 个 modern-HTS rows。
- 法定范围：List 1、2、3、4A；List 4B 因生效前暂停而不标为 tariffed。
- 处理：官方 code table 共 10,115 行；description-scoped HTS8 只扩展到明确覆盖的 HTS10；83 FR 49153 的删除和 Chapter 44 successor mappings 显式记录。
- 已修复的来源抽取问题：List 1 PDF text layer 将最后的 `9033.00.90` 截为 `9033.00`。builder 根据同一官方 notice 的 product-description table 恢复为 `90330090`，并验证 `hts10 × list_id × effective_date` 唯一。
- 关键边界：历史 exclusions 已归档但未应用；主面板是 gross statutory exposure。2024 review 采用现代 HTS，不能只截取前六位强行并入历史 HS2017 面板。

### 3.5 OECD ICIO

- 来源/版本：OECD ICIO 2025 edition regular tables；Extended archives 已保存但尚未构造 ownership-split processed output。
- builder：`code/data_build/build_oecd_icio_baseline.py`。
- interim：`data/interim/production/oecd_icio_output_va_fd.parquet` 和 IO-share 表。
- 当前 M0 输入：12,150 行，2017、2018、2022，81 economy/ROW 单元，50 个 sectors。
- 单位：current million USD。
- 处理：从 ICIO matrix 生成 gross output、value added、final demand、intermediate inputs、exports、imports 等 accounting fields；同时生成模型基准文件。
- 关键边界：负 value added 和负 taxes less subsidies 属于 accounting cells，保留原符号；未观测年份不插值，不构造 synthetic 2019 baseline。

### 3.6 OECD Analytical AMNE

- 来源/版本：OECD Analytical AMNE 2026 release。
- builder：`code/data_build/build_oecd_amne.py`。
- interim：`data/interim/mne/oecd_amne_affiliate_activity.parquet`。
- M0 输入：1,260,053 行，2008-2023 可用交集，粒度为 `parent × host × OECD sector × year`。
- 处理：affiliate output 为 bilateral cell；host-sector foreign-owned value added、exports、imports 按 `parent_affiliate_output_share` 分配到 parent；保留 `allocation_method`。
- 关键边界：affiliate employment 全部缺失；allocated value added、exports、imports 不能描述为直接 bilateral observations；166 个负 affiliate value-added observations 保留原值，不自动清零。

### 3.7 BEA Activities of U.S. MNEs

- 来源：BEA annual comprehensive tables，majority-owned foreign affiliates of U.S. MNEs。
- builder：`code/data_build/build_bea_us_mne_affiliate_country_industry.py`。
- interim：`data/interim/mne/bea_us_mne_affiliate_country_industry.parquet`。
- 覆盖：2017-2023；8,256 行；粒度 `year × affiliate_country × industry`。
- 处理：合并 employment、sales、value added、capital expenditures、goods exports to U.S.、goods imports from U.S.；每个指标保留 raw code、suppression、小值和 source file 字段。
- 缺失规则：`(D)` 和 employment size-range codes `A/F/G/H/I/J/K/L/M` 作为 suppressed/missing；`(*)` 作为 0.0 并保留 small-value flag。
- 方向规则：`goods_exports_to_us` 来自 BEA Table II.H 11；`goods_imports_from_us` 来自 Table II.H 3。
- 关键边界：source 原始 `bea_area_type` 标出 1,792 个 aggregate geography rows；country master 再将 source 误标为 country-or-area 的 regional/addendum labels 强制设为 aggregate，M1 coverage 最终排除 1,904 个 geography rows。Transportation equipment 比 autos 更宽，只能保留为 proxy/ambiguous 口径。BEA MNE value added 的 164 个负 observations 保留，M4 时需单独复核其来源和经济含义。

### 3.8 BEA Direct Investment by Country and Industry

- builder：`code/data_build/build_bea_direct_investment_country_industry.py`。
- interim：`data/interim/fdi/bea_direct_investment_country_industry.parquet`。
- 覆盖：2020-2024，两个方向，11,610 行；粒度 `year × direction × country × industry`。
- 处理：position、flows、income 分列并保留 raw code、suppression、小值、source URL/file 和 BEA geography metadata。
- 方向：`us_direct_investment_abroad` 为 U.S. outward；`foreign_direct_investment_in_us` 为 inward into U.S.。
- 关键边界：position 是 stock；flow 和 income 是 annual flows；不能相加为同一指标。source 原始 `bea_area_type` 标出 2,610 个 aggregate rows；country overrides 纳入后 M1 coverage 最终排除 3,060 个 geography rows。负 position/flow/income 是有效经济符号，不能因“负数”被清洗掉。

### 3.9 Mexico 官方 inward FDI

- 来源：Mexico Secretaría de Economía，经 datos.gob.mx 和 Data México。
- builder：`code/data_build/download_build_mexico_fdi.py`。
- raw：`data/raw/mexico_fdi/`，新 vintage 必须另存，不能覆盖现有 raw snapshot。
- interim：九张 `data/interim/fdi/mexico_fdi_*.parquet`。
- 全国表：1999Q1-2024Q4；2024 全国 total 为 USD 36,872.421 million。
- 当前详细季度交叉表：2006Q1-2024Q2。直接检查五张 detailed quarterly Parquet 的 2024 `quarter` 均只有 1 和 2；因此年度可比规则只允许完整 2006-2023，2024 保留季度或 H1-to-H1。
- 处理：`C` 保留为 null 并设 `confidential_flag=true`；负 FDI flow 保留；country names 显式标准化；SCIAN 保留 sector/subsector/industry_group level。
- 特殊国家行：`Total general` 是 total；`Otros países` 是可加总 residual group，但没有 ISO3，不能进入普通国家 join。
- 关键边界：详细 disclosed cells 因保密不必加总到全国总额；Mexico FDI 是 financial flow，不是 plant entry、employment 或 output。

## 4. M0：输入冻结、质量审计和样本冻结

### 4.1 M0.1 当前下载范围的结束条件

核心公开数据下载阶段被定义为 BACI、Census、Section 301、OECD ICIO、OECD AMNE、BEA MNE、BEA FDI 和 Mexico 官方 FDI 已有本地 raw/interim、builder、summary 或 validation。Mexico INEGI、Vietnam GSO、Statistics Canada 属于后续增强项；fDi Markets 按用户要求排除；商业数据库不属于当前完成门槛。

这一决策的原因是：M0-M3 的主要识别链已经具备，继续扩大来源会推迟对现有口径和合并逻辑的验证。国家统计数据应在 M3-M6 的结果显示具体覆盖缺口后定向补充。

### 4.2 M0.2 八个冻结输入接口

| Input ID | 路径 | 行数 | 年份 | 自然键 |
|---|---|---:|---|---|
| `baci_hs6_panel` | `data/interim/trade/baci_hs6_panel.parquet` | 123,313,077 | 2014-2024 | `year, exporter_iso3, importer_iso3, hs6` |
| `us_census_hs6_monthly` | `data/interim/trade/us_imports_hs6_monthly.parquet` | 5,017,364 | 2014-2024 | `year, month, origin_iso3, hs6` |
| `section301_hs6_exposure` | `data/interim/policy/section301_hs6_exposure.parquet` | 55,308 | 2014-2024 | `hs6, year` |
| `oecd_icio_output_va_fd` | `data/interim/production/oecd_icio_output_va_fd.parquet` | 12,150 | 2017, 2018, 2022 | `year, country_iso3, sector_oecd` |
| `oecd_amne_affiliate_activity` | `data/interim/mne/oecd_amne_affiliate_activity.parquet` | 1,260,053 | 2008-2023 | `year, host_country_iso3, parent_country_iso3, sector_oecd` |
| `bea_us_mne_affiliate_country_industry` | `data/interim/mne/bea_us_mne_affiliate_country_industry.parquet` | 8,256 | 2017-2023 | `year, affiliate_country, industry` |
| `bea_direct_investment_country_industry` | `data/interim/fdi/bea_direct_investment_country_industry.parquet` | 11,610 | 2020-2024 | `year, direction, country, industry` |
| `mexico_fdi_country_sector_quarterly` | `data/interim/fdi/mexico_fdi_country_sector_quarterly.parquet` | 596,366 | 2006-2024H1 | `year, quarter, parent_country_name, sector_level, sector_code` |

八个冻结文件总大小 1,512,110,467 bytes。M0 manifest 记录路径、文件大小、SHA256、schema、自然粒度、自然键、builder、build summary、版本和时间覆盖。报告：`data/validation/data_merge_input_manifest.json` 与 `.md`，状态 PASS。

### 4.3 M0.3 输入身份冻结

执行命令：

```powershell
python code\data_processing\build_input_manifest.py --project-root . --overwrite
```

关键 SHA256：

| Input ID | SHA256 |
|---|---|
| BACI HS2012 | `23ab6734c70503b3a0a7c6c7ec015cc4bf75ee334242dce6cf43ec68cfef46a4` |
| Census HS6 monthly | `65746c64f8e72a215fa55506f9d1eded5b13bf3e035fbb830a8407237299a205` |
| Section 301 HS6 | `22863ef3e034bc560d40fcbbc0945678ccd2e07bb3829ba630a36f4dfe6ca299` |
| OECD ICIO | `4c3c5b1a11d344e7b13b727a7036230d053312c137871525cb1fb412a4679643` |
| OECD AMNE | `ae5f859573e95773274928d0f27a90fe974fca2bd95f22fa78a849d8a2d8f856` |
| BEA MNE | `ab2e064459cc9dac8c13eebd7e399e91047133a93e8f35b9821520add7f219e8` |
| BEA FDI | `a80c567f8d2e966a5f56b1d64f3c3e0005734d5ea9840f6c5d1c43246f01b0ba` |
| Mexico country-sector FDI | `fce725b009dc96ae825bd3fed2d2b02ba5cc13501c5a6657bcdf3a09a022261a` |

### 4.4 M0.4 source-specific 质量审计

执行命令：

```powershell
python code\data_processing\audit_input_quality.py --project-root . --overwrite
```

八个输入的自然键重复为 0，key-null cells 为 0，hard failure 为 0。全部为 `PASS_WITH_EXPECTED_LIMITATIONS`，原因不是数据“坏了”，而是官方数据中存在不能被错误清洗掉的会计、保密、聚合或不可用状态。

| 来源 | 保留的限制 | 下游决定 |
|---|---|---|
| BACI | quantity 缺失 3,328,696 行 | value-based 主分析；quantity 不作为完成条件 |
| Census HS6 | 5,017,364 行 quantity 全为 0，unit 全为 `-` | 标记 unavailable，禁止数量水平/增长分析 |
| Section 301 | historical exclusions 未应用 | 只称 gross statutory exposure |
| ICIO | value added 8 个负 cells；taxes less subsidies 365 个负 cells | 保留原值和 accounting 含义；不截断为 0 |
| AMNE | employment 1,260,053 行全部缺失；VA 有负值；VA/exports/imports allocated | employment 不可用；保留 allocation_method 和符号 |
| BEA MNE | 1,792 aggregate geography rows；各指标存在 suppression | aggregate 下游排除；suppressed 保持 missing |
| BEA FDI | 2,610 aggregate rows；4,335 个负 position/flow/income cells；suppression | aggregate 排除；负号保留；stock/flow/income 分开 |
| Mexico FDI | 86,123 confidential rows；19,980 residual-country rows；7,152 个 observations 为负，在两个等价金额字段中合计 14,304 个 negative metric cells | confidential 为 missing；residual 不作普通国家；负 flow 保留 |

说明：上述限制不要求继续泛化下载。需要补充数据的情况是某个核心研究指标结构性缺失且没有替代来源，例如 AMNE employment 可由 BEA 或将来的国家统计补充；这与“当前下载文件不完整”不同。

### 4.5 M0.5 分析样本冻结

执行命令：

```powershell
python code\data_processing\validate_analysis_sample.py --project-root . --overwrite
```

配置：`configs/analysis_sample_v1.yaml`。Validation 有 35 个 checks，failure count 0，状态 PASS。

| 维度 | 冻结范围 |
|---|---|
| core connectors | VNM, MEX, CAN |
| Asian comparators | IND, IDN, MYS, PHL, THA, KOR, TWN |
| other candidates | POL, MAR, TUR |
| source core | CHN |
| extended East Asia | CHN, KOR, JPN, TWN |
| destination | USA |
| priority sectors | electronics, electrical equipment, machinery, autos, medical devices, textiles/apparel |
| trade window | 2014-2024 |
| pre | 2014-2017 |
| shock | 2018-2019 |
| post | 2020-2024 |
| structural baselines | 2017, 2018, 2022 |

2017 是 pre-shock primary ICIO baseline；2018 是 shock-onset interface；2022 是 post-shock robustness。2019 没有当前验证通过的 ICIO baseline，因此明确排除，而不是插值或伪造。

## 5. M1：统一国家、时间、产品和行业维度

M1 的基本原则是：先让每个 source code 都有显式状态，再合并数值。`mapped`、`aggregate`、`residual`、`proxy`、`ambiguous`、`outside_scope` 和 `unavailable` 是不同状态，不能压缩为“匹配/未匹配”二元变量。

### 5.1 M1.1-M1.2 country master 和 aggregate 隔离

- builder：`code/data_processing/build_country_master.py`。
- config：`configs/country_concordance_overrides.yaml`。
- output：`data/processed/concordances/country_crosswalk.parquet`。
- key：`source_name, source_country_id`。
- 行数：611；八个来源；duplicate keys 0；unresolved identifiers 0。
- 分类：39 aggregate、1 residual、1 proxy，其余 mapped countries；classification 互斥。

处理逻辑：

1. source-specific label/code 保留；
2. genuine country 才获得 canonical ISO3；
3. World、ROW、Total、Other、International organizations、regional totals 和 BEA addendum/aggregate labels 标为 aggregate；
4. Mexico `Otros países` 标为 residual，不赋普通国家 ISO3；
5. BACI `S19` 映射为 TWN 时设 proxy flag；
6. aggregate、residual 和 proxy 在下游有独立 join eligibility，防止与国家行重复加总。

Validation：`country_crosswalk_validation.json/.md`，SHA256 `29b4b4b936d8c974c2b9f9d9eaa37b9c5d67e170e94c39ccdbd5088be3adc4c6`，PASS。

### 5.2 M1.3 time aggregation rules

- builder：`build_time_rules.py`。
- config：`time_aggregation_rules.yaml`。
- output：`time_aggregation_rules.parquet`。
- key：`input_id, metric_name`；39 行；duplicate keys 0。

核心规则：

| 来源/指标 | 年度操作 | 禁止操作 |
|---|---|---|
| BACI annual value/quantity | identity | 不跨年求和 |
| Census monthly monetary flows | 对 reported monthly rows 求和，同时保留月表和 months diagnostics | 不作 all-origin denominator |
| Census quantity | not available | 不构造 quantity level/growth |
| Section 301 rate/share/exposure | annual identity/state | 不跨年求和 rate/exposure |
| ICIO accounting fields | 仅保留 2017/2018/2022 | 不插值缺失年份 |
| AMNE annual activity/share | identity | share/activity 不跨年求和；保留 allocation |
| BEA MNE activity | identity | suppressed 不补 0 |
| BEA FDI position | end-period stock identity | position 绝不跨期相加 |
| BEA FDI flow/income | annual flow identity | 不与 position 混合 |
| Mexico quarterly FDI | 只有四季度完整且均非 confidential 才求年度和 | 2024H1 不作 full-year |

实际 period audit：Census 每个 origin-year 有 12 个 source months；Mexico country-sector detailed 表完整 calendar years 为 2006-2023，2024 只有 Q1-Q2；8,059 个 country-sector-year groups quarters 不完整；46,593 个 groups 至少一季 confidential。

Validation：SHA256 `94c9b5ee7e7f6bc91fcf67a251a0cb39c2aa64b1303fdce7948280039899bfb4`，PASS。

### 5.3 M1.4 HS revision bridge

- builder：`build_hs_revision_bridge.py`。
- config：`hs_revision_rules.yaml`。
- official sources：UNSD HS2017-to-HS2012、HS2022-to-HS2012 workbooks和 WCO corrigenda。
- outputs：
  - `hs_to_hs2012_conversion.parquet`：16,209 行；
  - `hs_revision_correlations.parquet`：27,726 行；
  - `census_hs6_year_to_hs2012.parquet`：57,347 行。

版本分段：Census 2014-2016 视为 HS2012，2017-2021 为 HS2017，2022-2024 为 HS2022。HTS10 始终是 year-specific U.S. national code，不能当作稳定 international product identifier。

主 conversion 采用 official UNSD one-target mapping，weight 固定为 1，因此不会扩张 value。官方 full correlations 单独保存；multi-target rows 没有 numeric weight，在未来建立并验证 value-based weights 之前不能用于加总。CEPII `271000` 是五个 official HS2012 refined-petroleum codes 的 many-to-one analysis collapse，不作平均拆分。

覆盖：Section 301 和 BACI HS2017 代码覆盖 100%；Census gross value coverage 最低 97.192253%，主要差异来自 national chapters 98/99；排除这些 non-international codes 后，eligible value coverage 最低 99.996285%。

Validation：三个输出 SHA256 分别为 `1793d5...77f9`、`92a498...094a`、`d0be24...7e1d`；完整 hash 见第 10 节；状态 PASS。

### 5.4 M1.5 product-sector 和 BEC crosswalk

- builder：`build_product_sector_crosswalk.py`。
- config：`product_sector_rules.yaml` 和 `sector_scope.yaml`。
- official source：UNSD HS2012-to-BEC Rev.5 / ISIC Rev.4 workbook。
- output：`product_sector_crosswalk.parquet`，5,202 行，key 为 `analysis_hs6`。

处理逻辑：

1. 每个 BACI/CEPII product 只获得一个 `analysis_sector` 或一个明确非纳入状态；
2. sector 与 BEC end use 分开，不能把 industry classification 和 intermediate/final use 混为同一维度；
3. eligible sector mapping weight 为 1；excluded/outside/residual weight 为 null；
4. 349 个 composite/ambiguous BEC rows 不赋 equal/guessed allocation weights；
5. `271000` 的五个 components sector 一致，但 BEC uses 不同，因此 sector 可映射、end-use 保留歧义；
6. `999999` 作为 commodities not specified residual，不猜 sector 或 BEC。

| analysis sector | HS6 rows |
|---|---:|
| autos | 64 |
| electrical equipment | 177 |
| electronics | 252 |
| machinery | 467 |
| medical devices | 32 |
| textiles/apparel | 823 |
| other manufacturing | 2,422 |
| excluded/outside/residual | 965 |

所有产品显式状态覆盖 100%；first-round analysis-sector trade-value share 为 72.950566%。后者是主动缩窄的样本份额，不是 unmapped-data rate。

Validation：SHA256 `201c1d47ee861fe300db1574b6e80288bbeaec17e19fe4d368205b6d84995c09`，PASS。

### 5.5 M1.6 source-sector crosswalk

- builder：`build_source_sector_crosswalk.py`。
- config：`source_sector_rules.yaml`。
- output：`source_sector_crosswalk.parquet`。
- key：`source_name, source_sector_level, source_sector_code`；517 行。

| 来源 | 观测 codes | 直接支持 priority sectors | 关键限制 |
|---|---:|---|---|
| OECD ICIO | 50 | electronics, electrical, machinery, autos, textiles | medical devices 不可单独识别 |
| OECD AMNE | 39 | electronics, electrical, machinery, autos, textiles | medical devices 不可单独识别 |
| BEA MNE | 16 | electronics, electrical, machinery | Transportation equipment 仅 autos proxy；medical 不可分 |
| BEA FDI | 20 | electronics, electrical, machinery | 同上；aggregate/residual industries 不进入主 join |
| Mexico FDI | 392 | 六个 priority sectors | main join 仅 industry_group；SCIAN 3345 mixed/unweighted |

所有 source codes explicit-status coverage 100%。直接映射 weight 为 1；ambiguous、aggregate、residual、services 和 mixed categories weight 为 null。Mexico sector 和 subsector 与 industry_group 共存，必须从主 join 排除，避免层级重复加总。SCIAN 3391 支持 medical devices；3345 同时含 measuring/control/navigation 与 electronic medical equipment，不能无权重拆分。

Validation：SHA256 `99ab34b27a5a37ec4db4cb2fd65d35c48732d92f5363a04e7565d5b852142fe9`，PASS。

### 5.6 M1.7-M1.8 联合 coverage audit

- builder：`build_concordance_coverage_report.py`。
- report：`concordance_coverage.json/.md`。
- 所有七张 concordance 自然键 duplicate 0；upstream reports 均 PASS。

Coverage 分母不是简单使用所有 source rows，而是先排除 aggregate geography、residual country 和非主 join sector level，再对实际可进入研究接口的 rows 计算。signed FDI metrics 使用绝对值计算 coverage，避免正负 flow 相互抵消；原始符号不变。

具体 denominator 调整：

- ICIO：12,150 input rows -> 12,000 country-sector rows，排除 ROW aggregate；
- AMNE：1,260,053 -> 1,171,365，排除 ROW/aggregate geography combinations；其中 employment 1,171,365 行全部 missing，coverage 为 n/a；
- BEA MNE：8,256 -> 5,558，排除 1,904 个 final country-crosswalk aggregate geography rows和 794 个 aggregate/non-join industries；
- BEA FDI：11,610 -> 7,600，排除 3,060 个 final aggregate geography rows和 950 个 aggregate/non-join industries；
- Mexico FDI：596,366 -> 349,576，排除 19,980 residual-country rows 和 226,810 sector/subsector aggregate rows；denominator 中 43,780 confidential detail rows继续为 missing。

所有可观测 metrics 的 explicit-status value coverage 为 100%。这只表示每个值有明确 mapping status，不表示所有值都进入 priority sectors。

## 6. M2：产品冲击与贸易合并底表

### 6.1 M2.1 product treatment panel

- builder：`build_product_treatment_panel.py`。
- config：`product_treatment_rules.yaml`。
- output：`data/processed/harmonized/product_treatment_hs6_year.parquet`。
- key：`analysis_hs6, year`。
- grid：5,202 products × 11 years = 57,222 rows；duplicate 0。

设 HS2017 source code 为 `h`，analysis product 为 `a`，2017 China imports 为 `M_CHN,h`，2017 total U.S. imports 为 `M_US,h`，年份 `t` 的法定税率为 `tau_h,t`。对映射到 `a` 的 source codes：

```text
china_import_share_a = sum_h(M_CHN,h) / sum_h(M_US,h)

tariff_exposure_a,t = sum_h(M_CHN,h * tau_h,t) / sum_h(M_US,h)
```

`tariff_rate_a,t` 默认按 China imports 加权；若 China denominator 为 0，则按 total imports 加权；若 total denominator 也为 0，则保留 maximum legal source rate。缺少 2017 import denominator 时 share/exposure 保持 missing，不能伪造 0 share。

处理细节：

- policy input 55,308 rows / 5,028 HS2017 codes；
- BACI weight universe 5,384 codes；
- 356 个 weight codes 不在 legal exposure panel 中，显式记为 not listed、rate 0；
- 108 个 analysis products 接收多个 HS2017 source codes，使用上述 import weights；
- product mapping status 为：56,771 rows `mapped_hs17_import_weighted`、319 rows `mapped_hs17_no_2017_import_denominator`、132 rows `no_hs17_baci_weight_mapping`；
- 2014-2017 treatment 全为 0；
- tariffed product count：2018 为 3,574，2019-2024 为 4,865；
- exposure numerator 最大 reconciliation gap 为 USD 0.000053，仅为 floating-point 量级；
- gross statutory interpretation flags 固定：historical exclusions false，2024 review false/separate。

### 6.2 M2.2 connector trade legs

- builder：`build_connector_trade_panel.py`。
- config：`connector_trade_rules.yaml`。
- output：`connector_trade_legs_hs6_year.parquet`。
- key：`connector_iso3, analysis_hs6, year`。
- grid：13 connectors × 5,202 products × 11 years = 743,886 rows；duplicate 0。

四个金额字段：

1. `china_to_usa_value_usd`：China -> USA product-year benchmark；为便于 connector 内比较重复到每个 connector，不能跨 connector 加总；
2. `china_to_connector_value_usd`：China -> connector；
3. `east_asia_to_connector_value_usd`：extended East Asia -> connector；KOR 和 TWN connector 行排除 canonical self-trade；
4. `connector_to_usa_value_usd`：connector -> USA。

稀疏 BACI 中不存在的 bilateral product row 在完整 grid 上记为 0 trade value，同时 `source_row_count=0`，明确表示“完整来源中没有 reported row”，不是原始 missing 被任意填补。BACI quantity 因 source missingness 在 M2.2 中完全省略。

| Trade leg | source/output total USD | gap |
|---|---:|---:|
| China -> connector | 8,021,758,704,297 | 0 |
| East Asia -> connector | 13,242,306,197,894 | 0 |
| connector -> USA | 12,370,620,858,085 | 0 |

TWN 使用 BACI `S19` proxy，并在 output 中保留 proxy flag。

### 6.3 M2.3 trade-treatment merge

- builder：`merge_trade_treatment_panel.py`。
- config：`trade_treatment_merge_rules.yaml`。
- output：`connector_trade_hs6_year.parquet`。
- join：trade `743,886` rows 对 treatment `57,222` rows，keys 为 `analysis_hs6, year`，cardinality 为 many-to-one，left join。
- 结果：743,886 rows；unmatched trade rows 0；product/sector fields 差异 0；treatment 在同一 product-year 的 connector rows 间恒定。

| Field | input/output total USD | gap |
|---|---:|---:|
| China -> USA repeated benchmark | 69,463,714,130,434 | 0 |
| China -> connector | 8,021,758,704,297 | 0 |
| East Asia -> connector | 13,242,306,197,894 | 0 |
| connector -> USA | 12,370,620,858,085 | 0 |

注意：第一行是单一 China-USA product-year benchmark 在 13 个 connector 上重复后的总和，只能用于 merge 前后 reconciliation，不能解释为实际贸易总量。treatment 变量同样不能跨 connector 相加。

### 6.4 M2.4-M2.5 Census harmonization 和 15-origin scope

- builder：`build_census_harmonized_panels.py`。
- config：`census_harmonization_rules.yaml`。
- monthly output：`census_imports_hs6_monthly_harmonized.parquet`，4,906,643 rows，key `origin_iso3, analysis_hs6, year, month`，保持 sparse event-study interface。
- annual output：`census_imports_hs6_annual.parquet`，15 × 5,202 × 11 = 858,330 rows，key `origin_iso3, analysis_hs6, year`，完整 grid。

处理逻辑：

1. 按年份分配 HS revision；
2. 用 M1 canonical bridge 映射到 `analysis_hs6`；
3. chapters 98/99 作为 U.S. national special classifications 留在 coverage audit，不进入 internationally comparable output；
4. unresolved nonstandard codes 不强行映射；
5. import value、customs value、duties、dutiable value 四个 additive fields 按 origin-product-month 聚合；
6. annual 表按 reported monthly rows 求和，同时记录 observed month count；
7. 因每个 configured origin-year 的 12 个 source months 完整，annual complete grid 中不存在的 product rows 才可解释为 0 reported import；
8. quantity disabled；15-origin scope flag 和 `is_all_origin_denominator=false` 写入输出。

Coverage：gross mapped import value 97.286356%；排除 chapters 98/99 后 eligible coverage 99.997284%。Excluded national-special value USD 522,585,907,029；unresolved nonstandard value USD 509,271,053。

四个金额字段在 eligible input、monthly output 和 annual output 之间 gap 均为 0。

### 6.5 M2.6 Section 301 2024 exact HTS extension

- builder：`build_section301_2024_review_extension.py`。
- config：`section301_2024_review_rules.yaml`。
- output：`data/processed/policy/section301_2024_review_exact_hts.parquet`。
- key：`hts_code`；367 rows；duplicate 0。

365 rows 对 whole code 生效，2 rows 为 description-scoped。代码层级为 362 个 HTS8 和 5 个 HTS10；rate distribution 与 official extraction 一致：355 rows at 25%，2 at 50%，10 at 100%；effective date 2024-09-27。

输出明确包含 `historical_hs6_panel_merged=false`、`requires_modern_hts_concordance=true`，并且不存在 `analysis_hs6`。在 separately validated modern-HTS bridge 和 scope rule 出现之前，不允许截取六位并入历史面板。

### 6.6 M2 的执行顺序和设计原因

M2 不是在一张表上原地连续覆盖，而是保留纯 trade legs、独立 treatment 和 merge 后表。这样可以在每一步比较行数、key、总量和字段一致性，避免 treatment merge 改变贸易值却无法定位。Census 也保持独立，因为它是 monthly timing validation 和 configured-origin evidence，不是 BACI all-country annual trade 的替代品。

## 7. 缺失、零值、负值、aggregate 和重复字段合同

### 7.1 missing 与 zero

| 情况 | 正确值 | 原因 |
|---|---|---|
| BACI bilateral product row 在完整 source 中不存在 | M2 complete grid 可记 0，附 source-row-count 0 | 明确的 no reported trade row |
| Census annual product row 不存在 | 仅在 origin-year 12 个月 source 完整时记 0 reported imports | 完整月度来源支持 |
| Census quantity = 0, unit `-` | unavailable，不是真实 0 | source placeholder |
| BEA `(D)` / size-range code | missing + suppression flag | 官方保密/区间码 |
| Mexico `C` | missing + confidential flag | 官方保密 |
| AMNE employment | missing/unavailable | 当前来源没有该指标 |
| policy product 无 2017 denominator | share/exposure missing | 不能把未知 share 当 0 |

### 7.2 负值

- ICIO accounting negatives 保留；下游 aggregation 要保留 accounting residual 解释。
- AMNE allocated value added 的负值保留。
- BEA FDI negative position/flows/income 保留；flow reversal 和 direction convention 具有经济含义。
- Mexico negative FDI flows 保留。
- Coverage 计算对 signed metrics 使用 absolute observed value，仅用于避免分母抵消；输出原值不取绝对值。

### 7.3 aggregate、residual、proxy 和 repeated benchmark

- aggregate geography 不获得普通 country join eligibility。
- Mexico `Otros países` 是 residual group，无 ISO3；可在官方 total reconciliation 中单独使用，但不能作为普通国家。
- BACI `S19` 是 TWN proxy，任何 TWN 结果必须保留 proxy disclosure。
- BEA Transportation equipment 不是 autos one-to-one mapping。
- `china_to_usa_value_usd` 和 product-year treatment 在 connector panel 中重复，不能跨 connector 加总。

## 8. join cardinality 和总量守恒规则

| Join/aggregation | 允许的 cardinality | 必须验证 |
|---|---|---|
| source country -> country master | many source rows to one crosswalk row | source key 唯一；aggregate/residual 不进入 country join |
| source HS revision -> canonical HS2012 | many source rows to one target允许；每个 source code 只有一个 canonical target | weight=1；value 不膨胀 |
| full HS correlation | many-to-many 仅用于 audit | numeric weight 必须为空；禁止聚合 |
| product -> analysis sector | one product to one status/sector | eligible weight=1；ambiguous/excluded null |
| source sector -> analysis sector | one source code to one status；ambiguous 不拆分 | key 唯一；aggregate level 排除 |
| HS2017 policy -> analysis product-year | many source codes to one analysis product | import-weighted aggregation；numerator reconciliation |
| treatment -> connector trade | many connector rows to one product-year treatment row | all trade rows match；trade totals不变 |
| product -> sector in M3.1 | many products to one connector-sector-year | 以 `analysis_hs6` many-to-one 连接 canonical crosswalk；只使用 eligible weight=1；全部匹配；内嵌 sector 字段一致；聚合前后 value 守恒 |
| annual sector-year -> M3.2 window | 4/2/5 annual rows to one connector-sector-window；comparison 为三个 window rows to one connector-sector | 每个年度观察恰好分配一次；禁止 partial-window mean；long/comparison keys 唯一；mean×years 与 annual sum 守恒 |

任何实际出现的 many-to-many join 都必须停止，先建立显式权重并证明 source-code 内权重和为 1。不能依赖 pandas/SQL 默认行为接受 row multiplication。

## 9. 当前 validation 证据总表

| Validation report | 状态 | 核心结论 |
|---|---|---|
| `data_merge_input_manifest` | PASS | 8 inputs，identity/schema/year/build evidence 完整 |
| `data_merge_input_quality_audit` | PASS | hard failures 0，所有 expected limitations 已记录 |
| `analysis_sample_v1_validation` | PASS | country/sector/time/baseline 范围冻结 |
| `country_crosswalk_validation` | PASS | 611 rows，duplicate/unresolved 0 |
| `time_aggregation_rules_validation` | PASS | 39 metric rules，频率和 stock/flow rules 通过 |
| `hs_revision_bridge_validation` | PASS | canonical/no-expansion、official hash 和 coverage 通过 |
| `product_sector_crosswalk_validation` | PASS | 5,202 products，explicit status 100% |
| `source_sector_crosswalk_validation` | PASS | 517 source codes，explicit status 100% |
| `concordance_coverage` | PASS | 7 crosswalk keys duplicate 0；available metrics status coverage 100% |
| `product_treatment_panel_validation` | PASS | 57,222 rows，full grid，pre-2018 zero，numerator reconcile |
| `connector_trade_panel_validation` | PASS | 743,886 rows，full grid，trade legs gap 0 |
| `trade_treatment_merge_validation` | PASS | unmatched 0，trade totals gap 0 |
| `census_harmonized_panels_validation` | PASS | 4 monetary fields monthly/annual gap 0 |
| `section301_2024_review_extension_validation` | PASS | 367 exact HTS rows，与历史面板隔离 |
| `connector_trade_sector_panel_validation` | PASS | 1,001 rows、duplicate 0、4 flows eligible/full-universe gaps 0、policy formula gaps 0、deterministic SHA256 match、70 Stata aliases valid |
| `connector_trade_sector_window_validation` | PASS | 273/91 rows、duplicate 0、4/2/5 years complete、level/coverage/policy/growth gaps 0、two deterministic SHA256 matches、79/142 Stata aliases valid |
| `connector_trade_sector_growth_diagnostics_validation` | PASS | 364 rows、4 flows per cell、small-base/abnormal/winsor formulas 复算、deterministic SHA256 match、64 Stata aliases valid |
| `connector_trade_reorganization_indicators_validation` | PASS | 55,081/91/91 rows、replacement/source ratio/exposure/co-movement 复算、three deterministic SHA256 matches、56/92/49 Stata aliases valid |
| `connector_trade_sector_common_panel_validation` | PASS | 91 × 152、one-to-one full match、13 × 7 complete grid、21/49/21 groups、no selection、deterministic SHA256 match、152 Stata aliases valid |
| `connector_trade_sector_sensitivity_validation` | PASS | 1,092/182/364 rows、time/source/exposure formulas 独立复算、complete windows、nested/self-trade/missing states、three deterministic SHA256 matches、56/64/47 Stata aliases valid |
| `production_icio_validation` | PASS | 85,050/10,080 rows、source/analysis keys duplicate 0、81 geography/50 sectors、80-country × 6-sector × 3-year × 7-metric grid、negative accounting/source partition/reconciliation preserved、two deterministic SHA256 matches、54/43 Stata aliases valid |
| `production_amne_validation` | PASS | 7,560,318/53,760 rows、parent/host keys duplicate 0、positive/full-zero source universes、80-country × 6-sector × 16-year host grid、direct/allocated/unavailable/ROW/reconciliation states preserved、two deterministic SHA256 matches、71/56 Stata aliases valid |

## 10. 当前 processed 输出注册表

M0-M2 SHA256 来自 2026-07-19 validation snapshot，并在 2026-07-27 整理本档案时再次读取本地文件核对。M3.1-M3.5 SHA256 来自 2026-07-28、M3.6 SHA256 来自 2026-07-29、M4.1-M4.2 SHA256 来自 2026-08-02、M4.3 SHA256 来自 2026-08-03 的正式构建和第二次确定性构建；全部与各自 validation JSON 一致。

| Output | Rows | Natural key | SHA256 |
|---|---:|---|---|
| `country_crosswalk.parquet` | 611 | source_name, source_country_id | `29b4b4b936d8c974c2b9f9d9eaa37b9c5d67e170e94c39ccdbd5088be3adc4c6` |
| `time_aggregation_rules.parquet` | 39 | input_id, metric_name | `94c9b5ee7e7f6bc91fcf67a251a0cb39c2aa64b1303fdce7948280039899bfb4` |
| `hs_to_hs2012_conversion.parquet` | 16,209 | source_revision, source_hs6 | `1793d5baba30a135efa240f264e95f7ac5dc73cbea5d02e2d1999fc2a97577f9` |
| `hs_revision_correlations.parquet` | 27,726 | source_revision, source_hs6, target_hs6 | `92a498abfc28eb3e5f943c80ea4b98b87331526db430b68b5891d666ca14094a` |
| `census_hs6_year_to_hs2012.parquet` | 57,347 | year, source_hs6 | `d0be24214c1c83b31afc4fc55bf7d15ff677594c3e0accee12410021f88b7e1d` |
| `product_sector_crosswalk.parquet` | 5,202 | analysis_hs6 | `201c1d47ee861fe300db1574b6e80288bbeaec17e19fe4d368205b6d84995c09` |
| `source_sector_crosswalk.parquet` | 517 | source_name, source_sector_level, source_sector_code | `99ab34b27a5a37ec4db4cb2fd65d35c48732d92f5363a04e7565d5b852142fe9` |
| `product_treatment_hs6_year.parquet` | 57,222 | analysis_hs6, year | `498454e124c1b04913ebe2aeb2baa8aaaa54dca548db52d5d59d9785eda72455` |
| `connector_trade_legs_hs6_year.parquet` | 743,886 | connector_iso3, analysis_hs6, year | `9f0817d1192c372109e68c205749d0933550c62d847bae2a30b86039d2dbd149` |
| `connector_trade_hs6_year.parquet` | 743,886 | connector_iso3, analysis_hs6, year | `01fbbe43a8e067ed165d21f72d3b733fe240ec098957e99085fff67b16571fdb` |
| `census_imports_hs6_monthly_harmonized.parquet` | 4,906,643 | origin_iso3, analysis_hs6, year, month | `2ed0c595a0b25363151ea429fc0d1cee748318432ddf3f032f482ca68ddda14a` |
| `census_imports_hs6_annual.parquet` | 858,330 | origin_iso3, analysis_hs6, year | `1d06eebc2df07304ecbc1fb7d0bd1617eab63c522f9d0168c0020d5a19d4b0b1` |
| `section301_2024_review_exact_hts.parquet` | 367 | hts_code | `bc34c2bda7b3866bd0cc5cdafd67ef068d7f52406df99ea4c45813e06478ec2f` |
| `connector_trade_sector_year.parquet` | 1,001 | connector_iso3, analysis_sector, year | `95e547267892c4bc883788542f0e59ba284441b42f4ce1d379aea71a2f978c8c` |
| `connector_trade_sector_window.parquet` | 273 | connector_iso3, analysis_sector, window_id | `310da7f289d8760d3ead34215a294be18275c758a2084cfd9f905988b695e704` |
| `connector_trade_sector_window_comparison.parquet` | 91 | connector_iso3, analysis_sector | `be5f3a025a81d36d5a9bb1bd137d4bed9325a68ab5f1cb7f4d946a2373fbeb04` |
| `connector_trade_sector_growth_diagnostics.parquet` | 364 | connector_iso3, analysis_sector, flow_id | `fe69d953cd84a2acfc64ddb17b1ee57e3d0e44f7b44cad348f9016aee7e0953d` |
| `connector_trade_product_reorganization_window.parquet` | 55,081 | connector_iso3, analysis_hs6 | `1c83dc1070656c903d625b2e85c82ea6e7afa18535105351ccef24a405ed2c34` |
| `connector_trade_sector_reorganization_indicators.parquet` | 91 | connector_iso3, analysis_sector | `f13c5f8aa0c4402d0b467a06a6b99ba8ddc8389d47ede9ba8c8036275c1d74f2` |
| `connector_trade_sector_product_comovement.parquet` | 91 | connector_iso3, analysis_sector | `3095cd39a7355ce6968e0e5c29956841fd9e40bc72238d06aafe8d3ef0c3b0f1` |
| `connector_trade_sector_common_panel.parquet` | 91 | connector_iso3, analysis_sector | `36c58c229f3f43e86f7ff7570fc6a1ffe08ccb8fd3259bb5853abece3171f682` |
| `connector_trade_sector_time_window_sensitivity.parquet` | 1,092 | connector_iso3, analysis_sector, flow_id, window_spec_id | `1594fadeb348f88e07b2ec8f43ca3708f49f9e06a0b78fafe24ffb6417635aad` |
| `connector_trade_sector_source_bloc_sensitivity.parquet` | 182 | connector_iso3, analysis_sector, source_bloc_id | `67fbf760adb01a18d4e0e4f9ddd44eef9f3d2d2496a0a60d358cf8eab77e1eda` |
| `connector_trade_sector_exposure_definition_sensitivity.parquet` | 364 | connector_iso3, analysis_sector, exposure_definition_id | `96144e95dd525103b658ed7220a15d2f3c7c7acf79ea3f314314112971dc7cbd` |
| `production_icio_source_sector_long.parquet` | 85,050 | source_name, source_country_id, model_sector, year, metric_name | `266ff08c5bd26e00a08cb9f3654b7c83354d02da79cca036d65ccd68d0054110` |
| `production_validation_icio_long.parquet` | 10,080 | country_iso3, analysis_sector, year, source_name, metric_name | `e8bdc6070581f5a1697adba605ef8eac3e7c40a5946779a627ec08ea673315f0` |
| `production_amne_parent_host_sector_long.parquet` | 7,560,318 | source_name, source_host_country_id, source_parent_country_id, model_sector, year, metric_name | `6e3d0a77838b9c1d0cbae6445ee9b3f5637114747e51a148162c720d26605bcb` |
| `production_validation_amne_host_sector_long.parquet` | 53,760 | country_iso3, analysis_sector, year, source_name, metric_name | `b9219fbfe2852f5ca7088bcedf290526479147a57c3b63cc0a693194cc499179` |

## 11. 复现入口和执行顺序

从项目根目录运行。每一步失败时停止，不继续生成依赖该步骤的下游结果。

```powershell
# M0
python code\data_processing\build_input_manifest.py --project-root . --overwrite
python code\data_processing\audit_input_quality.py --project-root . --overwrite
python code\data_processing\validate_analysis_sample.py --project-root . --overwrite

# M1
python code\data_processing\build_country_master.py --project-root . --overwrite
python code\data_processing\build_time_rules.py --project-root . --overwrite
python code\data_processing\build_hs_revision_bridge.py --project-root . --overwrite
python code\data_processing\build_product_sector_crosswalk.py --project-root . --overwrite
python code\data_processing\build_source_sector_crosswalk.py --project-root . --overwrite
python code\data_processing\build_concordance_coverage_report.py --project-root . --overwrite

# M2
python code\data_processing\build_product_treatment_panel.py --project-root . --overwrite
python code\data_processing\build_connector_trade_panel.py --project-root . --overwrite
python code\data_processing\merge_trade_treatment_panel.py --project-root . --overwrite
python code\data_processing\build_census_harmonized_panels.py --project-root . --overwrite
python code\data_processing\build_section301_2024_review_extension.py --project-root . --overwrite

# M3.1
python code\data_processing\build_connector_trade_sector_panel.py --project-root . --overwrite

# M3.2
python code\data_processing\build_connector_trade_sector_window_panel.py --project-root . --overwrite

# M3.3
python code\data_processing\build_connector_trade_sector_growth_diagnostics.py --project-root . --overwrite

# M3.4
python code\data_processing\build_connector_trade_reorganization_indicators.py --project-root . --overwrite

# M3.5
python code\data_processing\build_connector_trade_sector_common_panel.py --project-root . --overwrite

# M3.6
python code\data_processing\build_connector_trade_sector_sensitivity.py --project-root . --overwrite

# M4.1
python code\data_processing\build_production_icio_long.py --project-root . --overwrite

# M4.2
python code\data_processing\build_production_amne_long.py --project-root . --overwrite

# M4.3
python code\data_processing\build_production_bea_mne_long.py --project-root . --overwrite

# 审计 PDF
python code\data_processing\build_data_processing_audit_pdf.py --project-root . --overwrite
python code\data_processing\build_data_processing_audit_pdf.py `
  --project-root . `
  --source docs\variable_construction_catalog.md `
  --output output\pdf\variable_construction_catalog.pdf `
  --overwrite
```

当前 M0-M4.3 还没有单一 orchestration entry；它是 M7.1 的必做项。合作者若现在复核，应按上述顺序执行并逐个查看同名 validation JSON/Markdown。完整重跑会处理超过 123 million BACI rows，应将临时目录和缓存显式指向项目 F 盘。若只复核 M4.3，先确认 BEA MNE activity、raw manifest、country crosswalk 和 source-sector crosswalk 的 SHA256/schema/key 与 frozen config 一致，再运行 M4.3 builder；两张正式输出先在 `tmp/m4_3_candidates/` 构造和验证，第二次输出写入 `tmp/m4_3_determinism/` 比较，只有全部 PASS 才替换 canonical outputs，两个目录随后由 builder 清除。

## 12. M3-M7 的强制更新协议

### 12.1 每完成一个 checklist 项目的同步要求

在把 `[ ]` 改为 `[x]` 前，必须同时完成：

1. 在本档案对应阶段新增“目的和原因”；
2. 记录 input path、input SHA256、schema、grain 和 natural key；
3. 记录 config 和明确公式；
4. 记录 join type、keys、cardinality 和 expected row count；
5. 记录 missing/zero/suppression/confidentiality/aggregate/allocated/proxy 处理；
6. 记录 output path、row count、natural key、schema version 和 SHA256；
7. 记录 validation checks、tolerance、结果和报告路径；
8. 记录未解决限制和对解释的影响；
9. 更新第 2、9、10、13、14 节；
10. 重建 PDF，检查页码、中文字体、表格换行、无截断，并更新 build summary。

### 12.2 标准阶段记录模板

```text
阶段/任务编号：
执行日期：
执行人/审查人：
目的和经济理由：
输入路径、hash、schema、grain、key：
配置和版本：
转换公式与权重：
join type、keys、cardinality：
missing/zero/negative/aggregate/suppression 处理：
输出路径、rows、key、hash：
validation checks 和 tolerance：
reconciliation：
异常/失败/修复：
未解决限制：
Stata 接口影响：
结论和是否允许下游使用：
```

### 12.3 M3.1 实际执行记录

阶段/任务编号：`M3.1 connector-sector-year annual aggregation`。

执行日期：2026-07-28。

目的和经济理由：把 M2 的 connector-product-year 四条贸易流和 product-year Section 301 treatment 聚合到共同经验 sector，建立后续窗口、replacement 和 ranking 的唯一年度底表。先形成年度 level 和透明分子/分母，可以在构造增长率前发现总量膨胀、错误 sector join、共同 benchmark 重复加总和 denominator 静默归零。

输入和冻结身份：

| Input | Rows | Grain / key | SHA256 |
|---|---:|---|---|
| `data/processed/harmonized/connector_trade_hs6_year.parquet` | 743,886 | `connector_iso3, analysis_hs6, year` | `01fbbe43a8e067ed165d21f72d3b733fe240ec098957e99085fff67b16571fdb` |
| `data/processed/concordances/product_sector_crosswalk.parquet` | 5,202 | `analysis_hs6` | `201c1d47ee861fe300db1574b6e80288bbeaec17e19fe4d368205b6d84995c09` |

配置和版本：

- `configs/connector_trade_sector_rules.yaml`；
- config SHA256 `6a313c01d9bfad6e6e6a2cb508bd787f35bdb0eddeb6e4f491a86d61bdd9ee9d`；
- aggregation version `connector_trade_sector_rules_v1`；
- schema version `connector_trade_sector_year_v1`；
- builder `code/data_processing/build_connector_trade_sector_panel.py`。

Join 和 eligibility：

1. 以 `analysis_hs6` 将 743,886 行 M2 panel left join 到 canonical crosswalk，要求 many-to-one；
2. input key、crosswalk key 和 output key duplicate 均为 0；
3. unmatched crosswalk rows 为 0；
4. M2 内嵌 `analysis_sector`、`sector_status`、`first_round_exclusion`、`is_analysis_sector_eligible` 和 `product_mapping_version` 与 canonical crosswalk mismatch 均为 0；
5. 只有 canonical `is_analysis_sector_eligible=true` 且 `sector_mapping_weight=1` 的 4,237 个产品进入 sector sums；965 个 excluded/outside-manufacturing/residual 产品不进入 sector sums；
6. eligible product counts 固定为 autos 64、electrical equipment 177、electronics 252、machinery 467、medical devices 32、other manufacturing 2,422、textiles/apparel 823。

贸易转换公式：

- 四条年度金额分别为 `sum_h eligible flow_value_usd`；
- 每条流的 `source_row_count` 是 eligible HS6 的 M2 row counts 之和；
- positive-product count 是 sector 内 `flow_value_usd > 0` 的 eligible HS6 数；
- zero-source-product count 是 sector 内 M2 `flow_row_count = 0` 的 eligible HS6 数，因此 source absence 没有被普通零值掩盖；
- excluded amount 和 `included / full-universe value` share 对四条流分别计算。因为非 eligible 产品没有可用于 sector allocation 的有效 weight，这些 coverage 字段在 connector-year 计算后跨 sector 重复，并设置 `coverage_repeated_across_sectors=true`。

Policy 转换公式：

1. 先把跨 connector 重复的 treatment 按 `analysis_hs6, year` 去重；
2. `sector_tariff_exposure_numerator_usd = sum_h(china_import_value_2017_h × tariff_rate_china_weighted_h,t)`；
3. `sector_tariff_rate_china_weighted = numerator / sum_h(china_import_value_2017_h)`；
4. `sector_tariff_exposure = numerator / sum_h(total_us_import_value_2017_h)`；
5. `sector_china_import_share_2017 = sum_h(china_import_value_2017_h) / sum_h(total_us_import_value_2017_h)`；
6. tariffed-product breadth/value shares由各自 count/value numerator 除以透明 sector denominator 重算，不对 product-level share 取平均；
7. 17 个 `mapped_hs17_no_2017_import_denominator` eligible products 和 11 个 `no_hs17_baci_weight_mapping` eligible products以独立 count/share 字段保留，不能当作普通零 denominator。

输出：

- path：`data/processed/harmonized/connector_trade_sector_year.parquet`；
- grain/key：`connector_iso3, analysis_sector, year`；
- rows/columns：1,001 / 70，等于 13 connectors × 7 sectors × 11 years；
- output SHA256：`95e547267892c4bc883788542f0e59ba284441b42f4ce1d379aea71a2f978c8c`；
- `china_to_usa_value_usd` 和 policy fields 跨 connector 重复用于比较；`common_benchmarks_not_additive_across_connectors=true` 与 `treatment_repeated_across_connectors=true` 禁止错误加总；
- TWN 的 77 个 sector-year rows 全部保留 `connector_is_proxy=true`；
- 本输出不含 quantity、时间窗口、增长率、small-base、replacement ratio、ranking、production-side 或 structural moments。

贸易 reconciliation：

| Flow | Eligible product total USD | Sector output total USD | Excluded total USD | 最大 eligible/full reconstruction gap USD |
|---|---:|---:|---:|---:|
| China→connector | 7,277,654,649,355 | 7,277,654,649,355 | 744,104,054,942 | 0 |
| East Asia→connector | 11,664,115,552,239 | 11,664,115,552,239 | 1,578,190,645,655 | 0 |
| connector→USA | 9,871,984,981,362 | 9,871,984,981,362 | 2,498,635,876,723 | 0 |
| China→USA | 67,908,975,727,203 | 67,908,975,727,203 | 1,554,738,403,231 | 0 |

Validation 和 tolerance：

- report：`data/validation/connector_trade_sector_panel_validation.json` 与 `.md`；
- status：`PASS`，failure count 0；
- value tolerance：USD 0.01；四条流的 global、connector-year eligible、excluded 和 full-universe reconstruction gaps 实际均为 0；
- ratio tolerance：`1e-12`；九个 policy rate/share 字段最大绝对公式误差实际均为 0；
- China→USA、policy 和 coverage repeated-field inconsistency count 均为 0；
- required numeric missing count 为 0；zero-source-product diagnostics 在输出中保留；
- 70 个 canonical 字段均有冻结 Stata alias，alias 缺失、额外和重复均为 0，最长 14 字符；
- 在项目 `tmp/m3_1_determinism/` 第二次构建，SHA256 与 canonical output 完全一致；随后确认临时目录已清除。

异常/修复：第一次通过的开发构建把 sector eligible count 命名为较含糊的 `included_product_count`。在写入正式合同前将其改为 `sector_eligible_product_count`，重建后 validation 和确定性检查重新 PASS。该开发中间 schema 未登记为正式输出。

Stata 接口影响：M3.1 只冻结 alias 和 32 字符约束，不提前导出 `.dta`。M7 仍需实际 export、`isid conn_iso3 ana_sector year`、storage/label 检查和 batch `.do` 验证。

结论：M3.1 单模块允许作为 M3.2 的输入。它不能用于声称窗口增长、replacement 或排名已经完成。

### 12.4 M3.2 实际执行记录

阶段/任务编号：`M3.2 complete trade windows and post-pre growth`。

执行日期：2026-07-28。

目的和经济理由：M3.1 的年度 panel 能观察逐年水平，但 pre、shock 和 post 窗口长度分别为 4、2、5 年，直接比较窗口总和会机械地把窗口长度误当成经济增长。M3.2 因此先把每个 connector-sector 的年度 level 转成完整窗口年度平均，并把 post-pre level change、Davis-Haltiwanger growth 和 positive-base log growth 放在单独的 comparison 表。采用两表接口，是为了让 growth 在每个 connector-sector 只出现一次，而不是在 pre/shock/post 三行中重复。

输入和冻结身份：

| Input | Rows/columns | Grain / key | SHA256 |
|---|---:|---|---|
| `data/processed/harmonized/connector_trade_sector_year.parquet` | 1,001 / 70 | `connector_iso3, analysis_sector, year` | `95e547267892c4bc883788542f0e59ba284441b42f4ce1d379aea71a2f978c8c` |
| `configs/time_windows.yaml` | configuration | pre/shock/post definitions | `d1daeed066db7cf734c15c804f31eaaf66a7c07b335f3c227a6c9effffd6ebb5` |

M3.1 input 的 Arrow schema signature SHA256 冻结为 `37fd30c8442cc1aea9045cd6b4904be851187e1b7ace21db26ee65d4de7a6256`。Builder 同时检查 input row count、70-column schema、年度 natural key、`schema_version=connector_trade_sector_year_v1` 和 `m3_sector_aggregation_version=connector_trade_sector_rules_v1`，不能只凭文件名接受输入。

配置和版本：

- config：`configs/connector_trade_sector_window_rules.yaml`；
- config SHA256：`95d42ee146b1e0cf6e98261b46e5db52bf81000770d12d55da3371350d50058b`；
- construction version：`connector_trade_sector_window_rules_v1`；
- long schema：`connector_trade_sector_window_v1`；
- comparison schema：`connector_trade_sector_window_comparison_v1`；
- builder：`code/data_processing/build_connector_trade_sector_window_panel.py`。

窗口分配和 cardinality：

1. `pre=2014-2017`，expected years 4；`shock=2018-2019`，expected years 2；`post=2020-2024`，expected years 5；
2. 1,001 个年度 observations 每行恰好分配到一个窗口；unassigned row count 0，overlapping year count 0；
3. 每个 `connector_iso3, analysis_sector, window_id` 的 distinct year count 必须严格为 4/2/5；91 个 cells 在每个窗口都完整，partial-window mean 数为 0；
4. long aggregation 是 4/2/5 annual rows to one connector-sector-window；comparison 是三个 long rows to one connector-sector；
5. long 和 comparison 的自然键 duplicate 都为 0。

四条 flow 转换：

```text
x_pre  = mean(x_t, 2014-2017)
x_shock = mean(x_t, 2018-2019)
x_post = mean(x_t, 2020-2024)

change_post_pre = x_post - x_pre
dh_growth = 2 * (x_post - x_pre) / (x_post + x_pre)
log_growth = ln(x_post) - ln(x_pre), only if x_pre > 0 and x_post > 0
```

金额、source-row count、positive-product count 和 zero-source-product count 都从 M3.1 年度字段取窗口算术平均。Count annual mean 可以是非整数，因此 window-level diagnostics 使用 double；M3.1 的年度整数 count 不被覆盖。Builder 对每条流独立验证 `annual mean × observed years = M3.1 annual sum`。

Zero 和负值规则：

- pre=post=0 时 DH 和 log 都 missing；
- 只有一端为 0 时 DH 为 ±2，log missing；
- 两端都大于 0 时 log 才定义；
- 不加 epsilon，不把 undefined growth 改成 0；
- 负 change 和负 growth 保留，不截断、不 winsorize；
- 当前数据四条流 pre/post zero 均为 0，每条流 91 个 log growth 均定义；
- 当前负 post-pre change cells 为 China→connector 3、East Asia→connector 5、connector→USA 6、China→USA 26，全部保留。

Coverage 转换：

1. 对每个 connector-year，把 7 个 eligible sector flows 求和，得到完整 eligible product universe value；
2. 从跨 sector 重复的 M3.1 coverage 字段只取一份 excluded value；
3. excluded annual mean 是窗口内 excluded 年度金额的算术平均；
4. included-value share 重新计算为 `sum_t eligible / sum_t(eligible + excluded)`，不是年度 share 的简单平均；
5. coverage 仍在 connector-window 粒度生成后跨 sector 重复，`coverage_repeated_across_sectors=true`，禁止跨 sector 加总。

Policy 转换：

1. 从跨 connector 重复的 M3.1 policy 字段只取一个 connector，形成 sector-year policy 表；
2. `sector_tariff_exposure_numerator_usd_annual_mean` 是年度 numerator 的窗口平均；
3. `sector_tariff_rate_china_weighted` 与 `sector_tariff_exposure` 分别用 annual-mean numerator 除以固定的 2017 China-import/total-import denominator；
4. tariffed product count 和 tariffed China/total import values先取年度平均，再重算三类 tariffed shares；
5. denominator observed/missing/zero/no-HS2017 counts 和 shares 显式保留；每个窗口仍保留 17 个 zero-denominator 和 11 个 no-HS2017-mapping eligible products；
6. pre policy exposure 当前为 0，但没有为 policy exposure 构造 percentage/log growth；comparison schema 中 policy growth field count 为 0。

输出：

| Output | Rows/columns | Grain / key | SHA256 |
|---|---:|---|---|
| `data/processed/harmonized/connector_trade_sector_window.parquet` | 273 / 79 | `connector_iso3, analysis_sector, window_id` | `310da7f289d8760d3ead34215a294be18275c758a2084cfd9f905988b695e704` |
| `data/processed/harmonized/connector_trade_sector_window_comparison.parquet` | 91 / 142 | `connector_iso3, analysis_sector` | `be5f3a025a81d36d5a9bb1bd137d4bed9325a68ab5f1cb7f4d946a2373fbeb04` |

Long 表含 annual-mean levels、diagnostics、ratio-of-sums coverage、policy summaries、window metadata、TWN proxy、版本和 non-additive/repeated flags。Comparison 表含四条流的 pre/shock/post、post-pre change、DH/log growth、flow-specific zero/defined/year-count fields，并展开 coverage 和随窗口变化的 policy levels；固定 2017 denominators 和 denominator exception fields只保留一份。

Validation 和 tolerance：

- report：`data/validation/connector_trade_sector_window_validation.json` 与 `.md`；
- status：`PASS`，failure count 0；
- long/comparison rows：273/91；columns：79/142；key duplicates：0/0；
- pre/shock/post observed year ranges严格为 4/2/5，incomplete cells 全部为 0；
- value tolerance：USD 0.01；四条 flow 的 `mean × years` reconciliation 最大差额实际均为 USD 0；
- ratio tolerance：`1e-12`；coverage、policy、long-to-comparison、change、DH 和 log 的最大公式误差实际均为 0；
- DH out-of-range count 0，infinite growth count 0，required numeric missing count long/comparison 均为 0；
- China→USA/policy repeated-field 与 coverage repeated-field inconsistency count 均为 0；
- TWN long/comparison rows 为 21/7，proxy false count 为 0；
- required repeated/non-additive flag false count 为 0；
- long 79 个、comparison 142 个 Stata aliases 全部覆盖、无重复、最长 13 字符。

确定性和候选输出规则：

1. Builder 先把两张 candidate Parquet 写入项目 F 盘 `tmp/m3_2_candidates/`，不直接覆盖 canonical outputs；
2. 独立重新读取冻结输入，在 `tmp/m3_2_determinism/` 第二次构建两张 Parquet；
3. long second-build SHA256 与 `310da7...e704` 完全一致；comparison second-build SHA256 与 `be5f3...eb04` 完全一致；
4. 只有 validation 全部 PASS 才把 candidates提升为 canonical outputs；
5. candidate 与 determinism 临时目录随后均确认不存在；
6. 任何硬性检查失败时不替换 canonical outputs、不改 checklist、不提交。

异常/修复：开发构建通过数值验证，但 comparison 表逐列插入 142 个字段时 pandas 报告 DataFrame fragmentation 性能警告。该警告不改变结果，但会污染正式运行日志。Builder 改为收集 derived columns 后一次性 `concat`，重新构建后警告消失，两张输出 SHA256 与修改前完全相同，validation 再次 PASS。

Stata 接口影响：M3.2 只冻结 resolved aliases 和 32 字符约束，不提前导出 `.dta`。M7 需分别生成 long window 与 comparison `.dta`，执行 `isid conn_iso3 ana_sector window_id` 和 `isid conn_iso3 ana_sector`，验证 double precision、missing/flags、labels 和 Parquet reconciliation。

结论：M3.2 单模块允许作为 M3.3 的输入。它只提供机械窗口和增长变量；不能声称 small-base、异常增长处理、winsorization、replacement、ranking、production evidence 或 structural moments 已完成。

### 12.5 M3.3 zero/small-base、异常增长与 winsorized sensitivity

#### 12.5.1 输入冻结和模块边界

M3.3 只读取：

`data/processed/harmonized/connector_trade_sector_window_comparison.parquet`

- input SHA256：`be5f3a025a81d36d5a9bb1bd137d4bed9325a68ab5f1cb7f4d946a2373fbeb04`；
- rows/columns：91/142；
- natural key：`connector_iso3, analysis_sector`；
- Arrow schema signature：`8121b99f2557548ff0fcb4fb62602c997b4946a7f4fd585df924f4f04311fa3c`；
- expected schema/construction versions：`connector_trade_sector_window_comparison_v1` / `connector_trade_sector_window_rules_v1`。

冻结规则：

- config：`configs/connector_trade_sector_growth_diagnostic_rules.yaml`；
- config SHA256：`57fb88dce2632114de692b46dd13cd9ea573cec79709af8ce4231339c53cde56`；
- builder：`code/data_processing/build_connector_trade_sector_growth_diagnostics.py`；
- construction version：`connector_trade_sector_growth_diagnostic_rules_v1`；
- output schema：`connector_trade_sector_growth_diagnostics_v1`。

Builder 不修改 M3.2 comparison、M3.2 long、M3.1、M0-M2、raw/archive/legacy 或 `_staging*`。它只把 91 个 connector-sector observations 重整为四条 flow 的自然长表，形成 364 行；不构造 replacement ratio、ranking、production-side fields 或 structural moments。

#### 12.5.2 输出结构和源值继承

输出：

| Output | Rows/columns | Grain / key | SHA256 |
|---|---:|---|---|
| `data/processed/harmonized/connector_trade_sector_growth_diagnostics.parquet` | 364 / 64 | `connector_iso3, analysis_sector, flow_id` | `fe69d953cd84a2acfc64ddb17b1ee57e3d0e44f7b44cad348f9016aee7e0953d` |

`flow_id` 固定为 China→connector、East Asia→connector、connector→USA 和跨 connector 重复的 China→USA benchmark。每个 connector-sector 恰好四行；output key duplicate 0，缺失 flow 的 connector-sector cell 0。

从 M3.2 逐 flow 继承：

- pre/shock/post annual-mean trade levels；
- post-pre level change；
- raw DH growth 和 raw positive-base log growth；
- pre/post zero 与 DH/log defined flags；
- 4/2/5 observed-year counts；
- connector group、BACI code、TWN proxy 和 trade unit；
- M3.2 construction version。

Builder 逐 flow 回接输入并比较上述字段。金额字段容许差额 USD 0.01，growth 容许差额 `1e-12`；所有实际最大差额与 missing mismatch 均为 0。Post-pre change、DH 和 log 又从 pre/post 独立复算，实际公式误差均为 0。负 change 数 3/5/6/26 与 M3.2 完全相同，未截断、未改成缺失。DH 越界数 0，infinite numeric 数 0。

#### 12.5.3 Small-base 规则和原因

规则分为三部分：

1. absolute：`value_usd_pre <= 25,000,000`；
2. sector-relative：在 `flow_id × analysis_sector` 内对 13 个 connectors 的 pre value 取 nearest-rank p10，rank=`ceil(0.10×13)=2`，小于等于第二小值者 flagged；
3. combined：`pre_zero OR absolute OR sector-relative`。

USD 25 million 是 extreme-small annual-mean pre level 的透明绝对门槛；sector-relative p10 防止大型 sector 中绝对金额不小但相对极小的 cell 被忽略。两者并列保留，后续可以分别做 absolute-only、relative-only 和 no-threshold robustness，而不是把一个经验阈值伪装为唯一经济定义。Nearest-rank 而非插值 percentile 使 13-cell 小组的 flagged observation 集清楚、可在 Stata 中复算。

China→USA benchmark 在每个 sector 跨 13 个 connectors 机械重复，对重复值做 connector-relative p10 没有统计含义。因此 91 行明确设为 `sector_relative_threshold_applicable=false`，relative cutoff missing、flag false；该 missing 是不适用状态，不是原始数据缺失。

当前 counts：

| Flow | Absolute | Sector-relative | Combined | Primary DH eligible | No-threshold DH eligible |
|---|---:|---:|---:|---:|---:|
| China→connector | 0 | 14 | 14 | 77 | 91 |
| East Asia→connector | 0 | 14 | 14 | 77 | 91 |
| connector→USA | 4 | 14 | 14 | 77 | 91 |
| China→USA | 0 | 0 | 0 | 91 | 91 |

四个 absolute-small cells 是 MAR electrical equipment、MAR machinery、MAR medical devices 和 TUR medical devices 的 connector→USA pre levels；均已包含在相对门槛的 14 个 cells 中。`dh_growth_primary_eligible` 和 `log_growth_robustness_eligible` 排除 combined small base；`dh_growth_no_threshold_eligible` 只要求 DH defined，使合作者可以复核阈值敏感性。当前没有 pre/post zero，但 zero rule 仍存在于 schema 中。

#### 12.5.4 异常增长规则和保留方式

每个 `flow_id × analysis_sector` 使用：

```text
robust_z = 0.6744897501960817 × (DH - median(DH)) / MAD(DH)
robust_z_outlier = |robust_z| > 3.5
mechanical_extreme = |DH| >= 1.5
abnormal_growth = robust_z_outlier OR mechanical_extreme
```

MAD=0 时不除以 0，robust z missing、defined false。当前 7 个 MAD-zero groups 正好是七个 China→USA sector benchmarks；因为每个 sector 的共同 benchmark 在 13 个 connectors 上重复，共有 91 行预期的 robust-z missing。

当前 robust-z / mechanical / combined counts：

- China→connector：1/0/1；
- East Asia→connector：1/0/1；
- connector→USA：1/3/4；
- China→USA：0/0/0。

六个 combined abnormal cells 为 PHL textiles/apparel 的 China→connector、POL other manufacturing 的 East Asia→connector，以及 IND electronics、MAR medical devices、VNM electrical equipment、VNM other manufacturing 的 connector→USA。`abnormal_growth_is_advisory=true`：这些行不自动删除、不覆盖 raw growth，也不因 flag 本身改变 primary eligibility。这样可以让合作者同时报告含/不含 review flags 的 robustness，避免数据清理规则预先决定结论。

#### 12.5.5 Winsorized sensitivity

Raw DH/log 保持独立字段。另在每个 `flow_id` 的 91-cell pooled sample 内，以 pandas/numpy linear/type-7 quantile 计算 p5/p95，并生成：

```text
winsorized_growth = min(max(raw_growth, p5_flow), p95_flow)
```

DH 与 log 在前三条 connector-specific flows 各有 10 行受影响；China→USA 为 0，因为每个 sector 的 13 行重复使 p5/p95 等于实际最小/最大 sector value。Cutoffs、reference count、affected flag 和 scope 均写入每行。`winsorized_values_for_sensitivity_only=true`；后续 ranking 不能静默用 winsorized value 替代 raw value。Level change 不 winsorize，且 `raw_level_change_preserved=true`。

Winsorization 采用 flow-level pooled sample，而不是 13-cell flow-sector group：后者样本太小，p5/p95 会机械影响每个 sector 的边缘 observations，并把 sector 内相对位置误当成跨 sector 可比的异常值。Pooled p5/p95 只提供透明的总体尾部敏感性；sector heterogeneity 仍由 raw values、sector-relative small-base 和后续 sector-specific ranking 分开处理。

#### 12.5.6 Validation、Stata 和确定性

- validation：`data/validation/connector_trade_sector_growth_diagnostics_validation.json/.md`；
- status/failure count：PASS/0；
- input/output duplicate keys：0/0；
- four-flow incomplete cell count：0；
- connector/sector/flow counts：13/7/4；
- relative reference/rank：13/2；
- MAD-zero groups：7；
- China→USA repeated-field inconsistencies：0；
- TWN rows/proxy false：28/0；
- 64 个 Stata aliases 全覆盖、唯一、不超过 32 字符，实际最长 11；
- required version fields missing count 全部为 0 且各只有一个值；
- output numeric infinities：0。

Builder 先写入项目 F 盘 `tmp/m3_3_candidates/`；随后重新读取冻结输入，在 `tmp/m3_3_determinism/` 完整构造第二张 Parquet。Candidate 与 second-build SHA256 均为 `fe69d9...953d`，完全一致。只有 validation PASS 后 candidate 才替换 canonical output；两个临时目录均确认不存在。

第一次候选运行的数值和核心 flags 通过，但人工 null audit 发现 `m3_window_construction_version` 直接按原 input index 赋给 concat 后 long table，只有前 91 行有值、其余 273 行 missing。该候选没有进入提交。Builder 改为先验证 input version 唯一，再把唯一值作为常量写入 364 行，并新增 version fields zero-missing/one-unique 强制门槛；重建后的最终 SHA256 为上述 `fe69d9...953d`。这说明公式 PASS 不能替代字段级人工核查。

Stata `.dta` 仍留到 M7。届时本表 aliases 应执行 `isid conn_iso3 ana_sector flow_id`，并复核 91 个 relative-cutoff missing 与 91 个 robust-z missing 均只出现在 China→USA 的不适用/MAD-zero状态。

结论：M3.3 允许作为 M3.4 的诊断输入。它已完成 zero/small-base、异常增长和 winsorized sensitivity 规则，但尚未构造 replacement、ranking、production evidence 或 structural moments。

### 12.6 M3.4 replacement、source-input、exposure overlap 和产品共变

#### 12.6.1 目的、输入冻结和自然粒度

目的：在不提前排名的前提下，把 M3.2 的完整窗口 levels、M3.3 的 growth diagnostics、M2 的 eligible HS6 产品变化和 Section 301 product exposure 组合成透明的 descriptive reorganization inputs。单独保留产品窗口表，是为了让 co-movement、exposure overlap 和 value-share 分母可以由合作者从 HS6 重新聚合，而不是只看到无法复核的部门 score。

冻结输入：

| Input | Rows/columns | Natural key | SHA256 | Arrow schema signature |
|---|---:|---|---|---|
| `connector_trade_hs6_year.parquet` | 743,886 / 56 | `connector_iso3, analysis_hs6, year` | `01fbbe43a8e067ed165d21f72d3b733fe240ec098957e99085fff67b16571fdb` | `7191fa2563cc8afdd66ca02db798c57b4923c93579b967275d913fb35818919b` |
| `product_sector_crosswalk.parquet` | 5,202 / 38 | `analysis_hs6` | `201c1d47ee861fe300db1574b6e80288bbeaec17e19fe4d368205b6d84995c09` | `c380c85460210aff3311d846ab00b2cfc9c8f0a7b75025e79f6d2f6465de1af3` |
| `connector_trade_sector_window_comparison.parquet` | 91 / 142 | `connector_iso3, analysis_sector` | `be5f3a025a81d36d5a9bb1bd137d4bed9325a68ab5f1cb7f4d946a2373fbeb04` | `8121b99f2557548ff0fcb4fb62602c997b4946a7f4fd585df924f4f04311fa3c` |
| `connector_trade_sector_growth_diagnostics.parquet` | 364 / 64 | `connector_iso3, analysis_sector, flow_id` | `fe69d953cd84a2acfc64ddb17b1ee57e3d0e44f7b44cad348f9016aee7e0953d` | `2b4f46da6e1ba860e3112b5c78fcc8a1998e69913adc4cf840b038be32e290a3` |

`configs/time_windows.yaml` SHA256 为 `d1daeed066db7cf734c15c804f31eaaf66a7c07b335f3c227a6c9effffd6ebb5`。M3.4 config 为 `configs/connector_trade_reorganization_indicator_rules.yaml`，SHA256 为 `0305b9a2a0904f9eac9953a89f977565a644fc25167e4be7b04dad9a44a7fe4d`；builder 为 `code/data_processing/build_connector_trade_reorganization_indicators.py`；construction version 为 `connector_trade_reorganization_indicator_rules_v1`。

Builder 不信任 M2 内嵌 sector：先以 `analysis_hs6` many-to-one 回接 canonical product-sector crosswalk，核验 743,886 行全部匹配，embedded sector、eligibility 和 mapping version mismatch 均为 0。只有 `is_analysis_sector_eligible=true` 且 `sector_mapping_weight=1` 的 4,237 个 products 进入 M3.4；sector counts 固定为 64、177、252、467、32、2,422、823。

#### 12.6.2 三表输出和窗口构造

| Output | Rows/columns | Grain / key | Schema version | SHA256 |
|---|---:|---|---|---|
| `connector_trade_product_reorganization_window.parquet` | 55,081 / 56 | connector-HS6 / `connector_iso3, analysis_hs6` | `connector_trade_product_reorganization_window_v1` | `1c83dc1070656c903d625b2e85c82ea6e7afa18535105351ccef24a405ed2c34` |
| `connector_trade_sector_reorganization_indicators.parquet` | 91 / 92 | connector-sector / `connector_iso3, analysis_sector` | `connector_trade_sector_reorganization_indicators_v1` | `f13c5f8aa0c4402d0b467a06a6b99ba8ddc8389d47ede9ba8c8036275c1d74f2` |
| `connector_trade_sector_product_comovement.parquet` | 91 / 49 | connector-sector / `connector_iso3, analysis_sector` | `connector_trade_sector_product_comovement_v1` | `3095cd39a7355ce6968e0e5c29956841fd9e40bc72238d06aafe8d3ef0c3b0f1` |

产品表对四条 flow 分别计算 2014-2017 的四年完整 annual mean、2020-2024 的五年完整 annual mean 和 post-pre change。每个产品 cell 的 observed-year counts 严格为 4/5。产品表按 sector 加总后与 M3.2 comparison 八个 flow-window levels 回勾，最大 floating-point gap 为 USD `0.0000152587890625`，低于 USD 0.01 门槛；missing mismatch 为 0。

China→USA benchmark 和 product policy 跨 connector 重复用于比较。逐 HS6 检查 China→USA pre/post/change、post tariff share、post exposure 和 policy mapping status，跨 connector 不一致数均为 0；输出用 repeated/non-additive flags 禁止跨 connector 求和。

#### 12.6.3 Replacement 与 source-input 公式

```text
china_us_decline = max(china_us_pre - china_us_post, 0)
connector_us_gain = connector_us_post - connector_us_pre
replacement_ratio = connector_us_gain / china_us_decline
```

Replacement denominator 必须严格大于 USD 25 million，不能等于门槛；numerator 保留 signed gain，不截成正值；不使用 epsilon，不 cap。91 个 cells 中 26 个 ratio defined，22 个为 positive-gain candidates，4 个 defined cells 保留负 connector gain，65 个 ratio 保持 missing。

China input 和 extended East Asia input 分别构造 level change、M3.3 raw DH/log growth、small-base/primary-eligibility/abnormal flags和同窗口 input-to-export ratios。Ratio denominator 为 connector→USA level，只有严格大于 0 时定义。China 与 East Asia pre/post 各 91 个 ratios 均有定义，公式与 missing-state 复算差额为 0。M3.3 继承字段逐 flow 回勾误差和 flag mismatch 均为 0。

#### 12.6.4 Exposure missing、overlap 和 high-exposure 定义

每个 eligible product 的 post tariffed status 是 2020-2024 mean，flag 规则为 mean > 0；当前没有 fractional post status。Product exposure 是 2020-2024 `tariff_exposure` mean。28 个 eligible products exposure missing，分布为 electronics 1、machinery 2、other manufacturing 25；其中 14 个同时 tariffed。这 28 个缺失保持 nullable missing，不能改成 exposure=0，也不进入 exposure-weighted denominator。

部门表同时报告：

- tariffed-product export value share；
- observed-exposure export value coverage；
- observed-exposure products 内的 export-value-weighted exposure；
- 正 connector-export product gains 中 exposure observed 的覆盖；
- observed-exposure gain 中 positive exposure 与 sector-positive-exposure p75 以上产品的份额。

Positive exposure 是 observed exposure > 0。Top-quartile 是每个 analysis sector 内 positive observed exposure 的 linear/type-7 p75，二者均保留；它们不能替代 tariffed status。七个 sector 的 tariffed/observed/missing/positive/top-quartile counts 与 config 逐一一致；跨 connector 不一致数为 0。所有 level shares 和 overlap levels 位于 [0,1]。

#### 12.6.5 HS6 产品共变和分母

Active-product 规则为 source pre + post + connector export pre + post > 0。普通 Pearson correlation 至少要求 20 个 active products；weighted Pearson 以 source input pre + connector export pre 为权重，至少要求 20 个正权重 products，零方差时 missing。China/East Asia 的普通和 weighted correlations 各 91 个全部定义，low-n 为 0；最小 active products 为 31/32，最小正权重 products 为 30/31，相关系数越界为 0。

分别报告 source-input 与 connector-export 同时正增长、China→USA decline 与 connector-export product gain、以及 decline + source gain + export gain triple condition。每个条件同时保留 eligible-product share、source-specific active-product share 和 positive-export-gain share。Value-share denominator 固定为逐产品 `max(connector_export_change,0)` 之和，不使用部门净 gain；91 个 denominator 均非零。独立逐 cell 复算所有 counts、shares、普通和 weighted correlations，最大误差为 0；share 越界数为 0。

#### 12.6.6 Validation、确定性、Stata 和解释边界

- validation：`data/validation/connector_trade_reorganization_indicators_validation.json/.md`，PASS/0 failures；
- 三张 natural key duplicate 均为 0；
- TWN rows 为 4,237/7/7，proxy false 均为 0；
- numeric infinities 均为 0；
- 56/92/49 个 Stata aliases 完整、唯一、不超过 32 字符，实际最长 13/14/13；
- candidate 先写入项目 F 盘 `tmp/m3_4_candidates/`；
- 第二次完整重建写入 `tmp/m3_4_determinism/`，三张 SHA256 与 candidates 逐一完全一致；
- 只有全部 validation PASS 后才替换 canonical outputs，两个临时目录均已清除。

首次候选构建没有替换 canonical outputs，因为 validation 将允许为负的 overlap change 错纳入 [0,1] level-share 检查，并误用部门净 positive gain 代替逐产品正 gain denominator。修复仅更正 validation 对象：范围检查限定为 level shares/overlap pre/post，分母检查改为 co-movement 表的逐产品正 gain 总和；三张候选数值与 hashes 未改变。这个事件说明必须区分 level share 与 share change，也必须区分 aggregate net change 与 sum of positive product changes。

M3.4 指标是 descriptive reorganization diagnostics，不是因果估计。M3.4 不产生 connector ranking、不筛掉 comparators、不把 co-movement 解释为已证实 rerouting、不加入 production-side evidence，也不构造 structural moments/counterfactual inputs。Stata `.dta` 仍留到 M7；届时分别执行 `isid conn_iso3 hs6` 和两张 `isid conn_iso3 ana_sector`，并验证 28 个 exposure missing 在 13 connectors 上形成 364 个 nullable product flags。

结论：M3.4 单模块完成，允许作为 M3.5 共同 connector/comparator 面板的输入。

### 12.7 M3.5 完整 connector/comparator 共同面板

#### 12.7.1 目的和为什么单独做共同面板

目的不是立即产生 connector ranking，而是先固定所有候选 connector 在同一分析 sector 上的共同观察集合，使后续 sensitivity 和 ranking 不能根据结果变量、ratio 是否定义或排名高低先删样本。若只把 MEX、VNM、CAN 或当前看起来表现最好的 observations 留下，后续比较会把样本选择误当成经济差异，也无法检查低增长、负增量和 undefined denominator 的情况。

共同面板只合并相同自然粒度的 M3.4 sector outputs。产品窗口表继续保持 `connector_iso3, analysis_hs6` 自然粒度，不并入 91 行 sector 表，避免将产品字段机械重复或制造 many-to-many expansion。

#### 12.7.2 冻结输入和身份

| Input | Rows × columns | Natural key | SHA256 |
|---|---:|---|---|
| `connector_trade_sector_reorganization_indicators.parquet` | 91 × 92 | connector_iso3, analysis_sector | `f13c5f8aa0c4402d0b467a06a6b99ba8ddc8389d47ede9ba8c8036275c1d74f2` |
| `connector_trade_sector_product_comovement.parquet` | 91 × 49 | connector_iso3, analysis_sector | `3095cd39a7355ce6968e0e5c29956841fd9e40bc72238d06aafe8d3ef0c3b0f1` |
| `configs/analysis_sample_v1.yaml` | YAML | frozen sample | `bd30ba2338897b857390972c5da7294e82de93664751fe22c1a8544a9fd7fee2` |
| `configs/country_groups.yaml` | YAML | country groups | `5ff425458023bb9540a4239e2d01973ef467309e0f8a8286661feb5c0a7f8db3` |
| `configs/connector_trade_reorganization_indicator_rules.yaml` | YAML | M3.4 rules | `0305b9a2a0904f9eac9953a89f977565a644fc25167e4be7b04dad9a44a7fe4d` |

M3.5 config 为 `configs/connector_trade_sector_common_panel_rules.yaml`，SHA256 为 `374a1a18c756f38054ae3ecf077f1e2f148c53da9a07cc5b1338c01d92b44d40`；builder 为 `code/data_processing/build_connector_trade_sector_common_panel.py`；construction version 为 `connector_trade_sector_common_panel_rules_v1`。

#### 12.7.3 Join、字段和版本处理

以 sector-reorganization 表为 master，按 `connector_iso3, analysis_sector` one-to-one outer validation merge product-comovement 表。两张输入 key duplicate 均为 0；join status 为 both 91、left-only 0、right-only 0。

两表共有 12 个同名字段。其中主键 2 个；9 个相同概念字段逐值核对，mismatch 全为 0；`schema_version` 是 source-specific metadata，预期不同，不能误判为内容冲突。输出把 sector schema 记录为 `m3_reorganization_sector_schema_version`，把 comovement schema 记录为 `m3_comovement_schema_version`；M3.4 config hash 改名为 `m3_reorganization_rules_config_sha256`，同时新增 M3.5 自身的 `rules_config_sha256`。37 个只存在于 comovement 表的字段原值加入，所有 92 个 sector 字段也逐字段回勾，missing mismatch 和 value mismatch 均为 0。

#### 12.7.4 完整样本和禁止筛选

样本按冻结配置保留：

- core connectors：VNM、MEX、CAN，3 个 connectors、21 行；
- Asian comparators：IND、IDN、MYS、PHL、THA、KOR、TWN，7 个 connectors、49 行；
- other candidates：POL、MAR、TUR，3 个 connectors、21 行。

每个 connector 恰有 autos、electrical equipment、electronics、machinery、medical devices、other manufacturing、textiles/apparel 7 个 sectors；每个 sector 恰有 13 个 connectors，总计 91 行。新增 group、connector-within-group 和 sector order，保证 Parquet 与未来 Stata 输出排序稳定。

91 行全部满足 `comparison_sample_included=true`、两张 source-row matched=true。`outcome_based_selection_applied`、`top_rank_filter_applied`、`complete_case_filter_applied`、`ranking_variables_constructed`、`production_variables_included` 和 `sensitivity_variables_constructed` 全部为 false。这些不是装饰字段，而是机器可检验的样本合同：M3.5 没有因为 replacement ratio missing、connector gain 为负、co-movement 较弱或未来排名较低而删除 observation。

#### 12.7.5 输出、missing preservation 和 validation

正式输出：

| Output | Rows × columns | Natural key | Schema version | SHA256 |
|---|---:|---|---|---|
| `connector_trade_sector_common_panel.parquet` | 91 × 152 | connector_iso3, analysis_sector | `connector_trade_sector_common_panel_v1` | `36c58c229f3f43e86f7ff7570fc6a1ffe08ccb8fd3259bb5853abece3171f682` |

M3.4 的设计状态未被 complete-case 清洗：26 个 replacement ratios defined、65 个 missing、22 个 positive-gain candidates；China/East Asia 普通和 weighted product correlations 四套字段均为 91/91 defined，low-n flags 均为 0；TWN 有 7 行且 proxy 全为 true；numeric infinities 为 0。

Validation 为 `data/validation/connector_trade_sector_common_panel_validation.json/.md`，PASS/0 failures。152 个 Stata aliases 完整、唯一、均符合 Stata 命名规则，最长 14 字符。候选先写入项目 F 盘 `tmp/m3_5_candidates/`；第二次完整构建写入 `tmp/m3_5_determinism/`，两个 Parquet SHA256 均为 `36c58c...1f682`；只有 PASS 后才替换 canonical output，两个目录随后清除。另以独立只读脚本重新检查 output hash、91 × 152 schema、key、13 × 7 网格、21/49/21 组别行数、selection flags、26/65 replacement 状态、correlation completeness、aliases 和 temp cleanup，结果 PASS。

首次候选构建没有替换 canonical output，因为冻结配置中的两个 input schema signatures 使用了不同于项目 builder 的序列化方式。文件 SHA256、rows、columns、keys、join、字段回勾、样本和确定性输出均已通过；只修正两个 expected schema-signature 值后重建 PASS。这个事件没有改变输入或构造公式，说明 schema hash 必须连同其 canonical serialization 方法一起冻结。

M3.5 共同面板不是 ranking output。它不能被描述为“最佳 connector 列表”，也不能把 M3.4 descriptive co-movement 解释为 causal rerouting。M3.6 sensitivity 已在下一节单独完成；M4-M5 production evidence、M6 ranking/moments 和 M7 Stata `.dta` 仍未执行。

结论：M3.5 单模块完成，允许作为 M3.6 sensitivity 的固定共同样本输入。

### 12.8 M3.6 alternative-window、source-bloc 与 exposure-definition sensitivity inputs

#### 12.8.1 目的和边界

M3.6 的目的不是宣布 connector ranking 稳健，而是把后续 M6 需要切换的三类定义做成可审计、可复算、自然粒度明确的输入：

1. 同一 trade flow 在 primary、exclude-2024 和 shock-only 三种时间口径下的 level/growth/stability；
2. China-only 与 extended East Asia 两种 source-bloc 定义下的 input growth、input-export ratios 和产品共变；
3. tariff overlap、continuous weighted exposure、positive-exposure gain share 和 top-quartile-exposure gain share 四种 exposure estimands。

本阶段没有定义 score、权重、rank、tie rule 或 winner cutoff；没有使用 production data；没有修改 M3.1-M3.5；没有导出 `.dta`。三张输出中 `sensitivity_variables_constructed=true`、`ranking_variables_constructed=false`。

#### 12.8.2 冻结输入

冻结 config 为 `configs/connector_trade_sector_sensitivity_rules.yaml`，SHA256：

`b628a76fc7a5615d5decf9a39810a476b653a81c2d74a68c2d5d35d45af3f11f`

| Input | Rows × columns / role | Natural key | SHA256 |
|---|---:|---|---|
| `connector_trade_sector_common_panel.parquet` | 91 × 152；source/exposure master 与共同样本 | connector_iso3, analysis_sector | `36c58c229f3f43e86f7ff7570fc6a1ffe08ccb8fd3259bb5853abece3171f682` |
| `connector_trade_sector_year.parquet` | 1,001 × 70；alternative-window annual source | connector_iso3, analysis_sector, year | `95e547267892c4bc883788542f0e59ba284441b42f4ce1d379aea71a2f978c8c` |
| `time_windows.yaml` | pre/shock/post source of truth | YAML | `d1daeed066db7cf734c15c804f31eaaf66a7c07b335f3c227a6c9effffd6ebb5` |
| `country_groups.yaml` | source-bloc members | YAML | `5ff425458023bb9540a4239e2d01973ef467309e0f8a8286661feb5c0a7f8db3` |

两个 Parquet 的 row/column count、Arrow schema signature、natural key、schema version 和 construction version 全部与冻结合同一致。两表共有同一组 91 个 connector-sector keys；annual input 每个 key 恰有 2014-2024 的 11 个 distinct years。`connector_group`、BACI code、proxy 和 value unit 在 annual/common 间 mismatch 均为 0。

#### 12.8.3 Time-window 表

输出 `connector_trade_sector_time_window_sensitivity.parquet` 为 1,092 × 56：

```text
91 connector-sector cells
× 4 flows
× 3 window specifications
= 1,092 rows
```

主键为 `connector_iso3, analysis_sector, flow_id, window_spec_id`，duplicate 0。窗口固定为：

- `primary_post`：2014-2017 annual mean 对 2020-2024 annual mean；
- `exclude_2024`：2014-2017 对 2020-2023；
- `shock_only`：2014-2017 对 2018-2019。

四条 flows 为 China→connector、extended-East-Asia→connector、connector→USA 和 China→USA。每条 observation 的 expected/observed year counts 都一致，1,092 个 `complete_window_pair` 全部为 true。Level change、DH 和 log 的公式与 M3.2 相同；coverage 从 annual eligible/excluded values 重算 ratio-of-sums，不平均年度 share。

`annual_dh_growth_sd` 取 comparison 窗口内相邻年份 DH growth 的 sample SD，`ddof=1`；`positive_growth_year_share` 取相邻年份 level change 为正的比例。Primary/exclude-2024 分别有 4/3 个 comparison transitions，SD 定义；shock-only 只有 1 个 transition，所以对应 364 行 sample SD 设计性 missing，不能填 0。所有 1,092 行 positive-growth-year share 有定义。

本表同时重复同一 cell-flow 的 primary values，并生成当前 specification 减 primary 的 level/DH/log difference 及 sign-agreement flags。它们是 definition sensitivity inputs，不是 rank changes。China→USA 在同一 sector/spec 跨 connector mismatch 为 0；`flow_is_common_benchmark` 和 non-additive flag 禁止跨 connector 加总。

#### 12.8.4 Source-bloc 表

输出 `connector_trade_sector_source_bloc_sensitivity.parquet` 为 182 × 64：

```text
91 connector-sector cells × 2 source definitions = 182 rows
```

主键 `connector_iso3, analysis_sector, source_bloc_id`，duplicate 0。China-only 为 CHN；extended East Asia 为 CHN/KOR/JPN/TWN。若 connector 本身是 KOR 或 TWN，则 source sum 排除该 connector origin；因此 7 sectors × 2 connectors = 14 行 `connector_self_trade_excluded=true`。这条规则与 M2/M3.4 一致，没有把 self-trade 当作 source input。

两种 definitions 映射到同一 generic schema，保留 pre/post/input gain、raw DH/log、small-base/primary-eligibility/abnormal flags、input-export ratio、active/weighted product counts、普通/weighted correlation、both-legs shares 和 triple-condition shares。Extended-East-Asia levels 在 pre/post 均不低于 China-only，nested-level violations 为 0。

差值和 direction flags 都相对 China-only 复算。由于 extended East Asia 包含 China，它不是独立 comparison group；difference 仅解释为额外 East Asian origins 在 self-trade rule 后的增量。不能把 East Asia 与 China 的数值差解释为两个独立样本的 treatment effect。

#### 12.8.5 Exposure-definition 表

输出 `connector_trade_sector_exposure_definition_sensitivity.parquet` 为 364 × 47：

```text
91 connector-sector cells × 4 exposure definitions = 364 rows
```

主键 `connector_iso3, analysis_sector, exposure_definition_id`，duplicate 0。四种 definitions 为：

- `tariff_overlap`：post connector export value 中 tariffed products 的 share；
- `exposure_weighted_rate`：observed-exposure products 内，以 connector export value 加权的连续 exposure；
- `positive_exposure_gain_share`：observed-exposure positive export gain 中 exposure > 0 产品的 share；
- `top_quartile_exposure_gain_share`：同一 gain denominator 中 sector positive-exposure p75 以上产品的 share。

前两种是 pre/post level estimands；后两种是 positive-gain estimands。Gain-based 的 pre/post/change 共 182 行按设计 missing，`pre_post_missing_by_design=true`；正式值写在 `exposure_measure_value`。每行都保留 numerator、denominator、coverage、threshold rule 和 measure basis。

四种 measures 不能因为都位于 `[0,1]` 就视为同一单位或直接互减。`cross_definition_numeric_difference_forbidden=true` 在 364 行全部成立。Underlying product policy 在 connectors 间重复，但 connector-specific export weights/gains 不同；本表的 measures 不可跨 connector 加总。

#### 12.8.6 验证结果

机器可读和合作者可读 validation 为：

- `data/validation/connector_trade_sector_sensitivity_validation.json`
- `data/validation/connector_trade_sector_sensitivity_validation.md`

Validation 状态 PASS，failures 为空。主要证据：

- 三张 output row/column/key/schema contracts 全部通过；numeric infinite count 为 0；
- time amount、DH、coverage 的独立复算最大差额为 0；primary 与 M3.5 level/growth 最大差额为 0；
- 三窗口的负 level-change counts 为 `3/5/6/26`、`3/5/6/26`、`13/12/13/26`，负值均保留；
- time zero endpoints 为 0，log growth 1,092/1,092 defined，annual DH SD 728 defined、364 shock-only missing；
- source negative input gains 为 China-only 3、extended East Asia 5；两口径在 input gain/DH/input-export-ratio change/product correlation 上方向一致数为 89/89/73/89；
- source preserved values、mechanical growth、China-only differences 和 direction flags 的最大差额为 0；
- exposure measures 364/364 defined；182 行支持 pre/post，182 行 gain-based pre/post missing；tariff-overlap/weighted-rate 负 change 为 47/32；
- exposure numerator/denominator 独立复算最大差额为 `2.22e-16`，小于 `1e-12`；
- 每个 connector 的七个 sectors 合计 28 个 exposure-missing products，13 个 connectors 全部一致，未填 0；
- TWN 在 time/source/exposure 表分别有 84/14/28 行，proxy flag mismatch 0；
- 56/64/47 个 aliases 完整唯一，实际最长 13/11/12，均低于 Stata 32 字符限制。

三张正式和第二次构建 SHA256 分别为：

| Output | SHA256 |
|---|---|
| time-window | `1594fadeb348f88e07b2ec8f43ca3708f49f9e06a0b78fafe24ffb6417635aad` |
| source-bloc | `67fbf760adb01a18d4e0e4f9ddd44eef9f3d2d2496a0a60d358cf8eab77e1eda` |
| exposure-definition | `96144e95dd525103b658ed7220a15d2f3c7c7acf79ea3f314314112971dc7cbd` |

三组 hash 均逐字一致。Candidate 使用 `tmp/m3_6_candidates/`，determinism 使用 `tmp/m3_6_determinism/`；两目录均由 builder 在成功后清除。正式输出和临时输出都在项目 F 盘，没有向 C 盘写大型数据。

#### 12.8.7 解释边界

M3.6 已验证的是“定义和计算接口可重复、状态保留、三类 alternative measures 可供后续使用”，不是“connector ranking 已经稳定”。Rank sensitivity 只有在 M6 固定 score、component transforms、weights、eligibility、missing rule 和 tie handling 后才能实际计算。Source-bloc comparison 是 nested descriptive comparison；exposure definitions 是不同 estimands；time-window sign agreement 不是因果识别。Production relocation、pure rerouting 和 welfare interpretation 仍需 M4-M6。

结论：M3.6 单模块完成，整个 M3 完成；随后执行的 M4.1 记录见下一节。

### 12.9 M4.1 ICIO production-side source/analysis long

#### 12.9.1 目的与严格范围

M4.1 只把已验证的 OECD ICIO accounting interface 转换为可审计的 production-side long format。它不合并 AMNE、BEA MNE、BEA FDI 或 Mexico FDI；不生成最终跨来源 `production_validation_long.parquet`；不计算 production growth、ranking、structural moments 或 welfare inputs。M4.1 的核心问题是：如何在保留全部 source cells 和 accounting exceptions 的同时，得到 country-analysis-sector-year 的可比生产指标。

正式 metric 固定为七项：`gross_output`、`value_added`、`exports`、`imports`、`intermediate_inputs`、`taxes_less_subsidies` 和 `accounting_residual`。全部单位为 `current_million_usd`，频率为 annual，`direct_or_allocated=direct`。不同 metric 不可相加。

#### 12.9.2 冻结输入和身份

| Input | Rows × columns | Natural key | SHA256 |
|---|---:|---|---|
| `data/interim/production/oecd_icio_output_va_fd.parquet` | 12,150 × 14 | year, country_iso3, sector_oecd | `4c3c5b1a11d344e7b13b727a7036230d053312c137871525cb1fb412a4679643` |
| `data/processed/concordances/source_sector_crosswalk.parquet` | 517 × 14 | source_name, source_sector_level, source_sector_code | `99ab34b27a5a37ec4db4cb2fd65d35c48732d92f5363a04e7565d5b852142fe9` |
| `data/processed/concordances/country_crosswalk.parquet` | 611 × 22 | source_name, source_country_id | `29b4b4b936d8c974c2b9f9d9eaa37b9c5d67e170e94c39ccdbd5088be3adc4c6` |

Config `configs/production_icio_rules.yaml` 的 SHA256 为 `271340a12200fc15a1694371aa46cdfd084ebc301846938ac98010e291a7a3a0`。Builder 同时冻结三个输入的 Arrow schema signatures、行列数、自然键、期望年份、geography/sector counts、metric rules、output schemas、Stata aliases、validation tolerance 和两个项目内临时目录。输入 hash、schema、key 或行列数任一不符即停止。

ICIO source interface 只有 2017、2018、2022，81 个 geography（80 个国家和一个 ROW aggregate）与 50 个 OECD sectors。Country crosswalk 的 81 个 ICIO codes 和 source-sector crosswalk 的 50 个 ICIO codes 均 many-to-one 全匹配，duplicate 为 0。13 个 connector/comparator countries 在 ICIO 中都是 direct country observations；TWN 不使用 BACI proxy。

#### 12.9.3 转换步骤

1. 将 ICIO `country_iso3` 暂存为 `source_country_id`、`sector_oecd` 暂存为 `model_sector`，避免在 crosswalk 前把 ROW 当普通 ISO3。
2. 用 `source_name=oecd_icio` 的 country crosswalk many-to-one 加入 canonical country、country/aggregate/residual/proxy 和 comparison-sample flags。
3. 用 `source_name=oecd_icio` 的 sector crosswalk many-to-one 加入 `analysis_sector`、mapping status/rule、first-round exclusion、weight 和 main-join eligibility。
4. 在 source-cell 层构造：

```text
accounting_residual
= gross_output
  - intermediate_inputs
  - taxes_less_subsidies
  - value_added
```

销售端 diagnostic 另行复算为 `gross_output_sales - intermediate_sales - final_demand`，只进入 validation，不作为第八个正式 metric。

5. 将每个 geography-sector-year source cell 展开为 7 个 metric rows，保留所有国家、ROW、eligible、first-round excluded 和 outside-manufacturing rows。这张表是正式 lineage/audit interface，不是可删除的临时中间表。
6. Analysis join eligibility 严格定义为 `country_is_country=true`、`sector_is_main_join_eligible=true`、`sector_mapping_weight=1` 且 `analysis_sector` 非 missing。只有满足全部条件的 source cells 按 `country_iso3, analysis_sector, year` 求和。
7. `other_manufacturing` 聚合 11 个 eligible OECD manufacturing sectors；electronics、electrical equipment、machinery、autos、textiles/apparel 各由一个 source sector 直接映射。ICIO 无法单列 medical devices，因此不生成 synthetic medical-devices rows。
8. Analysis long 再按 7 个 metric 展开，登记 source-sector count/codes/mapping rules、negative/zero flags、additivity boundary、source file、release/config/schema versions 和 43 个 Stata aliases。

#### 12.9.4 输出和自然粒度

| Output | Rows × columns | Natural key | SHA256 |
|---|---:|---|---|
| `production_icio_source_sector_long.parquet` | 85,050 × 54 | source_name, source_country_id, model_sector, year, metric_name | `266ff08c5bd26e00a08cb9f3654b7c83354d02da79cca036d65ccd68d0054110` |
| `production_validation_icio_long.parquet` | 10,080 × 43 | country_iso3, analysis_sector, year, source_name, metric_name | `e8bdc6070581f5a1697adba605ef8eac3e7c40a5946779a627ec08ea673315f0` |

Source long 是 `12,150 source cells × 7 metrics`。Analysis long 是 `80 countries × 6 sectors × 3 observed years × 7 metrics`。两张主键 duplicate 都为 0；每个 source cell 和每个 analysis country-sector-year cell 都恰有 7 个 metric rows。

#### 12.9.5 Universe reconciliation 和 accounting exceptions

12,150 个 source cells 被互斥、完备地分为：

| Partition | Source cells | 是否进入 analysis long |
|---|---:|---|
| ROW aggregate | 150 | 否；保留在 source audit long |
| actual-country main eligible | 3,840 | 是 |
| actual-country first-round excluded | 2,640 | 否；保留并对账 |
| actual-country outside manufacturing | 5,520 | 否；保留并对账 |

四组合计 12,150。每个 metric 都独立验证 `eligible total + excluded total = full source-universe total`，最大浮点差低于 `1e-6` million USD。Eligible source rows 聚合到 analysis long 后，每个 country-sector-year-metric 的最大误差为 0；总量差也全部低于同一 tolerance。

负值不是下载不完整，也不是需要补零的缺失：source universe 中有 8 个负 value-added、365 个负 taxes-less-subsidies、206 个负 production residual 和 1,634 个负 sales residual cells。Main eligible source cells 中前三类为 3、92、56；analysis-sector 聚合后为 0、30、22。聚合后 value-added 负值为 0 不代表原始负 cells 不存在，因此 source long 的 `observed_negative_flag` 必须保留。所有负值维持 signed value，不截断、不取绝对值、不改成 missing。

Source production residual 最大绝对值为 `82.0319999998901` million USD，sales residual 最大绝对值为 `238.60580000188202` million USD。Source/analysis accounting identity 的独立复算误差分别约 `4.66e-10` 和 `4.51e-10` million USD，低于 `1e-6` tolerance。

#### 12.9.6 Validation、确定性和失败门槛

机器报告为 `data/validation/production_icio_validation.json`，合作者报告为同名 `.md`，状态 PASS。Validation 同时检查：

- 三个输入的 SHA256、Arrow schema signature、行列数、自然键与 frozen config 一致；
- 81 个 country/geography codes 与 50 个 sector codes 全部匹配；16 个 eligible source sectors 的 weight 均为 1；
- 两张输出的行列数、schema、key、metric grid、年份和 medical-devices absence；
- 七个 source metrics 与 interim fields 或独立 accounting formula 逐 cell 一致，`source_file` mismatch 为 0；
- ROW/eligible/excluded/outside partition、负值/零值 flags 和全部 signed totals；
- source-to-analysis cell/totals reconciliation 和 analysis accounting identity；
- 13 个 comparison countries 对应 1,638 个 analysis-long rows，角色 flags 不重叠；
- source/analysis 的 54/43 个 Stata aliases 完整、唯一、合法、最长 12 字符；
- suppressed/confidential flags 全 false、ROW aggregate flags 完整、metrics 不可跨名相加；
- 所有 numeric values finite，没有 synthetic 2019 或 medical-devices rows。

正式候选先写入 `tmp/m4_1_candidates/`。相同冻结输入在 `tmp/m4_1_determinism/` 第二次完整构建；两张 candidate/second-build SHA256 分别逐字一致。只有所有检查 PASS 后才替换 canonical outputs；两个临时目录成功后均由 builder 清除。首次开发运行因 validation 对 pandas merge indicator 的零计数类别比较过严而被拒绝；修正为明确要求 `both=12,150`、`left_only=0`、`right_only=0` 后重跑，数据构造和两个 candidate hashes 未改变。

#### 12.9.7 解释边界和下一步

ICIO gross output/value added 是 country-sector aggregate production evidence，可用于检查 connector 部门生产规模、增加值和 IO accounting，但不能单独证明 firm entry、ownership-specific relocation 或因果 rerouting。Exports/imports 是 ICIO 同源 accounting measures，不替代 M3 的 BACI trade outcome。2019 及其他缺失 ICIO 年份不插值；medical devices 不从 C26 或 C31T33 拆分。M4.1 没有生成 `.dta`，正式 Stata export 仍在 M7。

结论：M4.1 单模块完成且其输出未被 M4.2/M4.3 改写。M4.2 AMNE 与 M4.3 BEA MNE 已作为独立模块完成；最终跨来源 production long 仍必须等 M4.4-M4.6 完成。

### 12.10 M4.2 AMNE parent-host 明细和 host-sector totals

#### 12.10.1 目标、范围和完成状态

M4.2 只处理 OECD Analytical AMNE 2026 release。它的目标是同时提供两层接口：一层保留 source `parent × host × sector × year` 的 bilateral ownership/activity lineage；另一层提供 actual host × common analysis sector × year 的 foreign-affiliate totals。M4.2 不构造 AMNE growth、MPE expansion、pre/post window、ranking、`hgamma`、structural moments、welfare inputs、BEA/FDI integration 或最终 `production_validation_long.parquet`。

本模块状态为 `VERIFIED`，validation 为 PASS。Canonical outputs 继续使用 Parquet；`.dta` 留到 M7。

#### 12.10.2 冻结输入与身份

| Input | Rows × columns | Natural key | SHA256 |
|---|---:|---|---|
| `oecd_amne_affiliate_activity.parquet` | 1,260,053 × 15 | year, host_country_iso3, parent_country_iso3, sector_oecd | `ae5f859573e95773274928d0f27a90fe974fca2bd95f22fa78a849d8a2d8f856` |
| `oecd_amne_mp_shares.parquet` | 4,250,880 × 19 | 同上 | `a7f312c5a7cf0e87a3ecb6552363dae2c0f2e296685000653087a7d86c524131` |
| `country_crosswalk.parquet` | 611 × 22；AMNE subset 81 | source_name, source_country_id | `29b4b4b936d8c974c2b9f9d9eaa37b9c5d67e170e94c39ccdbd5088be3adc4c6` |
| `source_sector_crosswalk.parquet` | 517 × 14；AMNE subset 39 | source_name, source_sector_level, source_sector_code | `99ab34b27a5a37ec4db4cb2fd65d35c48732d92f5363a04e7565d5b852142fe9` |

Source build summary hash 为 `f992635705498a2d48a5a6e36721c61c5349d9290ce4a0dc42102f1ca550e8c1`。Frozen config `configs/production_amne_rules.yaml` 的 SHA256 为 `a74bd728dc0b4236043a9c68035b28b12e6f02aa9d2a8aeeb8468901721c829d`。Config 同时冻结四个输入的 schema signatures、自然键、行列数、direct/allocated/derived/unavailable 规则、两张 output schemas、Stata aliases、expected counts、tolerances 和两个 F 盘临时目录。

`affiliate_activity` 是 positive-link interface：`affiliate_output` 严格大于 0。`mp_shares` 是完整 zero-inclusive universe：

```text
81 source hosts × 80 foreign parents × 41 source sectors × 16 years
= 4,250,880 rows
```

其中 2,990,827 行 affiliate output 为 0。MP-share 表的 positive-output subset 恰好有 1,260,053 个 keys，与 activity 表完全相同；对应数值最大差为 `1.46e-11` million USD，属于 allocation summation 浮点差。

#### 12.10.3 Country、ROW 和 sector mapping

AMNE country codes 共 81 个，country crosswalk 81/81 匹配：80 个实际国家和一个 `ROW` aggregate。Parent-host source detail 同时保留 ROW host 与 ROW parent，并使用 `source_host_country_id`、`source_parent_country_id` 作为自然键，避免把 aggregate 强行塞入 ISO3。Host-analysis long 只保留 80 个 actual hosts；但 ROW parent 代表未单列来源经济体，仍参与每个 actual host 的 foreign-parent totals。TWN 是 direct OECD observation，`proxy_flag=false`。

Positive activity 的 39 个 source sectors 全部匹配 canonical crosswalk，其中 15 个 eligible manufacturing codes 映射到 6 个 analysis sectors、4 个 first-round excluded、20 个 outside manufacturing。`other_manufacturing` 聚合 10 个 source sectors；electronics、electrical equipment、machinery、autos、textiles/apparel 各映射一个。Full MP-share universe 另有 `O84` 和 `T97T98` 两个全零 nonmanufacturing codes。为了不改变 M1 已冻结的 crosswalk hash，M4.2 config 将其显式登记为 `outside_manufacturing_auxiliary_zero_only`；它们不被当作 join failure，也不进入 analysis sums。AMNE taxonomy 不能单列 medical devices，因此不生成 synthetic rows。

#### 12.10.4 Parent-host source-detail 构造

Activity source row 先分别与 host/parent country crosswalk、source-sector crosswalk 做 many-to-one join。每个 positive link 展开为 6 个 metrics：

| Metric | 状态 | 处理 |
|---|---|---|
| affiliate_output | direct bilateral | 原值保留，可跨 parent/source sector 求和 |
| affiliate_value_added | allocated to parent | host-sector foreign total × parent output share |
| affiliate_exports | allocated to parent | host-sector foreign total × parent output share |
| affiliate_imports | allocated to parent | host-sector foreign total × parent output share |
| parent_affiliate_output_share | derived | direct bilateral output / bilateral parent-output sum |
| affiliate_employment | unavailable | value 保持 missing，禁止补 0 |

Parent share 的正确分母是同一 `host × source sector × year` 下所有 foreign-parent bilateral outputs 的和，不是 XVEM direct foreign-affiliate total。Row-level `allocation_method` 不能套用到全部 metrics；builder 按 metric 写 `direct_or_allocated`、`derivation_status`、formula、allocation weight 和 additivity flags。Parent long 只 materialize positive links，并显式写 `zero_affiliate_output_links_materialized_flag=false`；完整 zero links 不丢失，因为冻结 MP-share 输入仍用于 host grid 与 validation。

#### 12.10.5 Host-analysis-sector 构造

Host totals 从 full MP-share universe 开始。首先在 `host × source sector × year` 层确认 80 个 parents 的 repeated `gross_output`、`foreign_affiliate_output_total`、`foreign_affiliate_share` 和 source file 各自唯一；再求 bilateral output、allocated VA/exports/imports 的 parent sums。只有 actual host、main-join eligible sector、weight=1 的 source cells进入 analysis-sector aggregation。

Host long 保留 7 个 metrics：bilateral affiliate-output sum、direct XVEM foreign-affiliate output total、reconstructed foreign-affiliate VA/exports/imports totals、direct gross output、foreign-affiliate output share。最后一个 share 按 analysis-sector ratio of sums 重算：

```text
foreign_affiliate_output_share
= sum_eligible_source_sectors(foreign_affiliate_output_total)
  / sum_eligible_source_sectors(gross_output)
```

当 denominator 为 0 时 share 保持 missing。Source-sector share 不做简单平均。每个 metric row 同时保留 source-sector count/codes/rules、parent counts、positive-parent-link count、ROW-parent-included flag、source negative/zero/missing counts、bilateral-XVEM gap 和可加总限制。

#### 12.10.6 输出、主键和数值状态

| Output | Rows × columns | Natural key | SHA256 |
|---|---:|---|---|
| `production_amne_parent_host_sector_long.parquet` | 7,560,318 × 71 | source_name, source_host_country_id, source_parent_country_id, model_sector, year, metric_name | `6e3d0a77838b9c1d0cbae6445ee9b3f5637114747e51a148162c720d26605bcb` |
| `production_validation_amne_host_sector_long.parquet` | 53,760 × 56 | country_iso3, analysis_sector, year, source_name, metric_name | `b9219fbfe2852f5ca7088bcedf290526479147a57c3b63cc0a693194cc499179` |

Parent output 是 `1,260,053 positive links × 6 metrics`，主键 duplicate 0。它完整保留 166 个负 allocated VA observations；1,260,053 个 employment values 全部 missing 且 `metric_unavailable_flag=true`。Host output 是 `80 countries × 6 sectors × 16 years × 7 metrics`，主键 duplicate 0。它保留 113 个 bilateral/direct-foreign-output zero cells、27 个 gross-output zero cells、27 个 share missing 和 86 个真实 zero shares；没有 infinite values，也没有 medical-devices rows。

#### 12.10.7 Bilateral-XVEM reconciliation

Parent-output sum 与 XVEM foreign-affiliate output total 是两条不同 source interfaces，不能设错误的 equality gate。当前最大绝对差：

- source-sector host cell：`0.112743254114` million USD；
- analysis-sector host cell：`0.205832572254` million USD。

两者都保留：bilateral sum 用作 parent-share denominator 和 audit；direct XVEM total 用作正式 host foreign-activity level。差异不被填 0、不按比例缩放，也不把某一接口覆盖另一接口。

#### 12.10.8 Validation、确定性和开发期失败

机器报告为 `data/validation/production_amne_validation.json`，合作者报告为同名 `.md`。Validation 同时检查：

- 四个 frozen inputs 和 build summary 的 SHA256、schema、行列数、自然键；
- 两张 AMNE inputs 的 key 无缺失/重复、无 domestic diagonal、完整 80-parent grid；
- activity 与 MP positive subset 的 keys 和数值；
- 39 个 canonical sectors、两个 auxiliary zero-only sectors、81 个 country codes 的 join coverage；
- parent share 和 allocated VA/exports/imports 的独立公式复算；
- parent/host outputs 的 schema、行列数、keys、metric grids、zero/missing/negative states；
- ratio-of-sums share、ROW parent inclusion、ROW host exclusion、TWN direct status、medical-devices absence；
- 71/56 个 aliases 的完整性、唯一性、Stata 合法性和 32-character limit；
- candidate/second-build byte-level SHA256 equality 和临时目录清理。

正式候选先写入 `tmp/m4_2_candidates/`，第二次完整构建写入 `tmp/m4_2_determinism/`。两张 candidate/second-build hashes 逐字一致；两目录随后由 builder 清除。

开发期第一次运行已经构造候选，但 failure-report JSON 遇到 YAML date serialization，且异常路径中 Parquet handle 未先关闭；程序没有替换 canonical outputs。修正显式字符串化日期和关闭句柄后重跑，全部实质检查通过，只剩 reconciliation gap 快照因求和顺序相差约 `4e-12/7e-12` million USD。公式 tolerance 继续为 `1e-12`，但 gap 快照使用专门的 `1e-10` million USD tolerance；再次从冻结输入完整重建后 PASS。这个调整处理的是浮点快照，不改变任何数据值或经济公式。

#### 12.10.9 解释边界和下一步

AMNE direct affiliate output 与 ownership share 可用于 Scenario B incumbent MP-intensive evidence；allocated parent VA/trade 只能按有记录的 allocation estimate 解释。它不能单独证明 plant entry、firm relocation 或 causal rerouting。Employment 不可得的问题已由 M4.3 的 BEA MNE employment 接口部分补充，但来源覆盖和 ownership concept 不同，不能机械替换 AMNE。M4.2 单模块完成且输出未被 M4.3 改写。

### 12.11 M4.3 BEA MNE country-industry activity 标准化

#### 12.11.1 目标、范围和完成状态

M4.3 只标准化 BEA Activities of U.S. Multinational Enterprises 中 majority-owned foreign affiliates of U.S. MNEs 的 country/area × published industry × year activity。它提供 employment、sales、value added、capital expenditures、affiliate exports to U.S. 和 affiliate imports from U.S. 六项年度指标。Parent 固定为 USA，country 维度是 affiliate host。

本模块不下载更早年份，不处理 BEA direct-investment position/flows/income，不合并 Mexico，不构造 growth、pre/post window、ranking、structural moments、welfare inputs、`.dta` 或最终跨来源 `production_validation_long.parquet`。状态为 `VERIFIED`，机器 validation 为 PASS。

#### 12.11.2 冻结输入、raw manifest 和身份

| Input | Rows × columns / scope | Natural key | SHA256 |
|---|---:|---|---|
| `bea_us_mne_affiliate_country_industry.parquet` | 8,256 × 38；2017-2023 | year, affiliate_country, industry | `ab2e064459cc9dac8c13eebd7e399e91047133a93e8f35b9821520add7f219e8` |
| `country_crosswalk.parquet` | 611 × 22；BEA MNE subset 75 | source_name, source_country_id | `29b4b4b936d8c974c2b9f9d9eaa37b9c5d67e170e94c39ccdbd5088be3adc4c6` |
| `source_sector_crosswalk.parquet` | 517 × 14；BEA MNE subset 16 | source_name, source_sector_level, source_sector_code | `99ab34b27a5a37ec4db4cb2fd65d35c48732d92f5363a04e7565d5b852142fe9` |
| BEA source build summary | one JSON | n/a | `236b7afa5bd5065f7a6c614f9af33696f43cf8f8186ac50df61554082603b119` |
| raw manifest | 35 XLS entries | local_path | `0ad13fc2337a0f4ce74b5b10dab34666244624af5a429840e878c4e9854b4a59` |

Frozen config `configs/production_bea_mne_rules.yaml` 的 SHA256 为 `24db24e60bc70e7646773cf8cdebf80396c0c36c4e4439e9b388a89a4c74265b`。Config 冻结输入 hash/schema/key、六个 metric source fields、unit/direction/formula、suppression/small-value 规则、aggregate/proxy 规则、两张 output schema、expected exception counts、69/66 个 Stata aliases 和两个项目 F 盘临时目录。

Validation 重新读取 raw manifest 并逐一计算35个 XLS的实际文件大小与 SHA256；mismatch为0。Canonical output 中 metric-specific `source_file` 转为项目相对路径和正斜线，避免把本机 `F:/...` 前缀固化为跨机器接口；原始 interim input不被修改。

#### 12.11.3 Geography 标准化和实际 coverage

Input 有75个 source geography labels。Source 自带 `bea_area_type=aggregate` 标出1,792行，但不能只信任 source label：country crosswalk另外把 source 标为 `country_or_area` 的 `United Kingdom Islands, Caribbean` 112行强制识别为 aggregate。因此：

```text
8,256 source rows
= 1,904 final canonical aggregate-geography rows
+ 6,352 actual-country rows
```

Source-detail long 保留1,904行 aggregate base cells ×6 metrics供审计；analysis long中 aggregate geography为0。Actual rows对应57个 ISO3和397个实际 country-years。KOR 2017使用 `Korea, Republic of`、2018-2023使用 `South Korea`，两种source label在年份上不重叠，映射后 `country_iso3 × year × industry` duplicate为0。

Vietnam只在2019-2023出现，2017-2018不生成missing-grid或zero rows；Morocco在此BEA source完全不存在。项目13个 comparison countries中有12个可观察，共82个country-years。这些是source coverage状态，不是零affiliate activity。

#### 12.11.4 Industry mapping、strict main 和 autos proxy

16个published industries与canonical source-sector crosswalk 16/16匹配。Actual-country 6,352 rows按mapping status分解为：

| Mapping status | Rows |
|---|---:|
| mapped priority | 1,191 |
| mapped other manufacturing | 794 |
| Transportation-equipment ambiguous proxy | 397 |
| aggregate/residual industry | 1,191 |
| first-round excluded | 794 |
| outside manufacturing | 1,985 |

Strict main只允许weight=1的五个source industries：Computers and electronic products → electronics；Electrical equipment, appliances, and components → electrical equipment；Machinery → machinery；Chemicals与Food共同汇总为other manufacturing。因此1,985个main source rows聚合为1,588个main country-sector-year cells。

Transportation equipment混合motor vehicles、aerospace、rail、ship等活动，不能作one-to-one autos。为了让合作者能够直接进行明确标注的robustness，M4.3 analysis long另保留397个autos proxy cells，并强制：

```text
analysis_sector = autos
analysis_scope = proxy_robustness
proxy_flag = true
main_analysis_join_eligible = false
```

Main analysis必须筛选`main_analysis_join_eligible=true`。BEA published industry不能单独识别medical devices或textiles/apparel，不生成synthetic zero rows。

#### 12.11.5 Metric、方向和 source-cell 状态

| Metric | BEA table | Unit | Direction / interpretation |
|---|---|---|---|
| employment | II.G 1 | thousand employees | U.S.-parent-owned affiliate employment |
| sales | II.D 3 | current million USD | affiliate sales；不等于ICIO gross output |
| value_added | II.F 3 | current million USD | affiliate value added；负值允许 |
| capital_expenditures | II.C 4 | current million USD | affiliate PP&E expenditures |
| goods_exports_to_us | II.H 11 | current million USD | affiliate → USA |
| goods_imports_from_us | II.H 3 | current million USD | USA → affiliate |

`(D)`和employment size-range codes `A/F/G/H/I/J/K/L/M`保持numeric missing并标记suppressed。`(*)`按source builder保留为0.0并标记small value；它不是exact zero。Full source每项missing都能由suppression解释，unflagged missing为0：

| Metric | Suppressed/missing | Small-value | Reported zero | Negative |
|---|---:|---:|---:|---:|
| employment | 740 | 319 | 690 | 0 |
| sales | 1,344 | 89 | 325 | 0 |
| value added | 1,290 | 127 | 362 | 164 |
| capital expenditures | 1,494 | 745 | 1,011 | 0 |
| exports to U.S. | 1,996 | 691 | 3,523 | 0 |
| imports from U.S. | 2,055 | 610 | 2,767 | 0 |

#### 12.11.6 Suppression-safe analysis aggregation

对任一`country × analysis sector × year × metric`，builder先确认expected source-industry count。正式值严格定义为：

```text
value = sum(all required source-industry values)
        if every required component is disclosed
        otherwise missing

source_disclosed_value_sum
      = sum(available source-industry values, min_count=1)
```

第二个字段只用于diagnostic reconciliation。只要某个组成行业suppressed，不能把可见部分当作完整sector total。Analysis long同时记录expected/actual/disclosed industry counts、suppressed/small/missing/negative/zero/exact-zero component counts、partial-disclosure与all-components-suppressed flags。`other_manufacturing`需要Chemicals与Food两个components均披露；三个priority main sectors和autos proxy各只有一个source industry。

1,985个analysis cells中，strict missing分别为employment 181、sales 449、value added 392、capex 359、exports 595、imports 635。正式零与small-value状态分开：`reported_zero_flag`允许包含`(*)`，`exact_zero_flag`要求small-value component数为0。

#### 12.11.7 输出、主键和 hashes

| Output | Rows × columns | Natural key | SHA256 |
|---|---:|---|---|
| `production_bea_mne_source_industry_long.parquet` | 49,536 × 69 | source_name, source_country_id, model_sector, year, metric_name | `016c7b10891e3770c14eeb9cf0f489bd9d80281c91bd1e10e2a883f76205b514` |
| `production_validation_bea_mne_long.parquet` | 11,910 × 66 | country_iso3, analysis_sector, year, source_name, metric_name | `21d9998c77e9fa8b458af288a36746567d4ade49c3a50360a0f684b329691ade` |

Source long严格等于8,256 source keys ×6 metrics，保留全部aggregate、excluded、residual和proxy rows；analysis long严格等于1,985 cells ×6 metrics，其中9,528 rows是四个main sectors，2,382 rows是autos robustness proxy。两个自然键duplicate与missing均为0。

Value added负值分层为：full source 164、actual-country source 138、main-eligible source 32、strict main analysis 19、strict proxy analysis 18。负值没有截断或winsorize。2023 rows明确标为preliminary release。

#### 12.11.8 Validation、确定性和开发期事件

机器报告为`data/validation/production_bea_mne_validation.json`，合作者报告为同名`.md`。Final validation包含137项检查且failure为0，覆盖：

- input/build-summary/raw-manifest hashes、Parquet schemas、rows/columns和natural keys；
- 35个raw XLS的实际size/hash；
- country与industry many-to-one join、row preservation和canonical aggregate override；
- source-wide到69-column long的value/raw-code/suppression/small/source-file identity；
- source-to-analysis的strict value、disclosed sum与全部component counts独立重算；
- missing/suppression/small/zero/exact-zero/negative snapshots；
- trade directions、KOR label change、VNM/MAR coverage、TWN direct-country状态；
- main/proxy isolation、unsupported sectors absence、source-file portability；
- 69/66个aliases的完整、唯一、Stata合法和32-character门槛；
- candidate/second-build byte-level SHA256 equality与临时目录清理。

正式候选写入`tmp/m4_3_candidates/`，第二次完整构建写入`tmp/m4_3_determinism/`。两张candidate与second-build SHA256逐字一致，两个目录随后由builder精确清理。

开发期首次实现按group逐row构造analysis表，外层120秒执行限制终止了首次试跑；当时canonical output不存在，检查没有本轮Python进程仍在，task-owned candidate目录为空并被精确删除。随后改为按static group metadata和metric statistics向量化构造，不改变公式或冻结计数。第一次向量化candidate到validation时，所有实质数值检查通过，但analysis DataFrame误保留内部`resolved_analysis_sector`辅助列，形成67列而非66列；builder拒绝替换canonical并自动清理临时目录。删除内部列后重新完整构建两次，final validation PASS。两次事件都没有修改raw/interim/crosswalk或旧canonical outputs。

#### 12.11.9 使用边界和下一步

BEA MNE employment/capex可以补充AMNE employment unavailable的问题，sales/value added可用于美国MNE majority-owned affiliate activity validation；但它只代表U.S.-parent-owned affiliates，不是host economy全部foreign affiliates或national production。Sales不能当作ICIO gross output，affiliate trade不能与BACI/Census trade相加。Transportation proxy不能在主分析中当精确autos。

M4.3完成后仍没有BEA FDI stock/flow、Mexico FDI、跨来源production merge、production growth、ranking或structural moments。下一步只能在用户确认后进入M4.4 BEA direct investment标准化。

### 12.12 M4.4-M4.7 预留记录

后续 production long 必须逐源记录：BEA FDI direction/stock/flow、Mexico quarterly annualization 和 confidentiality。统一 long schema 不能让不同来源的 `output`、`sales`、`position`、`flow` 因同名而相加。M4.7 继续执行 ICIO 不插值规则。

### 12.13 M5 预留记录

每加入一个 production source，记录 left join 前后 rows、matched/unmatched keys、source totals、many-to-many expansion count、coverage flags 和可用年份。Integrated evidence table 只有在所有 source totals reconciliation 完成后才可打勾。

### 12.14 M6 预留记录

每个 ranking、rerouting indicator、production validation measure 和 structural moment 必须记录公式、unit、sample、winsorization/denominator rule、source、scenario A/B/C 归属，以及能否进入 model input。不得把 FDI 与 output 合成一个无单位指标而不披露标准化方式和权重。

### 12.15 M7 预留记录

最终 release 必须记录单一入口脚本、environment、input/output manifests、deterministic tests、Git commit、release label、Stata exports、variable dictionary、verification `.do` 和日志 success marker。本档案最终版的 Verification Status 只有在 full rebuild 成功、输出 comparison 通过后才能改为 `VERIFIED`。

## 13. 异常、失败和决策日志

| 日期 | 阶段 | 事件 | 判断和修复 | 影响 |
|---|---|---|---|---|
| 2026-07-18 | source build | List 1 PDF 将 `9033.00.90` 截短 | 根据同一官方 notice 的 description table 恢复 `90330090` 并验证 event key | 防止把整段 HS6 错扩展和 duplicate HTS10 |
| 2026-07-19 | M1 | multi-target HS correlations 没有可辩护数值权重 | 主 conversion 只用 official one-target weight 1；full correlation 仅 audit | 防止 many-to-many value inflation |
| 2026-07-19 | M1 | CEPII `271000` 合并五个 official HS2012 codes | sector 一致可映射；BEC uses 保持 ambiguity，不猜权重 | sector aggregation 可用，end-use split 不可用 |
| 2026-07-19 | M1 | Mexico SCIAN 3345 混合 measuring/control/navigation 和 medical electronics | 保留 ambiguous，mapping weight null | 不夸大 medical devices |
| 2026-07-19 | M2.1 | 356 个 BACI HS2017 weight codes 不在 policy panel | 显式 not listed、rate 0，保留 source-observed flag | complete legal universe 不丢失 |
| 2026-07-19 | M2.2 | KOR/TWN 在 East Asia source bloc 中会产生 self-trade | 按 canonical ISO3 排除 self-trade；TWN 同时保留 S19 proxy | source-to-connector leg 可解释 |
| 2026-07-19 | M2.6 | YAML 未加引号的 effective date 被 parser 读为 date object，首次运行失败 | 将 `2024-09-27` 明确引用为字符串后重跑；final validation PASS | 无残留输出错误；记录配置类型风险 |
| 2026-07-19 | audit | 旧说明写 Mexico detailed quarterly 到 2024Q4，但实际五张 detail Parquet 只到 Q2 | 以实际 Parquet 和 time validation 为准；修正文档为 national Q4 / detail Q2 | 2024 detail 不作 full-year comparison |
| 2026-07-28 | M3.1 | 开发构建将 sector eligible count 暂命名为 `included_product_count` | 在正式合同前改为 `sector_eligible_product_count`；重新构建、复算和确定性 hash 均 PASS | 最终 70-column schema 无含糊旧字段 |
| 2026-07-28 | M3.1 | 仅在文档登记 Stata aliases 无法形成机器门槛 | 将完整 70-field alias map 冻结进 config；validation 强制检查覆盖、唯一性和 32-character limit | M7 可按固定 alias export，但本阶段未生成 `.dta` |
| 2026-07-28 | M3.2 | long grain 与 post-pre growth 的自然 grain 不一致 | 采用 273-row long window + 91-row comparison 两表接口，避免同一 growth 在三个 window rows 重复 | long 用于窗口水平；comparison 用于一次性 post-pre 比较 |
| 2026-07-28 | M3.2 | comparison 开发构建出现 pandas fragmentation 性能警告 | 改为一次性 concat derived columns；重新构建无警告，两个 Parquet hash 未变化，validation PASS | 清除运行噪声；数值和 schema 不变 |
| 2026-07-28 | M3.3 | 首次 long candidate 的 M3.2 version 按原 input index 对齐，造成后 273 行 version missing | 拒绝完成状态；改为验证 source version 唯一后写入常量，并新增 version zero-missing/one-unique gate；重建 PASS | 数值与 flags 未受影响；最终 364 行 provenance 完整，候选错误未提交 |
| 2026-07-28 | M3.4 | 首次候选 validation 把允许为负的 overlap change 当作 [0,1] level share，并误用部门净 gain 检查产品正 gain denominator | 未替换 canonical outputs；范围 gate 限定为 level shares/overlap pre/post，denominator gate 改为逐产品正 export gain 总和；重建 PASS | 三张候选数值/hashes 未改变；修复 validation 定义而非数据 |
| 2026-07-28 | M3.5 | 首次冻结的两个 input schema signatures 使用了与项目 builder 不同的 serialization | validation 阻止替换 canonical output；用 builder 的 canonical JSON schema serialization 重算两个 expected signatures 后重建 PASS | 输入/数值/join/样本和构造公式未改变；记录 schema hash 必须同时冻结 serialization |
| 2026-07-29 | M3.6 | shock-only 只有一个年际转移；extended East Asia 包含 China；四种 exposure measures 不是同一 estimand | shock-only sample SD 设计性 missing；source comparison 标记 nested/self-trade；禁止 cross-exposure numeric difference 和 M3.6 rank | 避免把不可定义统计量填 0、把 nested bloc 当独立样本、或把不同 exposure 数值当可互换 ranking component |
| 2026-08-02 | M4.1 | 首次 validation 将 pandas merge indicator 中值为 0 的 `left_only/right_only` 类别也当成 mismatch | 保留候选失败状态；把门槛改为明确检查 `both=12,150`、`left_only=0`、`right_only=0` 后重跑 | 数据、schema 和两个 candidate hashes 未改变；最终 validation PASS，未用错误状态覆盖 canonical output |
| 2026-08-02 | M4.2 | 首次 failure-report 将 YAML date object 直接交给 JSON，异常路径中 Parquet handle 未先关闭 | 日期显式转字符串，所有 Parquet handles 在 replace/cleanup 前显式关闭；核实仅有本轮 candidate 文件后清理并重跑 | 未生成 canonical outputs；raw/interim/crosswalk 均未修改 |
| 2026-08-02 | M4.2 | Bilateral-XVEM gap 快照在不同 groupby 求和顺序下相差约 `4e-12/7e-12` million USD | 经济公式继续用 `1e-12`；只把 gap snapshot tolerance 设为 `1e-10` million USD，再从冻结输入完整重建 | 数据值、schema 和经济定义未改变；最终两张 deterministic hashes 一致、validation PASS |
| 2026-08-03 | M4.3 | 首次loop-based analysis构造超过外层120秒限制 | 确认无本轮Python进程、canonical不存在且task-owned candidate为空后精确清理；改为static metadata与metric group statistics向量化 | 只改变运行效率，不改变公式、冻结计数或输入；未触碰raw/interim/crosswalk |
| 2026-08-03 | M4.3 | 首次向量化candidate保留内部`resolved_analysis_sector`辅助列，形成67列而非冻结66列 | Validation拒绝canonical replace并自动清理；删除内部列后完整构建两次 | 所有实质数值检查原已通过；final 11,910 × 66、deterministic hashes一致、validation PASS |

## 14. 当前未解决限制和是否需要补数据

| 限制 | 是否影响已完成 M3.1-M4.3 / 下一步 M4.4 | 可能的后续动作 |
|---|---|---|
| BACI quantity 缺失 | 不影响 value-based M3.1-M3.6 或 M4.1-M4.3 production levels | 保持 value-based；除非研究明确需要 physical quantity 才找替代 |
| Census quantity unavailable | 不影响 | 禁止 quantity analysis；不需为 M3.2 补下载 |
| Census 只有 15 origins | 否 | 只作 configured-origin timing validation；all-origin denominator 用 BACI |
| Section 301 historical exclusions 未应用 | 否，但限制 causal interpretation | 若需要 realized-duty measure，单独开 policy extension |
| 2024 modern HTS 未并入历史面板 | 否 | 需要 modern-HTS concordance 后再单独扩展 |
| AMNE employment 全缺失 | M4.2 已显式保留 unavailable；M4.3 提供 U.S.-parent-owned affiliate employment，但两者scope不同 | 如仍不足再补国家统计；不得把BEA employment机械插补进AMNE |
| OECD/BEA medical devices 不可单列 | M4.1-M4.3 已保持 unsupported | Mexico/产品层可单列，跨源比较披露缺口；不得在 ICIO/AMNE/BEA 中补零行 |
| BEA Transportation equipment 比 autos 宽 | M4.3 已隔离为 `proxy_robustness`，不影响strict main | 只作显式proxy sensitivity，不作one-to-one或main join |
| Mexico detail 2024 仅 H1 | 否 | 2024 H1-to-H1 或季度分析；不作 annual total |
| Mexico confidential cells | 否 | 不补 0；报告 disclosed composition 和 national total 分开 |
| INEGI/Vietnam GSO/Statistics Canada 未下载 | 否 | M4-M6 若出现关键 output/employment gap，再定向补充 |

结论：这些主要是定义、覆盖和可比性限制，不是“核心下载只完成一半”。M3.1-M4.3 已在现有数据上完成；进入 M4.4 不需要先泛化下载，但以后必须根据具体 production-side empirical gap 决定是否补国家统计数据。

## 15. Stata 合作者交付合同

Parquet 是 lossless canonical processed format。最终交给合作者的 `.dta` 是衍生交付，不取代 Parquet。M7 必须满足：

- variable names 不超过 32 characters；
- ISO3 使用 `str3`，HS6 使用保留 leading zeros 的 `str6`；
- 日期、字符串 Unicode、numeric storage type、variable labels 和 value labels 明确；
- 每张表在 Stata 中执行 `isid`；
- row counts、key counts、missing/suppression/confidentiality counts 与 Parquet 对齐；
- float/double 精度差异有 tolerance，货币总量有 reconciliation；
- repeated/non-additive fields 有变量标签和 README 警告；
- M3.1 已冻结 70 个无重复 alias，最长 14 字符；M7 实际导出时仍必须再次对 `.dta` 验证，不能把本次 alias 检查当作 export 已完成；
- M3.2 已冻结 long 79 个和 comparison 142 个无重复 alias，最长均为 13 字符；M7 必须分别导出并验证两个 key，不能把 alias 检查当作 `.dta` 已生成；
- M3.3 已冻结 flow diagnostics 64 个无重复 alias，最长 11 字符；M7 必须验证 `isid conn_iso3 ana_sector flow_id`，并核实 91 个 relative-cutoff missing 和 91 个 robust-z missing 是 China→USA 的设计状态；
- M3.4 三张表已冻结 56/92/49 个无重复 aliases，最长 13/14/13；M7 必须分别验证 `isid conn_iso3 hs6`、`isid conn_iso3 ana_sector`、`isid conn_iso3 ana_sector`，并核实 364 个 nullable exposure flags 来自 28 个产品在 13 connectors 上的设计性 missing；
- M3.5 共同面板已冻结 152 个无重复 aliases，最长 14 字符；M7 必须验证 `isid conn_iso3 ana_sector`、91 行、13 × 7 完整网格、21/49/21 分组和全部 no-selection flags，不能把 aliases 已验证误写为 `.dta` 已导出；
- M3.6 三张 sensitivity 表已冻结 56/64/47 个无重复 aliases，最长 13/11/12；M7 必须分别验证 `isid conn_iso3 ana_sector flow_id win_spec`、`isid conn_iso3 ana_sector src_bloc`、`isid conn_iso3 ana_sector expo_def`，并保留 shock-only SD 和 gain-based pre/post 的设计性 missing；不能把 sensitivity inputs 误写为 ranking；
- M4.1 source/analysis long 已冻结 54/43 个无重复 aliases，最长均为 12；M7 必须分别验证 `isid source src_ctry model_sec year metric` 和 `isid country_iso3 ana_sector year source metric`，保留 ROW aggregate 与 negative accounting flags，不能把不同 metric reshape 后直接求和；
- M4.2 parent/host long 已冻结 71/56 个无重复 aliases，最长均为 12；M7 必须分别验证 `isid source src_host src_parent model_sec year metric` 和 `isid country_iso3 ana_sector year source metric`，保留 ROW parent/host、allocated/unavailable、zero-link 和 reconciliation flags，不能把 parent share 或 bilateral/XVEM levels 当作可重复相加字段；
- M4.3 source/analysis long 已冻结 69/66 个无重复 aliases，最长分别为 12/12；M7 必须分别验证 `isid source src_ctry model_sec year metric` 和 `isid country_iso3 ana_sector year source metric`，保留suppression/small/exact-zero、strict/disclosed与main/proxy flags；主分析必须筛选`main_joinok==1`；
- `STATATMP` 指向项目 F 盘目录；
- 提供 batch `.do`：逐表 `use`、`describe`、`isid`、关键 `assert`、`summarize`，并在 log 写明确 success marker；
- 提供推荐 merge 顺序，禁止合作者直接把 product-level trade 与 country-sector production 做 many-to-many merge。

## 16. 合作者严格复核清单

- [ ] 核对本档案版本、branch、commit 和 M0 manifest 生成时间。
- [ ] 对八个 frozen inputs 重新计算 SHA256，与第 4.3 节比较。
- [ ] 检查每个 validation JSON 的 status、failure count 和 output hash。
- [ ] 抽查 Parquet schema 和 natural key；确认 duplicate 0。
- [ ] 抽查 aggregate/residual/proxy flags，不让它们进入普通 country sums。
- [ ] 抽查 BEA suppression 和 Mexico confidential cells 仍为 missing。
- [ ] 抽查 negative accounting/FDI values 未被截断。
- [ ] 重算 M2.1 treatment numerator、M2.2 trade-leg totals、M2.3 merge totals。
- [ ] 确认 Census annual 858,330 是 15-origin complete grid，不是 all-origin total。
- [ ] 确认 2024 review 表没有 `analysis_hs6`。
- [ ] 对 M3.1 两个输入重算 SHA256，确认分别为 `01fbbe...fdb` 与 `201c1d...c09`。
- [ ] 对 M3.1 输出执行 `isid connector_iso3 analysis_sector year` 等价检查，确认 1,001 行、duplicate 0 和 7 个 sector eligible counts。
- [ ] 独立重算四条流 eligible/excluded/full-universe reconciliation 与九个 policy ratios，确认金额 gap ≤ USD 0.01、比例 gap ≤ `1e-12`。
- [ ] 确认 17 个 zero-denominator 与 11 个 no-HS2017-mapping eligible products 通过 count/share 字段显式保留。
- [ ] 确认 China→USA、policy 和 coverage repeated flags 被遵守，TWN 77 行全部保留 proxy flag。
- [ ] 确认 70 个 Stata aliases 完整、唯一且不超过 32 字符；不要误认为 `.dta` 已导出。
- [ ] 对 M3.2 两个冻结输入重算 SHA256，确认 M3.1 output 为 `95e547...c8c`、time windows 为 `d1daee...bb5`。
- [ ] 对 M3.2 long/comparison 执行两个 natural-key 等价检查，确认 273 × 79、91 × 142 和 duplicate 0。
- [ ] 确认所有 connector-sector 的 pre/shock/post distinct years 严格为 4/2/5，没有 partial-window mean。
- [ ] 独立复算四条流 `mean×years`、ratio-of-sums coverage、policy rates/shares、change、DH 和 log，确认金额 gap ≤ USD 0.01、比例 gap ≤ `1e-12`。
- [ ] 确认 17/11 denominator 异常在三个窗口中保留，负变化 3/5/6/26 未截断，policy growth fields 为 0。
- [ ] 确认 TWN long/comparison rows 为 21/7、所有 required repeated/non-additive flags 为 true。
- [ ] 确认 long 79 个、comparison 142 个 Stata aliases 完整、唯一且不超过 32 字符；不要误认为两个 `.dta` 已导出。
- [ ] 确认 M3.3 每个 connector-sector 恰好 4 个 flows，364 行主键唯一，raw level/change/growth 与 M3.2 完全一致。
- [ ] 独立复算 USD 25 million absolute、nearest-rank p10 relative、robust-z/MAD、`|DH|>=1.5` 和 flow-level p5/p95 winsorized alternatives。
- [ ] 确认 China→USA 的 91 个 relative-cutoff missing 与 91 个 robust-z missing 有对应 not-applicable/MAD-zero flags，不能填 0。
- [ ] 确认 64 个 M3.3 Stata aliases 完整唯一，TWN 28 行 proxy 完整，winsorized/abnormal flags 不自动覆盖或删除 raw observations。
- [ ] 对 M3.4 四张 Parquet inputs 和 `time_windows.yaml` 重算 SHA256/schema/key，确认均与冻结 config 一致。
- [ ] 对 M3.4 三张输出执行 natural-key 等价检查，确认 55,081 × 56、91 × 92、91 × 49 和 duplicate 0。
- [ ] 独立复算 product 4/5-year means、四条 changes、产品到部门金额回勾、USD 25 million replacement、signed ratio 和两套 source-input/export ratios。
- [ ] 确认 28 个 exposure missing、其中 14 个 tariffed 未被填 0；复算 tariff overlap、observed-value coverage、positive/p75 exposure gain shares。
- [ ] 独立复算 HS6 active counts、Pearson/weighted correlations、eligible/active/positive-gain shares，确认使用逐产品正 gain 而不是部门净 change。
- [ ] 确认 56/92/49 个 M3.4 Stata aliases 完整唯一，TWN 4,237/7/7 行 proxy 完整，China→USA/policy repeated fields 不跨 connector 加总。
- [ ] 对 M3.5 两张 Parquet inputs、analysis sample、country groups 和 M3.4 config 重算 SHA256/schema/key，确认与冻结 config 一致。
- [ ] 对 M3.5 共同面板执行 `isid connector_iso3 analysis_sector` 等价检查，确认 91 × 152、13 × 7 完整网格和 21/49/21 分组。
- [ ] 逐字段确认 M3.4 sector 表与 37 个 unique comovement fields 原值保留；共同内容字段 mismatch 为 0，两个 source-specific schema versions 未错误合并。
- [ ] 确认 91 行均 included/matched，outcome/top-rank/complete-case/ranking/production/M3.6 sensitivity flags 全部 false；26/65 replacement defined/missing、22 candidates、四套 correlations 和 TWN proxy 状态未改变。
- [ ] 确认 152 个 M3.5 Stata aliases 完整唯一、不超过 32 字符；不要误认为共同面板已排名或 `.dta` 已导出。
- [ ] 对 M3.6 common/annual Parquet、`time_windows.yaml` 和 `country_groups.yaml` 重算 SHA256/schema/key，确认与 sensitivity config 一致，且 annual 每个 connector-sector 恰有 2014-2024 的 11 年。
- [ ] 对三张 M3.6 输出执行 natural-key 等价检查，确认 1,092 × 56、182 × 64、364 × 47、13 × 7 完整样本和 duplicate 0。
- [ ] 独立复算 primary/exclude-2024/shock-only 的 annual means、ratio-of-sums coverage、level/DH/log、annual DH SD、positive-year share 和 primary differences；确认 shock-only 364 个 SD 是设计性 missing。
- [ ] 确认 China-only/extended-East-Asia source definitions 的 self-trade rule、nested interpretation、3/5 negative gains、14 self-excluded rows 和 89/89/73/89 direction agreement counts。
- [ ] 对四种 exposure definitions 按 numerator/denominator 复算；确认 gain-based pre/post missing、每个 connector 合计 28 个 exposure-missing products、47/32 negative changes 和 cross-definition difference forbidden flag。
- [ ] 确认 56/64/47 个 M3.6 Stata aliases 完整唯一，TWN 84/14/28 行 proxy 完整，所有 sensitivity flags true、ranking flags false；不要误认为 rank sensitivity 已计算或 `.dta` 已导出。
- [ ] 对 M4.1 三个 frozen inputs 重算 SHA256/schema/key；确认 ICIO 为 12,150 × 14、81 geography、50 sectors、2017/2018/2022。
- [ ] 对 M4.1 两张输出执行 `isid` 等价检查，确认 85,050 × 54 与 10,080 × 43、duplicate 0、每个 source/analysis cell 恰有 7 metrics。
- [ ] 复算 M4.1 accounting residual、ROW/eligible/first-round/outside partition、8/365/206 个 source negative cells 和 source-to-analysis reconciliation；确认没有 synthetic 2019 或 medical-devices rows。
- [ ] 确认 M4.1 54/43 个 Stata aliases 完整唯一，ROW aggregate 只在 source long，analysis long 的 suppression/confidential/proxy flags 全 false；不要误认为跨来源 production merge 或 `.dta` 已完成。
- [ ] 对 M4.2 两张 AMNE inputs 和两个 crosswalk 重算 SHA256/schema/key；确认 activity 为 1,260,053 positive links，MP share 为 4,250,880 行完整 `81×80×41×16` universe。
- [ ] 对 M4.2 parent/host outputs 执行 `isid` 等价检查，确认 7,560,318 × 71 与 53,760 × 56、duplicate 0、每个 positive source link 恰有 6 metrics、host grid 为 80 × 6 × 16 × 7。
- [ ] 独立复算 MP positive subset、parent share denominator、allocated VA/exports/imports、ratio-of-sums host share；确认 166 个负 parent VA 和 1,260,053 个 missing employment values 未被清零。
- [ ] 确认 ROW parent 进入 host totals、ROW host 不进入 actual-country grid，`O84/T97T98` 只作为全零 auxiliary exclusions，27 个 zero-gross-output shares 保持 missing，TWN 不标 proxy，medical devices 不伪造。
- [ ] 确认 bilateral parent sum 与 XVEM direct total 分开保留、gap 不被强制为 0；71/56 个 M4.2 Stata aliases 完整唯一且不超过 32 字符，不要误认为 growth、ranking、跨来源 production merge 或 `.dta` 已完成。
- [ ] 对 M4.3 BEA activity、country/sector crosswalk、build summary和raw manifest重算SHA256/schema/key；确认35个raw XLS size/hash全部匹配。
- [ ] 对 M4.3 两张outputs执行`isid`等价检查，确认49,536 × 69与11,910 × 66、duplicate 0、source每个key恰有6 metrics。
- [ ] 确认1,792 source aggregates加112 canonical override等于1,904 final aggregates；analysis只含57 actual countries、397 observed country-years，VNM 2017-2018与MAR没有伪造零行。
- [ ] 独立复算strict value、`source_disclosed_value_sum`和component counts；确认suppressed保持missing、`(*)`与exact zero分开、164/138/32/19/18层级负VA未截断。
- [ ] 确认9,528 main rows与2,382 autos proxy rows隔离，proxy全部`main_joinok=0`；69/66 aliases完整唯一，不要误认为BEA FDI、growth、cross-source merge或`.dta`已完成。
- [ ] 确认 PDF build summary 的 Markdown SHA256 与当前文档一致。
- [ ] M3-M7 每完成一项后复核本档案已同步更新。

## 17. 证据索引

### 17.1 核心说明和配置

- `data/data_merge_checklist.md`
- `code/data_processing/README.md`
- `docs/variable_construction_catalog.md`
- `output/pdf/variable_construction_catalog.pdf`
- `output/pdf/variable_construction_catalog_build_summary.json`
- `configs/analysis_sample_v1.yaml`
- `configs/country_concordance_overrides.yaml`
- `configs/time_aggregation_rules.yaml`
- `configs/hs_revision_rules.yaml`
- `configs/product_sector_rules.yaml`
- `configs/source_sector_rules.yaml`
- `configs/product_treatment_rules.yaml`
- `configs/connector_trade_rules.yaml`
- `configs/trade_treatment_merge_rules.yaml`
- `configs/census_harmonization_rules.yaml`
- `configs/section301_2024_review_rules.yaml`
- `configs/connector_trade_sector_rules.yaml`
- `configs/connector_trade_sector_window_rules.yaml`
- `configs/connector_trade_sector_growth_diagnostic_rules.yaml`
- `configs/connector_trade_reorganization_indicator_rules.yaml`
- `configs/connector_trade_sector_common_panel_rules.yaml`
- `configs/connector_trade_sector_sensitivity_rules.yaml`
- `configs/production_icio_rules.yaml`
- `configs/production_amne_rules.yaml`
- `configs/production_bea_mne_rules.yaml`

### 17.2 M0-M4.3 validation

- `data/validation/data_merge_input_manifest.json/.md`
- `data/validation/data_merge_input_quality_audit.json/.md`
- `data/validation/analysis_sample_v1_validation.json/.md`
- `data/validation/country_crosswalk_validation.json/.md`
- `data/validation/time_aggregation_rules_validation.json/.md`
- `data/validation/hs_revision_bridge_validation.json/.md`
- `data/validation/product_sector_crosswalk_validation.json/.md`
- `data/validation/source_sector_crosswalk_validation.json/.md`
- `data/validation/concordance_coverage.json/.md`
- `data/validation/product_treatment_panel_validation.json/.md`
- `data/validation/connector_trade_panel_validation.json/.md`
- `data/validation/trade_treatment_merge_validation.json/.md`
- `data/validation/census_harmonized_panels_validation.json/.md`
- `data/validation/section301_2024_review_extension_validation.json/.md`
- `data/validation/connector_trade_sector_panel_validation.json/.md`
- `data/validation/connector_trade_sector_window_validation.json/.md`
- `data/validation/connector_trade_sector_growth_diagnostics_validation.json/.md`
- `data/validation/connector_trade_reorganization_indicators_validation.json/.md`
- `data/validation/connector_trade_sector_common_panel_validation.json/.md`
- `data/validation/connector_trade_sector_sensitivity_validation.json/.md`
- `data/validation/production_icio_validation.json/.md`
- `data/validation/production_amne_validation.json/.md`
- `data/validation/production_bea_mne_validation.json/.md`

### 17.3 source-specific provenance

- `docs/data_source_log.md`
- `data/README.md`
- `data/section301_usage_note.md`
- `data/mexico_fdi_usage_note.md`
- `data/interim/**/**_build_summary.json`

## 18. 版本变更记录

| Version | Date | Completed through | Change |
|---|---|---|---|
| v0.1.0 | 2026-07-27 | M0-M2 | 建立首次完整内部审计档案；汇总 source-specific 处理、M0-M2 规则、输出 hashes、限制、复核清单和 M3-M7 更新协议；纠正 Mexico national Q4 / detail Q2 口径。 |
| v0.1.1 | 2026-07-27 | M0-M2 | 将变量构造目录登记为配套正式合同；要求 M3-M7 同步更新两份 Markdown、两份 PDF 和对应 build summary。 |
| v0.2.0 | 2026-07-28 | M0-M3.1 | 登记 M3.1 冻结输入、canonical crosswalk join、eligibility、四条流和 policy 公式、1,001 × 70 输出、flow reconciliation、17/11 denominator 异常、TWN/repeated flags、Stata aliases、确定性 hash 和开发期字段重命名。 |
| v0.3.0 | 2026-07-28 | M0-M3.2 | 登记 M3.2 冻结 M3.1/time-window 输入、两表 grain、4/2/5 年完整窗口、annual-mean/ratio-of-sums/policy/growth 公式、273 × 79 与 91 × 142 输出、17/11 异常、负变化、TWN/repeated flags、79/142 aliases、候选输出规则和两个确定性 hash。 |
| v0.4.0 | 2026-07-28 | M0-M3.3 | 登记 M3.3 冻结 M3.2 comparison 输入、364 × 64 flow-level diagnostics、USD 25 million/nearest-rank p10 small-base、robust-z/MAD 与 mechanical extreme、p5/p95 winsorized sensitivity、raw preservation、TWN/repeated flags、64 aliases、确定性 hash 和 version-field 修复。 |
| v0.5.0 | 2026-07-28 | M0-M3.4 | 登记 M3.4 四张冻结输入、canonical HS6-sector join、55,081 × 56 产品窗口、91 × 92 部门重组指标和 91 × 49 产品共变三表输出、USD 25 million replacement denominator、signed gain、China/East Asia ratios、28 个 exposure missing、positive/p75 overlap、产品正增量分母、Pearson/weighted correlations、56/92/49 aliases、三个确定性 hashes 和首次 validation-definition 修复。 |
| v0.6.0 | 2026-07-28 | M0-M3.5 | 登记 M3.5 两张冻结 M3.4 sector inputs、one-to-one full match、91 × 152 共同面板、13 × 7 完整网格、21/49/21 分组、角色/排序/source-match/no-selection flags、26/65 replacement 状态、152 aliases、确定性 hash、独立复核和首次 schema-signature serialization 修复。 |
| v0.7.0 | 2026-07-29 | M0-M3.6 | 登记 M3.6 M3.5-common/M3.1-annual/time/country 冻结输入、1,092 × 56 time-window、182 × 64 source-bloc、364 × 47 exposure-definition 三表输出、primary/exclude-2024/shock-only、nested East Asia/self-trade rule、四种非等价 exposure estimands、设计性 missing、56/64/47 aliases、独立复算和三个确定性 hashes；明确不构造 ranking。 |
| v0.8.0 | 2026-08-02 | M0-M4.1 | 登记 M4.1 三个冻结输入、81 geography/50 sector source universe、85,050 × 54 source-sector audit long、10,080 × 43 analysis-sector long、7 个 production/accounting metrics、ROW/eligible/excluded partition、source/aggregate negative preservation、54/43 aliases、独立复算和两个确定性 hashes；明确不插值 2019、不伪造 medical devices、不提前生成跨来源 production 文件。 |
| v0.9.0 | 2026-08-02 | M0-M4.2 | 登记 M4.2 activity/MP-share/country/sector 冻结输入、positive/full-zero universes、7,560,318 × 71 parent-host source-detail long、53,760 × 56 host-analysis-sector long、direct/allocated/derived/unavailable 规则、ROW parent/host 边界、166 个负 allocated VA、employment unavailable、ratio-of-sums share、bilateral-XVEM reconciliation、71/56 aliases、独立复算和两个确定性 hashes；明确不构造 growth、ranking、hgamma 或跨来源 production 文件。 |
| v1.0.0 | 2026-08-03 | M0-M4.3 | 登记 M4.3 activity/country/sector/build-summary/raw-manifest冻结身份、49,536 × 69 source-industry audit long、11,910 × 66 analysis long、六项BEA affiliate metrics、1,904 aggregate geography过滤、strict/disclosed双值接口、suppression/small/exact-zero规则、164个source负VA、四个main sectors与autos proxy隔离、VNM/MAR coverage、69/66 aliases、137项validation、两个确定性hashes和两次开发期拒绝事件。 |

下一次更新触发点：M4.4 BEA direct-investment country-industry-year standardization、direction/stock/flow/income、aggregate geography、suppression/signed states、outputs和validation全部完成时，同步更新本档案与变量目录并重建两份PDF，再单独勾选M4.4。
