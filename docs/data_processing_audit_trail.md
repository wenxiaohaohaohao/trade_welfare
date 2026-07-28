# Connector Economies 项目数据整理与合并审计档案

## Material Passport

- Origin Skill: `academic-research-suite/experiment-agent`
- Origin Mode: `validate`
- Origin Date: `2026-07-27`
- Verification Status: `ANALYZED`
- Version Label: `data_processing_audit_v0.2.0`
- Working Branch: `data-processing-variables`
- Frozen Upstream Commit Recorded by M0: `2df0a0628343c9abca6b3e26d893db351ec22b94`
- M0-M2 Evidence Snapshot Date: `2026-07-19`
- Current Completed Processing Stage: `M0-M3.1`
- Next Stage: `M3.2`，尚未开始
- Audience: 项目合作者和内部复核人员
- Publication Status: 内部严格审查材料，不是投稿附件

## 0. 文档目的、范围和使用方式

这是一份持续维护的内部数据审计档案。它不以压缩叙述或展示研究结果为目标，而是回答下列问题：每张数据表从哪里来、经过了什么转换、为什么采用该规则、主键和粒度是什么、哪些值可以加总、哪些值不能加总、哪些异常被保留、每一步如何验证、当前还有哪些限制，以及合作者如何从现有文件复核全过程。

本版记录两层流程：

1. `source -> raw -> interim`：主要公开数据的下载、归档、单库清洗和标准化；
2. `interim -> processed`：M0 输入冻结、M1 concordance、M2 产品冲击与贸易底表，以及 M3.1 connector-sector-year 年度聚合。

M3.1 已执行并在冻结的 M2/crosswalk 输入上完成确定性重建；M3.2-M7 尚未执行。本档案已为后续阶段预留固定结构。以后每完成一个 checklist 项目，必须在同一工作批次内更新本档案和 PDF，才允许打勾。仅有代码、仅有输出、仅有口头说明或尚未解释的 many-to-many join，都不构成完成。

本档案与 `docs/variable_construction_catalog.md` 配套使用。前者回答“数据经历了什么处理、凭什么相信处理正确”，后者回答“每个变量怎样构造、用于什么、允许怎样解释以及如何交给 Stata”。两份材料必须使用同一阶段状态和同一输出证据；若不一致，以实际数据、validation 和 build summary 为准，并在当次工作中修正文档。

### 0.1 本版能够证明什么

- 能证明当前 M0-M3.1 的输入身份、处理规则、输出文件、主键、行数和已执行 validation 均有本地证据。
- 能证明当前 processed 输出的 SHA256 与对应 validation JSON 记录一致。
- 能证明已知的 missing、suppressed、confidential、aggregate、allocated、proxy 和 non-additive 字段没有在 M0-M2 中被静默改成普通零值或普通国家记录。
- 能证明 Section 301 的口径是 gross statutory initial-action exposure，而不是 realized duties。
- 能证明 M3.1 的 1,001 行 connector-sector-year 输出在两个冻结输入上可确定性重建，四条流总量守恒、policy 公式复算和 Stata alias 合同均通过。

### 0.2 本版不能证明什么

- 本次没有从 raw 端完整重跑所有 M0-M2 大型 builder，因此整份 Material Passport 继续使用 `ANALYZED`；M3.1 本身是在冻结输入上两次构建并比较输出 SHA256，单模块 validation 为 `VERIFIED`。
- M3.2-M7 尚未完成，不能据此声称时间窗口增长、replacement ratio、connector ranking、production relocation、structural moments 或 welfare counterfactual 已经得到。
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
    -> M3.2-M3.6窗口、增长、replacement和ranking inputs [未开始]
    -> M4 production-side long table                    [未开始]
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
| M3.2-M3.6 | 未开始 | windows、growth、replacement、ranking inputs | 下一步仅为 M3.2 |
| M4-M6 | 未开始 | production long、integrated evidence、ranking/moments | 不得提前声称结果 |
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

## 10. 当前 processed 输出注册表

M0-M2 SHA256 来自 2026-07-19 validation snapshot，并在 2026-07-27 整理本档案时再次读取本地文件核对。M3.1 SHA256 来自 2026-07-28 正式构建和第二次确定性构建；全部与各自 validation JSON 一致。

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

