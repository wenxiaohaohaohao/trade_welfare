# Connector Economies 项目数据与研究进度

更新日期：2026-07-19
对应分支：`data`
本轮首个远程基准提交：`cfa0a17`（`Complete public Section 301 and Mexico FDI pipelines`）

## Executive Summary / 执行摘要

- **公开数据工程阶段已经基本完成。** BACI、U.S. Census imports、Section 301、OECD ICIO、OECD Analytical AMNE、BEA U.S. MNE、BEA direct investment 和 Mexico 官方 FDI 均已有本地标准化输出、可重复运行的 Python 脚本和 build summary。fDi Markets 按当前要求不处理，也不计入已完成资产。
- **现有数据已经能够分别测量政策冲击、贸易绕行、multinational production、投入产出传播和 FDI，但尚未形成联合识别结果。** 因此目前可以说“具备检验 MP relocation 是否超出 trade rerouting 的数据条件”，不能说“已经证明真实 relocation”。
- **模型基准数据已经生成，但结构模型尚未运行。** OECD ICIO 已生成 2017、2018、2022 三套 MATLAB-ready baseline；Scenario A/B/C 的 `htau`、`hgamma` structural moment、shock files、MATLAB model core 和 welfare counterfactual 尚未完成。
- **下一阶段的关键任务是统一映射和构造研究结果，而不是继续泛化下载。** 应先建立 HS/OECD/BEA/SCIAN concordance，再生成 connector ranking、production-side validation table 和 structural moment table，最后迁移并运行结构模型。

## 一、项目当前处于什么阶段

| 阶段 | 当前状态 | 已有证据 | 进入下一阶段的条件 |
|---|---|---|---|
| 数据下载与归档 | 当前范围内基本完成 | 主要公开来源均有本地文件和版本记录 | 新来源只有在明确增加识别价值时单独开批次 |
| 单库清洗与验证 | 基本完成 | 主要输出均有 `*_build_summary.json`；suppression、confidentiality、nomenclature 和公式残差有记录 | 运行统一跨库 validation，并固定分析版本 |
| 跨数据库统一 | 未完成 | 已有 country groups、sector scope 和 time windows 配置 | 完成 country、sector、product、year concordance |
| 贸易绕行事实 | 未完成 | BACI 与 Census 已可支持两段式贸易流和高频进口验证 | 生成正式 connector ranking、事件研究和稳健性表 |
| 生产转移验证 | 未完成 | AMNE、BEA MNE、BEA FDI、Mexico FDI 和 ICIO 已可组合 | 形成 sector-country-year production-side validation table |
| 结构矩与冲击 | 未完成 | Section 301、trade shares、MP shares 和 FDI/activity measures 均已存在 | 明确每个 moment 对应的 `htau` 或 Scenario B/C `hgamma` |
| 结构模型与福利分解 | 未完成 | 2017、2018、2022 ICIO baseline CSV 已生成 | 完成 MATLAB model-core 迁移、接口测试和 A/B/C counterfactual |

结论是：项目已经从“数据是否能取得”进入“如何把不同口径的数据组织成可信的识别和模型约束”。当前主要风险是跨库口径和解释边界，不是下载失败。

## 二、核心数据资产总览