# 审计 PDF
python code\data_processing\build_data_processing_audit_pdf.py --project-root . --overwrite
python code\data_processing\build_data_processing_audit_pdf.py `
  --project-root . `
  --source docs\variable_construction_catalog.md `
  --output output\pdf\variable_construction_catalog.pdf `
  --overwrite
```

当前 M0-M3.1 还没有单一 orchestration entry；它是 M7.1 的必做项。合作者若现在复核，应按上述顺序执行并逐个查看同名 validation JSON/Markdown。完整重跑会处理超过 123 million BACI rows，应将临时目录和缓存显式指向项目 F 盘。若只复核 M3.1，可以在确认两个配置 hash 后单独运行 M3.1 builder；其确定性临时输出固定在项目 `tmp/m3_1_determinism/` 并由 builder 在比较后清除。

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

### 12.4 M3.2-M3.6 预留记录

后续还必须记录 pre/shock/post aggregation、zero/small base rules、level change 与 growth、ranking component formulas、比较组保留和 sensitivity definitions。M3.2 未开始，不得从 M3.1 年度 level 临时计算并当作正式结果。

### 12.5 M4 预留记录

production long table 必须逐源记录：ICIO accounting fields、AMNE allocated fields、BEA aggregate filtering、BEA suppression、BEA FDI direction/stock/flow、Mexico quarterly annualization 和 confidentiality。统一 long schema 不能让不同来源的 `output`、`sales`、`position`、`flow` 因同名而相加。

### 12.6 M5 预留记录

每加入一个 production source，记录 left join 前后 rows、matched/unmatched keys、source totals、many-to-many expansion count、coverage flags 和可用年份。Integrated evidence table 只有在所有 source totals reconciliation 完成后才可打勾。

### 12.7 M6 预留记录

每个 ranking、rerouting indicator、production validation measure 和 structural moment 必须记录公式、unit、sample、winsorization/denominator rule、source、scenario A/B/C 归属，以及能否进入 model input。不得把 FDI 与 output 合成一个无单位指标而不披露标准化方式和权重。

### 12.8 M7 预留记录

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

## 14. 当前未解决限制和是否需要补数据

| 限制 | 是否影响已完成 M3.1 / 下一步 M3.2 | 可能的后续动作 |
|---|---|---|
| BACI quantity 缺失 | 不影响 value-based M3.1/M3.2 | 保持 value-based；除非研究明确需要 physical quantity 才找替代 |
| Census quantity unavailable | 不影响 | 禁止 quantity analysis；不需为 M3.2 补下载 |
| Census 只有 15 origins | 否 | 只作 configured-origin timing validation；all-origin denominator 用 BACI |
| Section 301 historical exclusions 未应用 | 否，但限制 causal interpretation | 若需要 realized-duty measure，单独开 policy extension |
| 2024 modern HTS 未并入历史面板 | 否 | 需要 modern-HTS concordance 后再单独扩展 |
| AMNE employment 全缺失 | 否 | M4 用 BEA employment；如仍不足再补国家统计 |
| OECD/BEA medical devices 不可单列 | 否 | 保持 unsupported；Mexico/产品层可单列，跨源比较披露缺口 |
| BEA Transportation equipment 比 autos 宽 | 否 | 只作 proxy/ambiguous sensitivity，不作 one-to-one |
| Mexico detail 2024 仅 H1 | 否 | 2024 H1-to-H1 或季度分析；不作 annual total |
| Mexico confidential cells | 否 | 不补 0；报告 disclosed composition 和 national total 分开 |
| INEGI/Vietnam GSO/Statistics Canada 未下载 | 否 | M4-M6 若出现关键 output/employment gap，再定向补充 |

结论：这些主要是定义、覆盖和可比性限制，不是“核心下载只完成一半”。M3.1 已在现有数据上完成；进入 M3.2 不需要继续泛化下载，但以后必须根据具体 empirical gap 决定是否补国家统计数据。

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

### 17.2 M0-M3.1 validation

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

下一次更新触发点：M3.2 的 window builder、config、output 和 validation 全部完成时，同步更新本档案与变量目录并重建两份 PDF，再单独勾选 M3.2。