| 数据源 | 时间覆盖 | 基本粒度 | 主要输出规模 | 在项目中的作用 |
|---|---|---|---:|---|
| CEPII BACI HS2012 | 2014-2024 | exporter-importer-HS6-year | 123,313,077 rows | connector ranking、两段式 rerouting、产品层面贸易变化 |
| U.S. Census imports | 2014-2024 | origin-HTS10/HS6-month | 12,132,098 HS10 rows；5,017,364 HS6 rows | 美国目的地高频进口替代与 China HTS10 权重 |
| USTR Section 301 | 2014-2024 exposure | list/action-HTS10；HS6-year | 32,357 HTS10 events；55,308 HS6-year rows | 政策冲击和 Scenario A `htau` discipline |
| OECD ICIO regular | 2017、2018、2022 | country-sector and bilateral IO links | 12,150 production rows；29,583,977 IO-share rows | 模型基准、trade/IO shares、福利传播 |
| OECD Analytical AMNE | 2008-2023 usable intersection | parent-host-sector-year | 1,260,053 activity rows；4,250,880 MP-share rows | foreign-affiliate output、MP shares、Scenario B `hgamma` |
| BEA U.S. MNE | 2017-2023 | affiliate country/area-industry-year | 8,256 rows | affiliate employment、sales、VA、capex 和 goods trade |
| BEA direct investment | 2020-2024 | direction-country/area-industry-year | 11,610 rows | outward/inward position、flows、income；Scenario C 外部约束 |
| Mexico official FDI | 1999Q1-2024Q4 national；2006Q1-2024Q4 detail | quarter-country-sector-state-investment type | 9 files，1,329,095 rows | Mexico nearshoring 的官方 FDI-flow 验证 |

## 三、数据文件详细说明

### 3.1 CEPII BACI：产品层面双边贸易

主要文件：

| 文件 | 内容 | 行数 |
|---|---|---:|
| `data/interim/trade/baci_hs6_panel.parquet` | 2014-2024 年完整项目期 bilateral HS6 panel | 123,313,077 |
| `data/interim/trade/baci_connector_flows.parquet` | source bloc、connector、destination bloc 相关的两段式流量 | 1,031,244 |
| `data/interim/trade/baci_country_product_year_flags.parquet` | country-product-year 层面的 connector/比较组标记 | 629,146 |

核心字段包括 year、exporter、importer、HS6 product、trade value、quantity、source file 和 country-group flags。贸易额从 BACI 的 thousand USD 转为 USD；HS6 保留为六位字符串。

研究用途：

1. 测量美国从中国进口的受冲击产品是否下降；
2. 测量 connector 对美国出口是否上升；
3. 测量 connector 是否同时增加从中国或东亚进口相关产品和中间品；
4. 构造 product-level connector ranking，并映射至汽车、电子、机械、医疗器械等部门。

解释边界：BACI 是年度 gross trade 数据，没有 ownership、plant 或 firm 信息。它能识别 trade rerouting pattern，不能单独证明当地生产扩张。BACI 的台湾口径是 `S19/Other Asia, nes`，不能静默当作严格 Taiwan-only 观测；quantity 允许缺失，核心 value-based 指标不能依赖 quantity 完整性。

### 3.2 U.S. Census：美国月度进口

主要文件：

| 文件 | 内容 | 行数 |
|---|---|---:|
| `data/interim/trade/us_imports_hs10_monthly.parquet` | 15 个配置来源经济体的月度 HTS10 美国进口 | 12,132,098 |
| `data/interim/trade/us_imports_hs6_monthly.parquet` | 同一来源范围的月度 HS6 聚合 | 5,017,364 |

覆盖来源为 CAN、CHN、IDN、IND、JPN、KOR、MAR、MEX、MYS、PHL、POL、THA、TUR、TWN 和 VNM，时间为 2014-2024。字段包括 import value、customs value、duties、dutiable value、quantity 和商品描述。

研究用途：提供美国目的地的高频进口替代证据；在 Section 301 构建中提供中国来源 HTS10 权重；与 BACI 年度结果进行时点和方向交叉核对。

解释边界：当前 Census 输出只覆盖配置中的 15 个来源经济体，不是 all-origin U.S. imports。它不能被误写成完整世界分母；Section 301 当前使用 BACI HS2017 总进口分母加 Census 中国 HTS10 权重的 hybrid 方案。

### 3.3 Section 301：政策冲击与 `htau`

主要文件：

| 文件 | 内容 | 行数 |
|---|---|---:|
| `data/interim/policy/section301_hts10_list_panel.parquet` | Lists 1、2、3、4A 的 HTS10 action/event panel | 32,357 |
| `data/interim/policy/section301_hs6_exposure.parquet` | 2014-2024 HS2017 年度 gross statutory exposure | 55,308 |
| `data/interim/policy/section301_2024_review_codes.parquet` | 2024 年 9 月 review 的 exact modern-HTS code/rate table | 367 |

官方 base-list source 共 10,115 行。主 exposure 使用 2017 China import share 与法定 tariff rate 构造，BACI HS2017 denominator 有 5,384 个产品；2017 年美国总进口为 USD 2.274 trillion，其中中国来源 USD 492.682 billion。

研究用途：提供相对外生且可追溯的产品层面政策冲击，构造 Scenario A 的 `htau`，并与 BACI/Census 的进口替代和 connector response 联动。

解释边界：这是 gross statutory schedule，不是扣除历次 product exclusions 后的 realized duties。2024 review 使用现代 HTS codes，必须保持为独立表，除非以后建立 scope-aware 的 HTS2022-to-HS2017 concordance。

### 3.4 OECD ICIO：生产、贸易和投入产出基准

主要文件：

| 文件 | 内容 | 行数 |
|---|---|---:|
| `data/interim/production/oecd_icio_output_va_fd.parquet` | gross output、value added、final demand、intermediate inputs、exports、imports | 12,150 |
| `data/interim/production/oecd_icio_io_shares.parquet` | source-country-sector 到 destination-country-sector 的 long-form intermediate-input shares | 29,583,977 |

覆盖 2017、2018、2022，包含 81 个 economy/ROW 单元和 50 个 OECD sectors，单位为 current million USD。MATLAB-ready 目录为：

- `data/model_inputs/icio_baseline_2017/`
- `data/model_inputs/icio_baseline_2018/`
- `data/model_inputs/icio_baseline_2022/`

每个目录含 `X_baseline.csv`、`va_baseline.csv`、`IO_baseline.csv`、`trshare_baseline.csv` 和 `manifest.json`。

研究用途：提供一般均衡模型的 production baseline、trade/absorption shares、value-added shares 和 IO propagation；也可与 AMNE/BEA 的 production-side activity 合并，判断 connector trade expansion 是否伴随 gross output 和 value added 扩张。

验证结果：trade shares 和 IO-share 重构达到 floating-point precision。OECD 矩阵因 rounding 和 statistical adjustments 存在非零 accounting residual，build summary 记录的最大 production-side residual 为 82.032 million USD，最大 sales-side residual 为 238.606 million USD。

### 3.5 OECD Analytical AMNE：foreign affiliate activity 与 MP shares

主要文件：

| 文件 | 内容 | 行数 |
|---|---|---:|
| `data/interim/mne/oecd_amne_affiliate_activity.parquet` | 正 affiliate-output 的 parent-host-sector-year activity cells | 1,260,053 |
| `data/interim/mne/oecd_amne_mp_shares.parquet` | 含 zero MP links 的完整 foreign parent-host-sector-year universe | 4,250,880 |

可用交集覆盖 2008-2023，含 81 host、81 parent 和 41-sector universe；positive affiliate output 涉及 39 sectors。最低字段为：

- `year`
- `host_country_iso3`
- `parent_country_iso3`
- `sector_oecd`
- `affiliate_output`
- `affiliate_value_added`
- `affiliate_employment`
- `affiliate_exports`
- `affiliate_imports`
- `ownership_type`

核心变量：

```text
mpe_expansion[c,s,t]
  = foreign_affiliate_output[c,s,t]
  - foreign_affiliate_output[c,s,t-1]

foreign_affiliate_share[c,s,t]
  = foreign_affiliate_output[c,s,t]
  / gross_output[c,s,t]
```

文件同时保留 parent-specific `mp_output_share` 和用于分配 aggregate foreign-owned activity 的 `parent_affiliate_output_share`。上述 share 和 year-over-year difference 的公式残差为 0。

研究用途：这是区分 multinational-production channel 与纯 trade rerouting 的核心数据之一。若 connector 的产品出口上升，同时相关 host-sector 的 foreign-affiliate output、MP share 或 value added 上升，production relocation 解释会更可信；若只有贸易增长而 production-side measures 不动，则证据更接近 rerouting。

解释边界：affiliate output 是 bilateral output matrix 中直接观测的 parent-host-sector cell；parent-country 的 value added、exports 和 imports 不是直接 bilateral observations，而是按 parent affiliate-output share 从 host-sector foreign-owned aggregate 分配。当前 Analytical AMNE 文件不提供 employment，因此 `affiliate_employment` 全部为 null，必须使用 BEA 或国家统计补充就业证据。

### 3.6 BEA U.S. MNE：美国跨国公司 affiliate activity

主要文件：`data/interim/mne/bea_us_mne_affiliate_country_industry.parquet`

覆盖 2017-2023、75 个 country/area labels、16 个 affiliate industries，共 8,256 行。对象是 majority-owned foreign affiliates of U.S. MNEs。核心变量为：

- employment；
- sales；
- value added；
- capital expenditures；
- goods exports to the United States；
- goods imports from the United States。

研究用途：补充 AMNE 不存在的 employment 和 capex；检查 U.S.-owned affiliates 在 Mexico、Canada、Vietnam 等 connector host 是否扩张；与 AMNE 共同约束 Scenario B incumbent MP-intensive adjustment。

解释边界：BEA `(D)` 和 employment size-range codes 是 suppressed/missing，不是 0；`(*)` 是 rounded small value，并另设 flag。当前 suppression 数量分别为 capex 1,494、sales 1,344、value added 1,290、employment 740、imports from U.S. 2,055、exports to U.S. 1,996。正式分析必须过滤 aggregate geography rows，并报告 suppression 对 sector-country moments 的影响。

### 3.7 BEA direct investment：双向投资账户数据

主要文件：`data/interim/fdi/bea_direct_investment_country_industry.parquet`

覆盖 2020-2024，包含 `U.S. direct investment abroad` 和 `foreign direct investment in the U.S.` 两个方向、80 个 country/area labels、20 个 industries，共 11,610 行。核心指标为 position、financial transactions/flows 和 income。

研究用途：提供 connector-country investment expansion 的外部验证；支持 Scenario C total MP-adjustment upper-bound 的范围约束；与 BEA MNE activity 分开识别“金融投资变化”和“affiliate production activity”。

解释边界：direct-investment position/flows/income 是国际投资账户概念，不是 affiliate output、value added、employment 或 plant entry。当前 suppressed/missing 数量为 flows 2,919、income 2,707、position 1,549，使用时必须保留 suppression flags。

### 3.8 Mexico 官方 FDI：North America nearshoring 的金融流量证据

九个输出如下：

| 文件 | 覆盖 | 行数 |
|---|---|---:|
| `mexico_fdi_national_quarterly.parquet` | 1999Q1-2024Q4 | 104 |
| `mexico_fdi_national_investment_type_quarterly.parquet` | 1999Q1-2024Q4 | 312 |
| `mexico_fdi_parent_country_annual.parquet` | 1999-2024 | 1,191 |
| `mexico_fdi_sector_annual.parquet` | 1999-2024 | 520 |
| `mexico_fdi_state_country_quarterly.parquet` | 2006Q1-2024Q4 | 96,200 |
| `mexico_fdi_state_sector_quarterly.parquet` | 2006Q1-2024Q4 | 616,420 |
| `mexico_fdi_state_investment_type_quarterly.parquet` | 2006Q1-2024Q4 | 7,104 |
| `mexico_fdi_country_sector_quarterly.parquet` | 2006Q1-2024Q4 | 596,366 |
| `mexico_fdi_country_investment_type_quarterly.parquet` | 2006Q1-2024Q4 | 10,878 |

2024 年全国 inward FDI 为 USD 36,872.421 million。national quarter total 与 investment-type sum 的最大差异为 0.000885 million USD。

研究用途：追踪 Mexico post-2020 nearshoring 在来源国、SCIAN 行业、州和投资类型上的变化；与 BEA outward FDI 和 MNE activity 交叉验证；为 Scenario C 提供 Mexico-specific financial-flow discipline。

解释边界：官方 confidential value `C` 保留为 null，不得当作 0。`Total general` 和 `Otros países` 有 aggregate/special flags；country-sector detail 因保密项不能机械加总至全国总额。FDI 是 financial flow，不是 affiliate output，也不能单独证明 plant entry 或 production relocation。

## 四、这些数据如何回答核心研究问题

### 4.1 Trade rerouting 的识别链条

1. Section 301 确定受冲击的 China-origin products 和 tariff timing；
2. Census 检查美国从中国和 connector origins 的月度进口替代；
3. BACI 检查同一 HS6 产品上 China-to-connector 与 connector-to-U.S. 两条贸易腿；
4. 将 HS products 映射到重点 sectors，形成 connector ranking 和 sector exposure。

这条链可以提供强 trade-rerouting evidence，但仍不能说明 connector 本地生产增加。

### 4.2 MP relocation 与纯 rerouting 的区分

生产侧验证需要把贸易变化与下列指标放在同一 country-sector-year 框架内：

- OECD AMNE affiliate output、foreign-affiliate share、MP expansion；
- BEA affiliate employment、sales、value added、capex；
- OECD ICIO gross output 和 value added；
- Mexico/BEA FDI flows 和 positions。

建议采用四项判据：

1. 受冲击产品中，美国从中国进口下降；
2. 美国从 connector 进口上升；
3. connector 从中国或东亚进口相关 intermediates 上升；
4. connector 对应行业的 output、value added、employment、capex、affiliate activity 或 FDI 至少有一组生产侧指标同步上升。

只有 1-3 成立时，应表述为 trade rerouting with limited production-side validation。四项均成立时，才可以谨慎表述为 partial production reallocation channel。即使四项都成立，也不是 firm-level plant relocation 的直接证明。

### 4.3 Scenario A/B/C 的数据约束

| Scenario | 经济含义 | 当前数据约束 | 当前状态 |
|---|---|---|---|
| A | trade-only connector lower bound；`hgamma = 1` | Section 301 `htau`、BACI/Census trade response | 数据具备，moment 尚未构造 |
| B | incumbent MP-intensive baseline | AMNE MP shares/output、BEA affiliate activity、ICIO production | 数据具备，`hgamma` discipline 尚未构造 |
| C | total MP-adjustment upper-bound proxy | Mexico FDI、BEA direct investment、AMNE/BEA activity 和 broader production expansion | 数据具备基础，upper-bound rule 尚未定义；fDi Markets 本批排除 |

Scenario C 不是 endogenous fixed-cost entry model，也不能报告为结构识别的 entry-margin welfare contribution。B 到 C 的差值只能解释为 total MP adjustment 的 scenario upper bound。

## 五、已完成与未完成的交付

### 已完成

- 主要公开来源的下载、归档、标准化和 source-specific validation；
- BACI main project panel 与 Section 301 专用 HS2017 denominator；
- Census configured-origin monthly imports；
- Section 301 official list event panel、annual gross exposure 和 separate 2024 review table；
- OECD ICIO production/IO shares 及 2017、2018、2022 model baselines；
- OECD AMNE affiliate activity 和 MP-share outputs；
- BEA MNE activity 与 BEA direct-investment country-industry panels；
- Mexico 官方 FDI 九张标准化表；
- source versions、usage notes、build summaries 和 suppression/confidentiality 规则。

### 尚未完成

- HS6/HTS10、OECD 41/50 sectors、BEA industries、Mexico SCIAN 的统一 concordance；
- 正式 connector-country ranking、事件研究、rerouting figures 和 tables；
- AMNE/BEA/ICIO/FDI 联合 production-side validation；
- Scenario A/B/C structural moment table；
- scenario-specific MATLAB shock files；
- MATLAB equilibrium solver、welfare decomposition 和 counterfactual results；
- manuscript-ready empirical tables、figures 和 welfare-bound matrix。

## 六、建议的下一步顺序

1. **固定分析口径。** 建立 country、sector、product 和 time concordance，并对每个映射记录 source、many-to-one rule 和未映射率。
2. **先生成最小经验事实。** 计算 Mexico、Vietnam、Canada 等候选 connector 的两段式贸易流和 Section 301 exposure response，优先汽车、电子、机械和医疗器械。
3. **加入生产侧验证。** 将 AMNE、BEA MNE、ICIO、Mexico FDI 和 BEA FDI 合并到 country-sector-year 层面，明确 suppression 和 allocated fields。
4. **构造 structural moments。** 每个 moment 必须注明来源、公式、样本、单位、进入 `htau` 或 `hgamma` 的方式，以及属于 lower bound、baseline 还是 upper bound。
5. **测试模型接口。** 使用一个小型 country-sector sample 验证 ordering、normalization 和 baseline accounting，再迁移完整 MATLAB model core。
6. **运行第一组福利界限。** 比较 direct fragmentation、Scenario A、Scenario B 和 Scenario C，并分别报告 trade、MP 和 IO propagation channels。

在上述步骤完成前，不建议继续扩大数据来源。USITC USMCA automotive statistic 和 BEA Mexico electronics/medical-device suppression 属于明确的剩余核实项；fDi Markets 继续保持不处理。

## 七、关键风险与汇报口径

| 风险 | 正确处理方式 |
|---|---|
| 将贸易增长写成生产转移 | 必须同时给出 production-side activity；否则只称 rerouting 或 connector trade growth |
| 将 FDI flow 写成 plant entry | 明确 FDI 是 financial-account measure，并与 affiliate activity/production 分开 |
| 将 AMNE allocated fields 写成直接 bilateral observations | 在表注中说明 parent-level VA/exports/imports 的分配规则 |
| 将 suppression/confidentiality 当作 0 | BEA `(D)`、size-range codes 和 Mexico `C` 保持 missing 并报告覆盖 |
| 将 Section 301 exposure 写成 realized duties | 只称 gross statutory exposure；exclusions 后税负需要独立构建 |
| 将 configured-origin Census 当作世界分母 | 明确 15-origin scope；全来源 denominator 使用经过验证的 BACI hybrid |
| 将 Scenario C 写成 entry model | 只称 total MP-adjustment upper-bound proxy |

## 八、复现和核查入口

| 内容 | 路径 |
|---|---|
| 数据版本和输出注册 | `configs/data_versions.yaml` |
| 全部来源状态 | `docs/data_source_log.md` |
| 数据目录说明 | `data/README.md` |
| OECD ICIO summary | `data/interim/production/oecd_icio_build_summary.json` |
| OECD AMNE summary | `data/interim/mne/oecd_amne_build_summary.json` |
| BACI summary | `data/interim/trade/baci_batch1_build_summary.json` |
| Census summary | `data/interim/trade/us_census_imports_build_summary.json` |
| Section 301 summary/note | `data/interim/policy/section301_build_summary.json`；`data/section301_usage_note.md` |
| BEA MNE summary | `data/interim/mne/bea_us_mne_affiliate_country_industry_build_summary.json` |
| BEA FDI summary | `data/interim/fdi/bea_direct_investment_country_industry_build_summary.json` |
| Mexico FDI summary/note | `data/interim/fdi/mexico_fdi_build_summary.json`；`data/mexico_fdi_usage_note.md` |

正式分析应从 `data/interim/` 生成新的 `data/processed/` 文件，不直接修改 `data/raw/`。所有正式结果必须能追溯到上述 build summary、usage note 和构建脚本。
