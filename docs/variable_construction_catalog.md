# Connector Economies 变量构造目录与使用指南

## Material Passport

- Origin Skill: `stata-latex-research`
- Origin Date: `2026-07-27`
- Verification Status: `VERIFIED_THROUGH_M3.6`
- Version Label: `variable_catalog_v0.7.0`
- Current Data Stage: `M0-M3.6 completed`
- Next Construction Stage: `M4.1 not started; user authorization required`
- Canonical Format: Parquet
- Collaborator Format: Stata `.dta`

## 0. 结论和使用方式

从 M3.1 开始，变量构造应以本目录为变量合同。它回答六个问题：

1. 变量在哪一层数据上构造；
2. 变量的公式、分母、时间窗口和单位是什么；
3. 变量用于 connector ranking、rerouting、production validation 还是 structural moments；
4. 零值、缺失、负值、small base、suppression 和 confidentiality 如何处理；
5. 变量能否求和、能否跨 connector 比较、能否进入回归或模型；
6. 导出 Stata 时使用什么名称、storage type、主键和验证命令。

本目录同时包含三类变量：

- `EXISTING_VALIDATED`：M2 或 M3.1-M3.6 已存在且 validation PASS；
- `PLANNED_M4` 至 `PLANNED_M6`：已经定义但尚未构造，必须在对应阶段完成后补充实际 output hash 和 validation；
- `STRUCTURAL_TARGET_ONLY`：只能作为模型校准目标或输入候选，不能直接解释为已经识别的结构参数。

凡是本目录未登记的正式变量，不应直接写入最终 processed data。临时探索变量可以存在于 `tmp/` 或交互式 Stata session，但进入正式输出前必须补齐本目录。

本目录与 `docs/data_processing_audit_trail.md` 构成同一套审查材料。本目录不重复数据来源和完整处理历史，而是引用审计档案中的输入、输出和 validation 证据；审计档案也不能替代这里的变量级公式、用途和解释边界。M3-M7 任一阶段完成时，两份 Markdown、两份 PDF 和对应 build summary 必须同步更新。

## 1. 状态、粒度和可加总性代码

### 1.1 状态

| 状态 | 含义 |
|---|---|
| `EXISTING_VALIDATED` | 已在 processed Parquet 中存在，主键和 validation 已通过 |
| `PLANNED_M4` | production-side standardized long table 时构造 |
| `PLANNED_M5` | trade 和 production evidence 合并时构造 |
| `PLANNED_M6` | ranking、rerouting、validation 和 structural moments 时构造 |
| `STRUCTURAL_TARGET_ONLY` | 观测 moment 或 candidate shock，不等于已识别结构参数 |
| `PROHIBITED` | 明确禁止构造或禁止解释的变量 |

### 1.2 粒度代码

| Grain ID | 唯一键 | 主要文件 |
|---|---|---|
| `G_PRODUCT_YEAR` | `analysis_hs6, year` | product treatment |
| `G_CONN_PRODUCT_YEAR` | `connector_iso3, analysis_hs6, year` | connector trade |
| `G_ORIGIN_PRODUCT_MONTH` | `origin_iso3, analysis_hs6, year, month` | Census monthly |
| `G_CONN_SECTOR_YEAR` | `connector_iso3, analysis_sector, year` | M3 trade-sector |
| `G_CONN_SECTOR_WINDOW` | `connector_iso3, analysis_sector, window_id` | M3 window summaries |
| `G_CONN_SECTOR_COMPARISON` | `connector_iso3, analysis_sector` | M3 pre/shock/post comparison and growth |
| `G_CONN_SECTOR_FLOW_DIAG` | `connector_iso3, analysis_sector, flow_id` | M3.3 small-base、异常增长和 winsorized sensitivity diagnostics |
| `G_CONN_PRODUCT_WINDOW` | `connector_iso3, analysis_hs6` | M3.4 产品窗口变化、policy exposure 和共变底表 |
| `G_CONN_SECTOR_REORG` | `connector_iso3, analysis_sector` | M3.4 replacement、source-input、exposure-overlap 核心指标 |
| `G_CONN_SECTOR_COMOVE` | `connector_iso3, analysis_sector` | M3.4 HS6 产品共变与 rerouting diagnostics |
| `G_CONN_SECTOR_COMMON` | `connector_iso3, analysis_sector` | M3.5 完整 13-connector × 7-sector 共同面板；不含结果筛选或排名 |
| `G_PROD_LONG` | `country_iso3, analysis_sector, year, source_name, metric_name`，必要时增加 direction/parent | M4 production long |
| `G_EVIDENCE` | `connector_iso3, analysis_sector, year` | M5 integrated evidence |
| `G_RANK` | `connector_iso3, analysis_sector, ranking_spec` | M6 ranking |
| `G_MOMENT` | `moment_id, scenario` | M6 structural moments |

### 1.3 可加总性代码

| Code | 规则 |
|---|---|
| `ADD_WITHIN_KEYS` | 可以在不跨越声明维度时求和，例如产品金额聚合到 sector |
| `NONADDITIVE_RATE` | rate/share/exposure 不能直接求和，必须重算分子分母 |
| `NONADDITIVE_REPEAT` | 为比较而重复，绝不能跨重复维度求和 |
| `STOCK` | 时点/期末 stock，不能跨年求和 |
| `FLOW` | 期间 flow，可在不重叠期间内求和 |
| `LEVEL` | level，可比较或求差，但通常不跨单位/来源相加 |
| `FLAG` | 逻辑状态，不作金额加总 |

## 2. 通用键、标签和 provenance 变量

这些字段必须尽可能贯穿 M3-M7。它们不是辅助杂项，而是合作者复核 join 和解释边界的基础。

| Canonical name | Stata name | Type | Grain | 用途 | 状态 |
|---|---|---|---|---|---|
| `connector_iso3` | `conn_iso3` | str3 | connector grains | connector 国家键 | existing/planned |
| `country_iso3` | `country_iso3` | str3 | production | production host/country 键 | planned M4 |
| `analysis_hs6` | `hs6` | str6 | product grains | 保留 leading zeros 的产品键 | existing |
| `analysis_sector` | `ana_sector` | str32 | sector grains | 第一阶段共同经验 sector | existing |
| `year` | `year` | int | annual grains | calendar year | existing |
| `month` | `month` | byte | monthly | 1-12 | existing |
| `window_id` | `window_id` | str8 | window | pre/shock/post | existing validated |
| `source_name` | `source` | str20 | production long | 数据来源区分 | planned M4 |
| `metric_name` | `metric` | str32 | production long | 指标区分 | planned M4 |
| `unit` | `unit` | str32 | all long outputs | 单位，禁止跨单位相加 | planned M4 |
| `mapping_version` | `map_ver` | str32 | all | concordance 版本 | planned |
| `build_version` | `build_ver` | str32 | all | builder/output schema 版本 | existing/planned |
| `source_row_count` | `src_n` | long | all | 聚合 cell 的原始行数 | existing/planned |
| `source_file_count` | `srcfile_n` | int | all | provenance 完整性 | existing/planned |
| `mapping_status` | `map_status` | str32 | all | mapped/aggregate/residual/ambiguous 等 | existing/planned |
| `is_analysis_eligible` | `ana_ok` | byte | all | 是否进入第一阶段主分析 | existing/planned |
| `is_proxy` | `is_proxy` | byte | all | TWN S19 或其他 proxy | existing/planned |
| `is_aggregate` | `is_agg` | byte | production/country | aggregate geography/sector | existing/planned |
| `is_residual` | `is_resid` | byte | country | Mexico residual 等 | existing/planned |
| `suppressed_flag` | `suppressed` | byte | production | BEA suppressed | planned M4 |
| `confidential_flag` | `confidentl` | byte | production | Mexico confidential | existing/planned |
| `allocated_flag` | `allocated` | byte | production | AMNE allocated metric | planned M4 |
| `nonadditive_flag` | `nonadd` | byte | all | repeated/rate/stock 不可加总 | planned |

Stata 中所有逻辑变量使用 numeric byte 0/1，并附 value label。不能把 Python boolean 转成字符串 `"True"`/`"False"`。

## 3. M2 已验证的政策变量

文件：`data/processed/harmonized/product_treatment_hs6_year.parquet`。粒度 `G_PRODUCT_YEAR`。

| Canonical name | Stata name | 定义/单位 | 可加总性 | 用途 | 状态 |
|---|---|---|---|---|---|
| `total_us_import_value_2017` | `usimp17` | 2017 total U.S. imports，USD | level；映射后可加总 | treatment 分母 | existing validated |
| `china_import_value_2017` | `chnimp17` | 2017 China imports，USD | level；映射后可加总 | China share 和 weights | existing validated |
| `china_import_share_2017` | `chnshr17` | `chnimp17/usimp17`，fraction | nonadditive rate | exposure 分母结构 | existing validated |
| `tariff_rate_china_weighted` | `trf_chw` | source HS17 rate 按 China imports 加权 | nonadditive rate | sensitivity/provenance | existing validated |
| `tariff_rate_total_import_weighted` | `trf_usw` | source rate 按 total imports 加权 | nonadditive rate | zero-China fallback | existing validated |
| `tariff_rate` | `trf_rate` | 最终 statutory rate，fraction | nonadditive rate | policy intensity | existing validated |
| `tariff_exposure` | `trf_expo` | `sum(China imports × rate)/sum(total imports)` | nonadditive rate | 主 gross exposure | existing validated |
| `tariffed_product` | `tariffed` | 任一 mapped source code rate > 0 | flag | treatment indicator | existing validated |
| `source_hs17_code_count` | `hs17_n` | 汇入 analysis product 的 HS17 数量 | count | audit many-to-one | existing validated |
| `policy_source_observed_count` | `polobs_n` | legal panel 中 observed source codes | count | 区分 not-listed 与 missing | existing validated |
| `source_tariffed_hs17_count` | `trfhs17_n` | positive-rate source codes | count | treatment composition | existing validated |
| `tariff_rate_max_source` | `trf_max` | mapped sources 最大法定 rate | nonadditive rate | denominator=0 fallback | existing validated |
| `policy_mapping_status` | `pol_map` | weighted/no denominator/no HS17 weight | category | sample/filter/audit | existing validated |
| `historical_exclusions_applied` | `hist_excl` | 当前恒为 0 | flag | 防止误称 realized duties | existing validated |
| `four_year_review_2024_included` | `rev24_in` | 当前恒为 0 | flag | 防止误并 2024 review | existing validated |

禁止变量：

| Prohibited name/concept | 原因 |
|---|---|
| `realized_tariff_paid` from current panel | 当前数据未重建 customs-entry realized duties |
| `tariff_exposure_with_exclusions` | historical exclusions 尚未应用 |
| `2024_review_hs6` by first-six-digit truncation | modern HTS scope 和 historical HS6 不可直接等同 |

## 4. M2 已验证的贸易金额和 Census 变量

### 4.1 Connector trade

文件：`connector_trade_hs6_year.parquet`。粒度 `G_CONN_PRODUCT_YEAR`。

| Canonical name | Stata name | 单位 | 可加总性 | 用途 | 状态 |
|---|---|---|---|---|---|
| `china_to_usa_value_usd` | `cn_us_val` | current USD | `NONADDITIVE_REPEAT` across connector | 共同 China-USA benchmark | existing validated |
| `china_to_connector_value_usd` | `cn_conn_val` | current USD | add across products, not connectors unless desired | China input leg | existing validated |
| `east_asia_to_connector_value_usd` | `ea_conn_val` | current USD | add across products | East Asia input leg | existing validated |
| `connector_to_usa_value_usd` | `conn_us_val` | current USD | add across products/connectors with clear scope | connector export leg | existing validated |
| `*_row_count` | shortened `*_n` | count | additive count | 区分 true zero 与 source rows | existing validated |
| `east_asia_self_trade_excluded` | `ea_selfx` | flag | flag | KOR/TWN self-trade rule | existing validated |
| `baci_absence_treated_as_zero` | `baci_zrule` | flag | flag | complete-grid zero rule | existing validated |
| `china_to_usa_common_benchmark` | `cnus_common` | flag | flag | repeated warning | existing validated |
| `treatment_repeated_across_connectors` | `trf_repeat` | flag | flag | non-additive warning | existing validated |

### 4.2 Census

月度 grain `G_ORIGIN_PRODUCT_MONTH`；年度 grain `origin_iso3, analysis_hs6, year`。

| Canonical name | Stata name | 单位/公式 | 用途 | 状态 |
|---|---|---|---|---|
| `import_value_usd` | `imp_val` | current USD | 主进口金额 | existing validated |
| `customs_value` | `cust_val` | current USD | customs valuation check | existing validated |
| `duties` | `duties` | current USD | collected duties 描述，不等于 Section 301-only duties | existing validated |
| `dutiable_value_usd` | `dutiable` | current USD | dutiable base | existing validated |
| `observed_month_count` | `month_n` | 0-12 | 年度 cell 的月度覆盖 | existing validated |
| `calendar_source_months_complete` | `cal12_ok` | flag | 允许 sparse absence -> zero 的前提 | existing validated |
| `quantity_usable` | `qty_ok` | 当前恒为 0 | 禁止 quantity analysis | existing validated |
| `is_all_origin_denominator` | `allorig` | 当前恒为 0 | 防止误作全来源分母 | existing validated |

`duties/import_value` 可以作为描述性 average duty ratio，但不能命名为 Section 301 realized rate，除非另行识别 tariff program 和 entry-level scope。

## 5. M3.1 connector-sector-year 基础聚合变量

状态：`EXISTING_VALIDATED`。

正式文件：`data/processed/harmonized/connector_trade_sector_year.parquet`。粒度 `G_CONN_SECTOR_YEAR`，唯一键为 `connector_iso3, analysis_sector, year`。

构建证据：

- builder：`code/data_processing/build_connector_trade_sector_panel.py`；
- 冻结配置：`configs/connector_trade_sector_rules.yaml`；
- 输入：743,886 行 `connector_trade_hs6_year.parquet` 与 5,202 行 `product_sector_crosswalk.parquet`；
- 输出：1,001 行、70 列，13 connectors × 7 sectors × 2014-2024；
- 输出 SHA256：`95e547267892c4bc883788542f0e59ba284441b42f4ce1d379aea71a2f978c8c`；
- validation：`data/validation/connector_trade_sector_panel_validation.json` 与 `.md`，状态 `PASS`；
- 配置 SHA256：`6a313c01d9bfad6e6e6a2cb508bd787f35bdb0eddeb6e4f491a86d61bdd9ee9d`；
- 确定性检查：项目 F 盘临时目录第二次构建的 Parquet SHA256 与正式输出完全一致，临时目录已清除；
- Stata 接口：70 个 alias 全部登记、互不重复、最长 14 个字符，均不超过 Stata 的 32 字符限制。本阶段不提前生成 `.dta`。

### 5.1 金额和覆盖

先用 `analysis_hs6` 把 M2 panel many-to-one 连接到 canonical product-sector crosswalk。只有 canonical `is_analysis_sector_eligible=true` 且 `sector_mapping_weight=1` 的产品，才在 `connector_iso3, analysis_sector, year` 内求和。M2 内嵌 sector 字段只用于一致性检查，不能取代 canonical crosswalk。

| Canonical name | Stata name | 公式 | 可加总性 | 用途 | 状态 |
|---|---|---|---|---|---|
| `china_to_usa_value_usd` | `cn_us_val` | `sum_h eligible china_to_usa_value_usd` | `NONADDITIVE_REPEAT` across connector | China decline benchmark | `EXISTING_VALIDATED` |
| `china_to_connector_value_usd` | `cn_conn_val` | `sum_h eligible china_to_connector_value_usd` | `FLOW` | China input leg | `EXISTING_VALIDATED` |
| `east_asia_to_connector_value_usd` | `ea_conn_val` | `sum_h eligible east_asia_to_connector_value_usd` | `FLOW` | broader source input leg | `EXISTING_VALIDATED` |
| `connector_to_usa_value_usd` | `conn_us_val` | `sum_h eligible connector_to_usa_value_usd` | `FLOW` | connector export leg | `EXISTING_VALIDATED` |
| `sector_eligible_product_count` | `sec_elig_n` | sector 内 distinct eligible HS6 | count | sector composition 与 denominator | `EXISTING_VALIDATED` |

四条流各有独立 diagnostics；`<flow>` 分别是 `china_to_connector`、`east_asia_to_connector`、`connector_to_usa` 和 `china_to_usa`：

| Canonical pattern | Stata aliases | 公式和含义 | 状态 |
|---|---|---|---|
| `<flow>_value_usd_row_count` | `cn_conn_src_n`, `ea_conn_src_n`, `conn_us_src_n`, `cn_us_src_n` | eligible products 的 M2 source-row count 之和 | `EXISTING_VALIDATED` |
| `<flow>_positive_product_count` | `cn_conn_pos_n`, `ea_conn_pos_n`, `conn_us_pos_n`, `cn_us_pos_n` | sector 内 `<flow>_value_usd > 0` 的 eligible HS6 数 | `EXISTING_VALIDATED` |
| `<flow>_zero_source_product_count` | `cn_conn_zsrc_n`, `ea_conn_zsrc_n`, `conn_us_zsrc_n`, `cn_us_zsrc_n` | sector 内 M2 `<flow>_row_count = 0` 的 eligible HS6 数；保留 source absence，不等同 observed zero | `EXISTING_VALIDATED` |

excluded、outside-manufacturing 和 residual products 没有可用于 sector sums 的有效 sector weight，因此 coverage 在 `connector_iso3, year` 粒度计算后跨 7 个 sector 重复。所有 coverage 字段都带 `coverage_repeated_across_sectors=true`，不能跨 sector 求和。

| Canonical name | Stata name | 公式 | 可加总性 | 状态 |
|---|---|---|---|---|
| `excluded_product_count` | `excl_prod_n` | connector-year 内 965 个非 eligible 产品的 distinct count | `NONADDITIVE_REPEAT` across sector | `EXISTING_VALIDATED` |
| `china_to_connector_excluded_value_usd` | `cn_conn_excl` | 非 eligible 产品的 China→connector value sum | `NONADDITIVE_REPEAT` across sector | `EXISTING_VALIDATED` |
| `china_to_connector_included_value_share` | `cn_conn_inclsh` | eligible / full-universe China→connector value | `NONADDITIVE_RATE` | `EXISTING_VALIDATED` |
| `east_asia_to_connector_excluded_value_usd` | `ea_conn_excl` | 非 eligible 产品的 East Asia→connector value sum | `NONADDITIVE_REPEAT` across sector | `EXISTING_VALIDATED` |
| `east_asia_to_connector_included_value_share` | `ea_conn_inclsh` | eligible / full-universe East Asia→connector value | `NONADDITIVE_RATE` | `EXISTING_VALIDATED` |
| `connector_to_usa_excluded_value_usd` | `conn_us_excl` | 非 eligible 产品的 connector→USA value sum | `NONADDITIVE_REPEAT` across sector | `EXISTING_VALIDATED` |
| `connector_to_usa_included_value_share` | `conn_us_inclsh` | eligible / full-universe connector→USA value | `NONADDITIVE_RATE` | `EXISTING_VALIDATED` |
| `china_to_usa_excluded_value_usd` | `cn_us_excl` | 非 eligible 产品的 China→USA value sum；同时跨 connector 重复 | `NONADDITIVE_REPEAT` | `EXISTING_VALIDATED` |
| `china_to_usa_included_value_share` | `cn_us_inclsh` | eligible / full-universe China→USA value；同时跨 connector 重复 | `NONADDITIVE_RATE` | `EXISTING_VALIDATED` |

### 5.2 sector-level treatment

先对 `analysis_hs6, year` 去除 connector 复制，再在 sector-year 重算分子和分母。Policy rate/exposure 不能按产品 rate 直接求和。

| Canonical name | Stata name | 公式 | 用途 | 状态 |
|---|---|---|---|---|
| `sector_total_us_import_value_2017` | `sec_usimp17` | `sum_h usimp17_h` | transparent denominator | `EXISTING_VALIDATED` |
| `sector_china_import_value_2017` | `sec_cnimp17` | `sum_h chnimp17_h` | China weight denominator | `EXISTING_VALIDATED` |
| `sector_tariff_exposure_numerator_usd` | `sec_trf_num` | `sum_h(chnimp17_h × rate_h,t)` | common transparent numerator | `EXISTING_VALIDATED` |
| `sector_tariff_rate_china_weighted` | `sec_trf_cw` | `sec_trf_num / sec_cnimp17` | 法定 rate intensity | `EXISTING_VALIDATED` |
| `sector_tariff_exposure` | `sec_expo` | `sec_trf_num / sec_usimp17` | 主 gross policy exposure | `EXISTING_VALIDATED` |
| `sector_china_import_share_2017` | `sec_cnshr17` | `sec_cnimp17 / sec_usimp17` | baseline China dependence | `EXISTING_VALIDATED` |
| `sector_treatment_product_count` | `sec_trt_n` | distinct eligible HS6 | policy count denominator | `EXISTING_VALIDATED` |
| `policy_denominator_observed_product_count` | `pol_denobs_n` | `usimp17_h > 0` 且非缺失的 eligible HS6 数 | denominator audit | `EXISTING_VALIDATED` |
| `tariffed_product_count` | `trf_prod_n` | `tariffed_product=true` 的 eligible HS6 数 | breadth numerator | `EXISTING_VALIDATED` |
| `tariffed_china_import_value_2017` | `trf_cnimp17` | tariffed eligible HS6 的 China imports sum | China treatment mass | `EXISTING_VALIDATED` |
| `tariffed_total_us_import_value_2017` | `trf_usimp17` | tariffed eligible HS6 的 total U.S. imports sum | total-import treatment mass | `EXISTING_VALIDATED` |
| `tariffed_product_share_count` | `trf_psh_n` | `trf_prod_n / sec_trt_n` | breadth | `EXISTING_VALIDATED` |
| `tariffed_product_share_china_value` | `trf_psh_c` | `trf_cnimp17 / sec_cnimp17` | China treatment mass share | `EXISTING_VALIDATED` |
| `tariffed_product_share_us_value` | `trf_psh_u` | `trf_usimp17 / sec_usimp17` | total-import treatment mass share | `EXISTING_VALIDATED` |

缺少 denominator 或 HS2017 mapping 的产品不静默转成普通零 denominator：

| Canonical name | Stata name | 公式/含义 | 状态 |
|---|---|---|---|
| `treatment_missing_denominator_product_count` | `trt_missden_n` | `usimp17_h` 缺失或不大于 0 的 eligible HS6 数 | `EXISTING_VALIDATED` |
| `treatment_zero_denominator_product_count` | `trt_zeroden_n` | `policy_mapping_status=mapped_hs17_no_2017_import_denominator` 的 HS6 数；全样本 17 个 distinct products | `EXISTING_VALIDATED` |
| `treatment_no_hs17_mapping_product_count` | `trt_nohs17_n` | `policy_mapping_status=no_hs17_baci_weight_mapping` 的 HS6 数；全样本 11 个 distinct products | `EXISTING_VALIDATED` |
| `treatment_missing_denominator_product_share` | `trt_miss_sh` | missing denominator count / `sec_trt_n` | `EXISTING_VALIDATED` |
| `treatment_zero_denominator_product_share` | `trt_zero_sh` | zero denominator count / `sec_trt_n` | `EXISTING_VALIDATED` |
| `treatment_no_hs17_mapping_product_share` | `trt_nohs17_sh` | no-HS2017-mapping count / `sec_trt_n` | `EXISTING_VALIDATED` |

主回归/排名应优先使用 `sector_tariff_exposure`，同时把 weighted rate 和 tariffed shares 作为 robustness，不把它们互相替代。

### 5.3 标签、版本和不可加总 flags

| Canonical name | Stata name | 内容/规则 | 状态 |
|---|---|---|---|
| `connector_group` | `conn_group` | core/comparator 分组 | `EXISTING_VALIDATED` |
| `connector_baci_code` | `conn_baci` | BACI reporter/partner code | `EXISTING_VALIDATED` |
| `connector_is_proxy` | `is_proxy` | TWN 使用 BACI S19 proxy；TWN 的 77 行全部为 1 | `EXISTING_VALIDATED` |
| `analysis_sector_status` | `sec_status` | canonical sector status | `EXISTING_VALIDATED` |
| `trade_value_unit` | `val_unit` | current USD | `EXISTING_VALIDATED` |
| `treatment_concept` | `trt_concept` | gross statutory initial actions | `EXISTING_VALIDATED` |
| `historical_exclusions_applied` | `hist_excl` | 恒为 0 | `EXISTING_VALIDATED` |
| `four_year_review_2024_included` | `rev24_in` | 恒为 0 | `EXISTING_VALIDATED` |
| `review_2024_treatment` | `rev24_trt` | separate exact-HTS extension | `EXISTING_VALIDATED` |
| `treatment_version` | `trt_ver` | M2 treatment version | `EXISTING_VALIDATED` |
| `is_analysis_sector_eligible` | `ana_ok` | 本输出恒为 1 | `EXISTING_VALIDATED` |
| `sector_mapping_weight` | `sec_wt` | 本输出恒为 1 | `EXISTING_VALIDATED` |
| `baci_absence_treated_as_zero` | `baci_zrule` | complete-grid BACI absence rule | `EXISTING_VALIDATED` |
| `quantity_included` | `qty_in` | 恒为 0；本输出不含 quantity | `EXISTING_VALIDATED` |
| `china_to_usa_common_benchmark` | `cnus_common` | China→USA benchmark 跨 connector 重复 | `EXISTING_VALIDATED` |
| `treatment_repeated_across_connectors` | `trt_repeat` | sector treatment 跨 connector 重复 | `EXISTING_VALIDATED` |
| `coverage_repeated_across_sectors` | `cov_repeat` | connector-year coverage 跨 sector 重复 | `EXISTING_VALIDATED` |
| `common_benchmarks_not_additive_across_connectors` | `bm_nonadd` | 禁止跨 connector 求和共同 benchmark | `EXISTING_VALIDATED` |
| `product_mapping_version` | `prod_mapver` | canonical product-sector mapping version | `EXISTING_VALIDATED` |
| `m3_sector_aggregation_version` | `m3_aggver` | `connector_trade_sector_rules_v1` | `EXISTING_VALIDATED` |
| `schema_version` | `schema_ver` | `connector_trade_sector_year_v1` | `EXISTING_VALIDATED` |

### 5.4 M3.1 验证结论和解释边界

- 两个输入 SHA256 与冻结配置一致；输入、crosswalk 和输出主键重复均为 0；全部 HS6 成功匹配，M2 内嵌 sector 字段与 canonical crosswalk 不一致数为 0。
- eligible HS6 数固定为 autos 64、electrical equipment 177、electronics 252、machinery 467、medical devices 32、other manufacturing 2,422、textiles/apparel 823。
- 四条 flow 的 product-level eligible totals 与 sector totals 差额均为 USD 0；`eligible + excluded = full universe` 的 connector-year 最大差额均为 USD 0。
- 九个 policy rate/share 字段独立公式复算最大绝对误差均为 0，小于 `1e-12`。
- China→USA benchmark、policy 和 coverage 的重复一致性不一致数均为 0。
- 当前输出只含年度 level、coverage 和 sector treatment。它不含 pre/shock/post window、growth、small-base、replacement ratio、ranking、production-side 或 structural moments。

## 6. M3.2 时间窗口变量

状态：`EXISTING_VALIDATED`。

正式文件：

1. `data/processed/harmonized/connector_trade_sector_window.parquet`：273 行、79 列，粒度 `G_CONN_SECTOR_WINDOW`，唯一键 `connector_iso3, analysis_sector, window_id`；
2. `data/processed/harmonized/connector_trade_sector_window_comparison.parquet`：91 行、142 列，粒度 `G_CONN_SECTOR_COMPARISON`，唯一键 `connector_iso3, analysis_sector`。

构建证据：

- builder：`code/data_processing/build_connector_trade_sector_window_panel.py`；
- 冻结配置：`configs/connector_trade_sector_window_rules.yaml`，SHA256 `95d42ee146b1e0cf6e98261b46e5db52bf81000770d12d55da3371350d50058b`；
- 冻结输入：1,001 × 70 的 M3.1 年度 panel，SHA256 `95e547267892c4bc883788542f0e59ba284441b42f4ce1d379aea71a2f978c8c`；
- 时间定义：`configs/time_windows.yaml`，SHA256 `d1daeed066db7cf734c15c804f31eaaf66a7c07b335f3c227a6c9effffd6ebb5`；
- long 输出 SHA256：`310da7f289d8760d3ead34215a294be18275c758a2084cfd9f905988b695e704`；
- comparison 输出 SHA256：`be5f3a025a81d36d5a9bb1bd137d4bed9325a68ab5f1cb7f4d946a2373fbeb04`；
- validation：`data/validation/connector_trade_sector_window_validation.json` 与 `.md`，状态 `PASS`；
- 确定性检查：项目 F 盘第二次构建的两张 Parquet 分别与正式候选逐字节 hash 相同，候选和 determinism 临时目录均已清除；
- Stata 接口：long 79 个、comparison 142 个 resolved aliases 全部完整、互不重复，最长 13 字符。本阶段仍不生成 `.dta`。

### 6.1 窗口定义和 long annual-mean levels

不同窗口长度不相等：pre 4 年、shock 2 年、post 5 年。因此 level comparison 使用完整年度观察的算术平均值，不使用窗口总和。

| `window_id` | 年份 | `window_order` | expected/observed years | 状态 |
|---|---|---:|---:|---|
| `pre` | 2014-2017 | 1 | 4 / 4 | `window_complete=true` |
| `shock` | 2018-2019 | 2 | 2 / 2 | `window_complete=true` |
| `post` | 2020-2024 | 3 | 5 / 5 | `window_complete=true` |

所有 91 个 connector-sector cells 在三个窗口都完整，没有 partial-window mean。Long 表的窗口字段为：

| Canonical name | Stata name | 定义 | 状态 |
|---|---|---|---|
| `window_id` | `window_id` | pre/shock/post | `EXISTING_VALIDATED` |
| `window_order` | `win_order` | 1/2/3 | `EXISTING_VALIDATED` |
| `window_start_year` / `window_end_year` | `win_start` / `win_end` | 冻结端点 | `EXISTING_VALIDATED` |
| `expected_year_count` / `observed_year_count` | `exp_yn` / `obs_yn` | 预期与实际 distinct years | `EXISTING_VALIDATED` |
| `window_complete` | `win_complete` | observed=expected | `EXISTING_VALIDATED` |
| `window_level_is_annual_mean` | `win_mean` | 本输出恒为 1 | `EXISTING_VALIDATED` |

四条流在 long 表使用下列 family。`<flow>`/`<prefix>` 对应 `china_to_connector/cncn`、`east_asia_to_connector/eacn`、`connector_to_usa/cnusx`、`china_to_usa/cnus`。

| Canonical pattern | Stata pattern | 公式/含义 | 状态 |
|---|---|---|---|
| `<flow>_value_usd_annual_mean` | `<prefix>_val` | 完整窗口年度金额算术平均 | `EXISTING_VALIDATED` |
| `<flow>_source_row_count_annual_mean` | `<prefix>_src_n` | M3.1 flow-specific source-row counts 的年度平均 | `EXISTING_VALIDATED` |
| `<flow>_positive_product_count_annual_mean` | `<prefix>_pos_n` | positive eligible HS6 count 的年度平均 | `EXISTING_VALIDATED` |
| `<flow>_zero_source_product_count_annual_mean` | `<prefix>_zsrc_n` | source-row count=0 eligible HS6 count 的年度平均；不等同 observed zero | `EXISTING_VALIDATED` |

年度 count 的窗口平均可能为非整数，因此 long 表中这些 annual-mean diagnostics 使用 `double`；底层年度 count 没有被修改。

### 6.2 Coverage 使用 ratio of sums

非 eligible 产品没有 sector weight。Coverage 仍先在 `connector_iso3, year` 计算，再聚合到 `connector_iso3, window_id` 并跨 sector 重复；`coverage_repeated_across_sectors=true` 继续禁止跨 sector 加总。

| Canonical pattern | Stata pattern | 公式 | 可加总性 | 状态 |
|---|---|---|---|---|
| `excluded_product_count` | `excl_prod_n` | 窗口内固定的非 eligible 产品数 965 | `NONADDITIVE_REPEAT` | `EXISTING_VALIDATED` |
| `<flow>_excluded_value_usd_annual_mean` | `<prefix>_excl` | 非 eligible 年度金额的窗口平均 | `NONADDITIVE_REPEAT` across sector | `EXISTING_VALIDATED` |
| `<flow>_included_value_share` | `<prefix>_inclsh` | `sum_t eligible_value_t / sum_t(eligible_value_t + excluded_value_t)` | `NONADDITIVE_RATE` | `EXISTING_VALIDATED` |
| `included_value_share_uses_ratio_of_sums` | `incl_rsum` | 本输出恒为 1，禁止误解为 annual shares 的简单平均 | `FLAG` | `EXISTING_VALIDATED` |

### 6.3 Window policy summaries

Policy denominator 仍是透明的 2017 sector denominator。时间变化的 numerator/count/value 先取完整窗口年度平均，再重算 rate/share；不平均年度 rate/share。

| Canonical name | Stata name | 公式 | 状态 |
|---|---|---|---|
| `sector_tariff_exposure_numerator_usd_annual_mean` | `sec_trf_num` | `mean_t sector_tariff_exposure_numerator_usd_t` | `EXISTING_VALIDATED` |
| `sector_total_us_import_value_2017` | `sec_usimp17` | 固定 2017 total-import denominator | `EXISTING_VALIDATED` |
| `sector_china_import_value_2017` | `sec_cnimp17` | 固定 2017 China-import denominator | `EXISTING_VALIDATED` |
| `sector_tariff_rate_china_weighted` | `sec_trf_cw` | annual-mean numerator / `sec_cnimp17` | `EXISTING_VALIDATED` |
| `sector_tariff_exposure` | `sec_expo` | annual-mean numerator / `sec_usimp17` | `EXISTING_VALIDATED` |
| `sector_china_import_share_2017` | `sec_cnshr17` | `sec_cnimp17 / sec_usimp17` | `EXISTING_VALIDATED` |
| `tariffed_product_count_annual_mean` | `trf_prod_n` | 年度 tariffed eligible-product count 的窗口平均 | `EXISTING_VALIDATED` |
| `tariffed_china_import_value_2017_annual_mean` | `trf_cnimp17` | tariffed China-import mass 的年度平均 | `EXISTING_VALIDATED` |
| `tariffed_total_us_import_value_2017_annual_mean` | `trf_usimp17` | tariffed total-import mass 的年度平均 | `EXISTING_VALIDATED` |
| `tariffed_product_share_count` | `trf_psh_n` | annual-mean tariffed count / treatment count | `EXISTING_VALIDATED` |
| `tariffed_product_share_china_value` | `trf_psh_c` | annual-mean tariffed China value / `sec_cnimp17` | `EXISTING_VALIDATED` |
| `tariffed_product_share_us_value` | `trf_psh_u` | annual-mean tariffed total value / `sec_usimp17` | `EXISTING_VALIDATED` |

Treatment denominator observed/missing/zero/no-HS2017 counts和 shares 保留为窗口字段。每个窗口跨 sector 加总仍为 17 个 zero-denominator eligible products 和 11 个 no-HS2017-mapping eligible products。Pre 的 91 个 connector-sector policy exposure 全部为 0；本模块没有对 policy exposure 构造 change、percentage growth 或 log growth。

### 6.4 Comparison levels、changes 和 growth

对任意非负年度 flow `x_t`：

```text
x_pre  = mean(x_t, 2014-2017)
x_shk  = mean(x_t, 2018-2019)
x_post = mean(x_t, 2020-2024)

d_x_post_pre = x_post - x_pre
g_dh_x_post_pre = 2 * (x_post - x_pre) / (x_post + x_pre)
g_log_x_post_pre = ln(x_post) - ln(x_pre), only if both > 0
```

`g_dh` 是推荐 primary growth：无量纲、允许一端为 0、范围 [-2,2]。`g_log` 只用于 positive-base robustness。禁止把 undefined log growth 自动设为 0。

Comparison 表对每条贸易腿构造：

| Family | Canonical stem | Stata prefix | Pre/shock/post | Change | DH | Log |
|---|---|---|---|---|---|---|
| China -> USA | `china_to_usa` | `cnus` | `cnus_pre/shk/post` | `d_cnus` | `gdh_cnus` | `gln_cnus` |
| China -> connector | `china_to_connector` | `cncn` | `cncn_pre/shk/post` | `d_cncn` | `gdh_cncn` | `gln_cncn` |
| East Asia -> connector | `east_asia_to_connector` | `eacn` | `eacn_pre/shk/post` | `d_eacn` | `gdh_eacn` | `gln_eacn` |
| connector -> USA | `connector_to_usa` | `cnusx` | `cnusx_pre/shk/post` | `d_cnusx` | `gdh_cnusx` | `gln_cnusx` |

完整 canonical patterns 是 `<flow>_value_usd_pre/shock/post`、`<flow>_value_usd_change_post_pre`、`<flow>_value_usd_dh_growth_post_pre` 和 `<flow>_value_usd_log_growth_post_pre`。Comparison 表还展开四条流的 excluded annual mean、included-value share，以及九个随窗口变化的 policy summaries；固定 2017 denominators 和 denominator-exception counts/shares只保留一份，避免无意义的 pre/shock/post 复制。

### 6.5 Zero/defined flags 和 M3.3 边界

| Canonical pattern | Stata pattern | 定义 | 状态 |
|---|---|---|---|
| `<flow>_pre_zero_flag` | `<prefix>_pre0` | pre annual mean = 0 | `EXISTING_VALIDATED` |
| `<flow>_post_zero_flag` | `<prefix>_post0` | post annual mean = 0 | `EXISTING_VALIDATED` |
| `<flow>_dh_growth_defined` | `<prefix>_dhok` | pre+post != 0 | `EXISTING_VALIDATED` |
| `<flow>_log_growth_defined` | `<prefix>_logok` | pre>0 and post>0 | `EXISTING_VALIDATED` |
| `<flow>_years_observed_pre/shock/post` | `<prefix>_preyn/shkyn/postyn` | 实际 distinct years | `EXISTING_VALIDATED` |

边界规则已实现：

- 两端都为 0：DH 和 log 均缺失；
- 只有一端为 0：DH 为 ±2，log 缺失；
- 两端都为正：DH 和 log 均定义；
- 负 level change 和负 growth 原样保留，不截断。

当前数据四条流的 pre-zero 和 post-zero 数都为 0，每条流 91 个 log growth 全部定义。负 post-pre change 数分别为 China→connector 3、East Asia→connector 5、connector→USA 6、China→USA 26。DH 全部位于 [-2,2]，没有 infinite。

M3.2 本身不设 small-base 阈值、不标异常、不 winsorize；这些规则已经在单独的 M3.3 long diagnostic interface 中实现。推荐主排名继续同时使用 level change 和通过 M3.3 eligibility 的 DH growth，不依赖单一百分比增长；未经阈值筛选的 DH 仍保留为 robustness。

### 6.6 M3.2 validation 和解释边界

- M3.1 input hash、70-column Arrow schema signature、1,001 行和年度主键全部匹配冻结配置；
- 每个年度观察恰好属于一个窗口，source window definition 与 frozen definition 完全一致；
- long/comparison 主键重复均为 0，行数严格为 273/91；
- 四条流 annual mean × years 与 M3.1 annual sum 的最大金额差额均为 USD 0；source-row、positive-product 和 zero-source diagnostics 的 count reconciliation gap 均为 0；
- comparison 的 pre/shock/post levels 与 long 完全一致；change、DH 和 log 独立复算最大绝对误差均为 0；
- coverage ratio-of-sums 和所有 policy numerator/denominator/rate/share 独立复算误差均为 0；
- China→USA/policy 跨 connector、coverage 跨 sector 的 inconsistency count 均为 0；
- TWN 有 21 个 long rows、7 个 comparison rows，proxy false count 为 0；
- long/comparison required numeric missing count 均为 0；
- 两张 Parquet 的第二次确定性构建 SHA256 分别完全一致，candidate 和 determinism 临时目录已清除。

M3.2 可以作为 M3.3 的唯一输入接口之一。它不能用于声称 small-base 处理、异常增长决策、replacement ratio、connector ranking、production relocation 或 structural moments 已完成。

### 6.7 M3.3 small-base、异常增长与 winsorized sensitivity

M3.3 使用 M3.2 comparison 表作为唯一输入，不改写 M3.2。输出为：

`data/processed/harmonized/connector_trade_sector_growth_diagnostics.parquet`

- grain：`G_CONN_SECTOR_FLOW_DIAG`；
- 主键：`connector_iso3, analysis_sector, flow_id`；
- 行列数：364 × 64，即 91 个 connector-sector cells × 4 条 flow；
- schema version：`connector_trade_sector_growth_diagnostics_v1`；
- construction version：`connector_trade_sector_growth_diagnostic_rules_v1`；
- SHA256：`fe69d953cd84a2acfc64ddb17b1ee57e3d0e44f7b44cad348f9016aee7e0953d`；
- validation：`data/validation/connector_trade_sector_growth_diagnostics_validation.json/.md`，status `PASS`。

四条 `flow_id` 为 `china_to_connector`、`east_asia_to_connector`、`connector_to_usa` 和 `china_to_usa`。每行复制该 flow 的 pre/shock/post annual-mean level、post-pre level change、原始 DH/log growth、zero/defined flags 和 4/2/5 observed-year counts。复制值与 M3.2 逐 flow 对账；level tolerance 为 USD 0.01，growth tolerance 为 `1e-12`，实际最大差额均为 0。

#### 6.7.1 Small-base 合同

```text
absolute_small_base_flag
    = 1[value_usd_pre <= USD 25,000,000]

sector_relative_cutoff
    = nearest-rank p10 of value_usd_pre
      within flow_id × analysis_sector

sector_relative_small_base_flag
    = 1[value_usd_pre <= sector_relative_cutoff]

small_base_flag
    = pre_zero_flag
      OR absolute_small_base_flag
      OR sector_relative_small_base_flag
```

相对门槛的 reference group 是每个 sector 内 13 个 connectors；nearest-rank `ceil(0.10 × 13)=2`，因此 cutoff 是该组第二小的 pre value。China→USA 是跨 connector 重复的共同 benchmark，同一 sector 的 13 行数值相同，做 connector-relative 排名没有含义，所以 `sector_relative_threshold_applicable=false`、cutoff missing、relative flag false；这 91 个 missing 是设计结果，不是数据遗漏。

| Canonical name | Stata alias | 定义/用途 | 状态 |
|---|---|---|---|
| `absolute_small_base_threshold_usd` | `sb_abs_cut` | 固定 USD 25 million | `EXISTING_VALIDATED` |
| `absolute_small_base_flag` | `sb_abs` | pre level 不高于绝对门槛 | `EXISTING_VALIDATED` |
| `sector_relative_pre_value_cutoff_usd` | `sb_rel_cut` | flow-sector nearest-rank p10 cutoff | `EXISTING_VALIDATED` |
| `sector_relative_small_base_flag` | `sb_rel` | pre level 不高于相对 cutoff | `EXISTING_VALIDATED` |
| `small_base_flag` | `small_base` | zero/absolute/relative 的并集 | `EXISTING_VALIDATED` |
| `dh_growth_primary_eligible` | `dh_prim_ok` | DH defined 且非 small base | `EXISTING_VALIDATED` |
| `log_growth_robustness_eligible` | `log_rob_ok` | log defined 且非 small base | `EXISTING_VALIDATED` |
| `dh_growth_no_threshold_eligible` | `dh_nothr_ok` | 只要求 DH defined 的无门槛 robustness | `EXISTING_VALIDATED` |

当前 absolute/relative/combined flag 数分别为：China→connector 0/14/14；East Asia→connector 0/14/14；connector→USA 4/14/14；China→USA 0/0/0。四个 absolute small-base cells 均为 connector→USA，分别是 MAR electrical equipment、MAR machinery、MAR medical devices 和 TUR medical devices。Absolute flags 是 relative flags 的子集，所以 connector→USA combined count 仍为 14。Preferred DH/log sample 对前三条 connector-specific flows 各保留 77 个 cells；no-threshold DH robustness 每条 flow 均保留 91 个。

#### 6.7.2 异常增长合同

在每个 `flow_id × analysis_sector` 组内：

```text
robust_z = 0.6744897501960817
           × (DH - median(DH)) / MAD(DH)

robust_z_outlier_flag = 1[|robust_z| > 3.5]
mechanical_extreme_dh_flag = 1[|DH| >= 1.5]
abnormal_growth_flag = robust_z_outlier OR mechanical_extreme
```

`|DH| >= 1.5` 对应 post/pre 至少为 7 或至多为 1/7。MAD=0 时 robust z 明确 missing、`robust_z_defined=false`，不除以 0；当前 7 个 MAD-zero groups 全部是跨 connector 重复的 China→USA sector benchmark，因此共有 91 个预期的 `robust_z_score_dh` missing。

当前 robust-z / mechanical / combined abnormal counts 为 China→connector 1/0/1、East Asia→connector 1/0/1、connector→USA 1/3/4、China→USA 0/0/0。Combined abnormal cells 共 6 个：PHL textiles/apparel 的 China input decline；POL other manufacturing 的 East Asia input growth；IND electronics、MAR medical devices、VNM electrical equipment 的 connector→USA mechanical extremes；VNM other manufacturing 的 connector→USA robust-z outlier。`abnormal_growth_flag` 只是 review flag，不自动删除、不改变 eligibility，也不覆盖原始值。

#### 6.7.3 Winsorized sensitivity 合同

DH 与 log growth 分别在 91 个 observations 的 `flow_id` pooled sample 内使用 linear/type-7 p5 和 p95：

```text
growth_winsorized = min(max(growth_raw, p5_flow), p95_flow)
```

对前三条 connector-specific flows，DH 和 log 各有 10 行被边界替代；China→USA 因 7 个 sector values 各重复 13 次，p5/p95 等于实际最小/最大 sector value，affected count 为 0。采用 91-cell flow-level pool 是为了避免在只有 13 个 observations 的 flow-sector group 内用 p5/p95 机械截断每个 sector 的边缘值；sector-specific heterogeneity 继续由 raw values、sector-relative small-base 和后续 ranking 处理。`winsorized_values_for_sensitivity_only=true`，不能替代 raw DH/log；`raw_level_change_preserved=true`，level change 完全不 winsorize。

| Canonical name | Stata alias | 用途 | 状态 |
|---|---|---|---|
| `value_usd_dh_growth_post_pre_raw` | `gdh_raw` | 未截断 DH 主值/robustness | `EXISTING_VALIDATED` |
| `value_usd_log_growth_post_pre_raw` | `gln_raw` | positive-base raw log growth | `EXISTING_VALIDATED` |
| `dh_growth_winsorized` | `dh_win` | flow-level p5/p95 sensitivity | `EXISTING_VALIDATED` |
| `log_growth_winsorized` | `log_win` | flow-level p5/p95 sensitivity | `EXISTING_VALIDATED` |
| `abnormal_growth_flag` | `abn_growth` | advisory review flag | `EXISTING_VALIDATED` |

全部 64 个 canonical fields 有唯一 Stata alias，最长 11 字符。TWN 有 28 行且 proxy flag 全部保留。China→USA levels/growth/cutoffs 在同一 sector 跨 connector 完全一致，并用 `flow_repeated_across_connectors=true` 与 `flow_not_additive_across_connectors=true` 明确禁止跨 connector 求和。Parquet 的第二次项目 F 盘确定性构建 SHA256 完全一致，candidate/determinism 临时目录已清除。本阶段不导出 `.dta`。

M3.3 只确定样本诊断与敏感性接口；它没有构造 replacement ratio、ranking、production evidence、structural moments 或 counterfactual inputs。

## 7. M3.4-M3.6 贸易重组、共同面板与 sensitivity inputs

M3.4 已完成并通过 validation。使用三个自然粒度输出，避免把产品字段、部门指标和部门相关系数机械重复到同一张超级宽表：

| Output | Rows × columns | Natural key | SHA256 |
|---|---:|---|---|
| `connector_trade_product_reorganization_window.parquet` | 55,081 × 56 | `connector_iso3, analysis_hs6` | `1c83dc1070656c903d625b2e85c82ea6e7afa18535105351ccef24a405ed2c34` |
| `connector_trade_sector_reorganization_indicators.parquet` | 91 × 92 | `connector_iso3, analysis_sector` | `f13c5f8aa0c4402d0b467a06a6b99ba8ddc8389d47ede9ba8c8036275c1d74f2` |
| `connector_trade_sector_product_comovement.parquet` | 91 × 49 | `connector_iso3, analysis_sector` | `3095cd39a7355ce6968e0e5c29956841fd9e40bc72238d06aafe8d3ef0c3b0f1` |

冻结 config 为 `configs/connector_trade_reorganization_indicator_rules.yaml`，SHA256 为 `0305b9a2a0904f9eac9953a89f977565a644fc25167e4be7b04dad9a44a7fe4d`。Builder 为 `code/data_processing/build_connector_trade_reorganization_indicators.py`；validation 为 `data/validation/connector_trade_reorganization_indicators_validation.json/.md`，状态 PASS。三张表的 56/92/49 个 Stata aliases 均完整、唯一且最长分别为 13/14/13 字符。

### 7.1 Import replacement

```text
china_us_decline = max(cnus_pre - cnus_post, 0)
connector_us_gain = cnusx_post - cnusx_pre
replacement_ratio = connector_us_gain / china_us_decline
```

`replacement_ratio` 只有在 `china_us_decline` 严格大于 USD 25 million 时定义；否则 missing。connector gain 保留正负符号，不截为 0，不使用 arbitrary epsilon，不在 M3.4 构造 capped ratio。当前 91 个 cells 中有 26 个 ratio defined；其中 22 个 connector gain 为正，4 个为负；其余 65 个 ratio 保持 missing。主结果同时保留 level gain 和 decline，不能只报告 ratio。

| Canonical name | Stata name | 用途 | 状态 |
|---|---|---|---|
| `china_us_decline_usd` | `cnus_drop` | China displacement level | `EXISTING_VALIDATED` |
| `connector_us_gain_usd` | `conn_gain` | connector gain level，保留负值 | `EXISTING_VALIDATED` |
| `replacement_ratio` | `repl_ratio` | signed connector gain 相对 China decline | `EXISTING_VALIDATED` |
| `replacement_ratio_defined` | `repl_ok` | denominator 是否严格大于 USD 25 million | `EXISTING_VALIDATED` |
| `import_replacement_candidate_flag` | `repl_cand` | defined 且 connector gain > 0 | `EXISTING_VALIDATED` |
| `replacement_capped_for_rank` | `repl_cap` | 仅 ranking 的 capped version | `PLANNED_M6`，M3.4-M3.6 均未构造 |

### 7.2 Source-to-connector input growth

| Canonical name | Stata name | 定义/状态 |
|---|---|---|
| `china_input_gain_usd` | `cnin_gain` | China→connector post-pre level change；`EXISTING_VALIDATED` |
| `east_asia_input_gain_usd` | `eain_gain` | East Asia→connector post-pre level change；`EXISTING_VALIDATED` |
| `china_input_dh_growth_raw` | `gdh_cnin` | 从 M3.3 原样继承的 China input DH growth；`EXISTING_VALIDATED` |
| `east_asia_input_dh_growth_raw` | `gdh_eain` | 从 M3.3 原样继承的 East Asia input DH growth；`EXISTING_VALIDATED` |
| `connector_export_dh_growth_raw` | `gdh_conn` | 从 M3.3 原样继承的 connector→USA DH growth；`EXISTING_VALIDATED` |
| `china_input_to_export_ratio_pre/post` | `srcx_cnpre/srcx_cnpost` | China input / connector export，同窗口；`EXISTING_VALIDATED` |
| `east_asia_input_to_export_ratio_pre/post` | `srcx_eapre/srcx_eapost` | East Asia input / connector export，同窗口；`EXISTING_VALIDATED` |
| `china_input_to_export_ratio_change` | `d_srcx_cn` | post-pre；`EXISTING_VALIDATED` |
| `east_asia_input_to_export_ratio_change` | `d_srcx_ea` | post-pre；`EXISTING_VALIDATED` |

China-only 与 extended East Asia 是两套独立 source 定义，不能混成一个未标口径的字段。ratio denominator 是同窗口 connector→USA export，只有严格大于 0 时定义；当前两套 pre/post ratios 均为 91/91 defined。不能用 arbitrary epsilon 生成正式值。M3.3 的 small-base、primary eligibility 和 abnormal flags 一并原样带入部门核心表；M3.4 不改写 raw growth。

### 7.3 Product-level co-movement

先在 55,081 行产品窗口表中对每个 connector-HS6 计算四条贸易流的 2014-2017 annual mean、2020-2024 annual mean 和 post-pre change，再在 connector-sector 内聚合。产品 active 规则为 source pre + post + connector export pre + post 严格大于 0。Pearson correlation 至少要求 20 个 active products；weighted correlation 以 source input pre + connector export pre 为权重并至少要求 20 个正权重 products。当前 China/East Asia 的 91 个普通和 91 个 weighted correlations 全部定义；最小 active counts 为 31/32，最小正权重 counts 为 30/31。

| Canonical name | Stata name | 公式/用途 |
|---|---|---|
| `china/east_asia_both_legs_positive_product_share` | `cn/ea_both_psh` | source input gain >0 且 connector-US product gain >0，占全部 eligible HS6 |
| `china/east_asia_both_legs_positive_active_share` | `cn/ea_both_ash` | 同一 product count，占 source-specific active HS6 |
| `china/east_asia_both_legs_positive_export_gain_share` | `cn/ea_both_gsh` | 条件产品的正 connector-export gain / 全部正 connector-export gain |
| `china_decline_connector_gain_product_share` | `rerout_psh` | China-US decline 且 connector-US product gain >0，占 eligible HS6 |
| `china/east_asia_triple_condition_product_share` | `cn/ea_triple_psh` | China-US decline、source input gain、connector-US gain 同时成立 |
| `china/east_asia_product_change_correlation` | `cn/ea_prod_cor` | source-input change 与 connector-export change 的 HS6 Pearson correlation |
| `china/east_asia_weighted_product_change_correlation` | `cn/ea_wprod_cor` | 使用 pre source input + pre connector export 权重 |

eligible-product share、active-product share 和 positive-export-gain share 使用不同分母，不能互相替代。Value share 的分母是逐产品 `max(connector export change, 0)` 之和，不是部门净 change。相关系数和 share 全部通过独立复算，越界数为 0。它们是 descriptive co-movement diagnostics，不是 rerouting 的因果估计。

### 7.4 Exposure overlap

| Canonical name | Stata name | 公式 |
|---|---|---|
| `connector_export_tariff_overlap_pre` | `ovlp_pre` | pre connector-US exports 中 tariffed/exposed product 的 value share |
| `connector_export_tariff_overlap_post` | `ovlp_post` | post share |
| `connector_export_exposure_weighted_pre/post` | `expo_w_pre/expo_w_post` | observed-exposure products 内以 connector export value 加权的 product exposure |
| `connector_export_exposure_observed_value_share_pre/post` | `expo_cov_pre/expo_cov_post` | exposure-weighted分母相对全部 connector export value 的覆盖 |
| `gain_in_positive_exposure_products_share` | `gain_pos_sh` | 有 observed exposure 的正 export gain 中，positive-exposure products 的份额 |
| `gain_in_top_quartile_exposure_products_share` | `gain_top_sh` | 有 observed exposure 的正 export gain 中，sector-positive-exposure p75 以上产品的份额 |

产品 exposure 使用 post 五年 tariff exposure 的平均值；tariffed flag 使用 post tariff-status mean > 0。28 个 eligible products 的 exposure 缺失保持 missing，其中 14 个 tariffed，不能当作 exposure=0。Exposure-weighted分母只含 observed-exposure products，同时输出覆盖率。两套 high-exposure 定义均已冻结并报告：`exposure > 0`，以及 analysis-sector 内 positive observed exposure 的 linear/type-7 p75。Tariffed、positive exposure 和 top-quartile exposure 是不同概念，不得互相替代。China→USA 和 policy 产品字段在 connectors 间重复，只作比较，明确 non-additive。

### 7.5 M3.5 完整 connector/comparator 共同面板

M3.5 已完成并通过 validation。输出为：

| Output | Rows × columns | Natural key | SHA256 |
|---|---:|---|---|
| `connector_trade_sector_common_panel.parquet` | 91 × 152 | `connector_iso3, analysis_sector` | `36c58c229f3f43e86f7ff7570fc6a1ffe08ccb8fd3259bb5853abece3171f682` |

冻结 config 为 `configs/connector_trade_sector_common_panel_rules.yaml`，SHA256 为 `374a1a18c756f38054ae3ecf077f1e2f148c53da9a07cc5b1338c01d92b44d40`。Builder 为 `code/data_processing/build_connector_trade_sector_common_panel.py`；validation 为 `data/validation/connector_trade_sector_common_panel_validation.json/.md`，状态 PASS。

共同面板只合并相同自然粒度的两张 M3.4 表：以 91 × 92 的 sector-reorganization 表为 master，将 91 × 49 的 product-comovement 表按 `connector_iso3, analysis_sector` one-to-one 合并。91 个 keys 在两边全部匹配；9 个共同内容字段逐值 mismatch 为 0；两张输入各自的 schema version 分开登记；37 个 co-movement 专属字段未经变换加入。M3.5 不把 connector-product 表与 sector 表横向拼接，因此没有产品层金额的机械重复。

样本顺序和角色固定为：

| Group | Connectors | Connector count | Panel rows |
|---|---|---:|---:|
| `core_connectors` | VNM, MEX, CAN | 3 | 21 |
| `asian_comparators` | IND, IDN, MYS, PHL, THA, KOR, TWN | 7 | 49 |
| `other_candidates` | POL, MAR, TUR | 3 | 21 |

每个 connector 恰有 7 个 analysis sectors，每个 sector 恰有 13 个 connectors。这个 13 × 7 网格不依赖 replacement ratio 是否定义、增长方向、exposure overlap、co-movement、未来排名或 production data availability。

| Canonical name | Stata name | 定义/用途 | 状态 |
|---|---|---|---|
| `core_connector_flag` | `core_conn` | VNM/MEX/CAN 角色 | `EXISTING_VALIDATED` |
| `asian_comparator_flag` | `asia_comp` | 7 个 Asian comparators | `EXISTING_VALIDATED` |
| `other_candidate_flag` | `other_cand` | POL/MAR/TUR | `EXISTING_VALIDATED` |
| `comparison_sample_included` | `sample_in` | 共同面板保留状态；当前 91/91 为 true | `EXISTING_VALIDATED` |
| `connector_group_order` | `conn_grp_ord` | core/Asian/other 的稳定排序 1/2/3 | `EXISTING_VALIDATED` |
| `connector_order_within_group` | `conn_ord` | 冻结配置中的组内顺序 | `EXISTING_VALIDATED` |
| `analysis_sector_order` | `sec_ord` | 7 个 sectors 的稳定顺序 | `EXISTING_VALIDATED` |
| `m3_sector_source_row_matched` | `sec_src_ok` | M3.4 sector master row matched | `EXISTING_VALIDATED` |
| `m3_comovement_source_row_matched` | `comov_src_ok` | M3.4 co-movement row matched | `EXISTING_VALIDATED` |
| `outcome_based_selection_applied` | `outcome_sel` | 当前全部 false | `EXISTING_VALIDATED` |
| `top_rank_filter_applied` | `toprank_sel` | 当前全部 false | `EXISTING_VALIDATED` |
| `complete_case_filter_applied` | `ccase_sel` | 当前全部 false | `EXISTING_VALIDATED` |
| `ranking_variables_constructed` | `rank_built` | 当前全部 false；ranking 留到 M6 | `EXISTING_VALIDATED` |
| `production_variables_included` | `prod_incl` | 当前全部 false；production 留到 M4-M5 | `EXISTING_VALIDATED` |
| `sensitivity_variables_constructed` | `sens_built` | 在 M3.5 共同面板中全部 false；三张 M3.6 输出中全部 true | `EXISTING_VALIDATED` |

M3.4 的数值和缺失状态全部保留：26 个 `replacement_ratio` defined、65 个 missing、22 个正 connector-gain candidates；四套 China/East Asia 普通/weighted correlations 均为 91/91 defined，low-n 均为 0；TWN 7 行继续标记 proxy。共同面板有 152 个完整、唯一、不超过 Stata 32 字符的 aliases，实际最长 14 字符。它是后续 sensitivity 和 ranking 的共同样本接口，不是已完成 ranking，也不是“胜出 connector”样本；不能据此作因果 rerouting、production relocation 或 structural welfare 解释。

### 7.6 M3.6 sensitivity inputs

状态：`EXISTING_VALIDATED`。M3.6 只构造 sensitivity inputs，不计算 score、rank、winner、production evidence 或 structural moment。输出采用三张自然粒度长表，避免把不同定义的变量误写成同一宽表中的可互换指标。

| Output | Rows × columns | Natural key | SHA256 |
|---|---:|---|---|
| `connector_trade_sector_time_window_sensitivity.parquet` | 1,092 × 56 | `connector_iso3, analysis_sector, flow_id, window_spec_id` | `1594fadeb348f88e07b2ec8f43ca3708f49f9e06a0b78fafe24ffb6417635aad` |
| `connector_trade_sector_source_bloc_sensitivity.parquet` | 182 × 64 | `connector_iso3, analysis_sector, source_bloc_id` | `67fbf760adb01a18d4e0e4f9ddd44eef9f3d2d2496a0a60d358cf8eab77e1eda` |
| `connector_trade_sector_exposure_definition_sensitivity.parquet` | 364 × 47 | `connector_iso3, analysis_sector, exposure_definition_id` | `96144e95dd525103b658ed7220a15d2f3c7c7acf79ea3f314314112971dc7cbd` |

冻结 config 为 `configs/connector_trade_sector_sensitivity_rules.yaml`，SHA256 为 `b628a76fc7a5615d5decf9a39810a476b653a81c2d74a68c2d5d35d45af3f11f`。Builder 为 `code/data_processing/build_connector_trade_sector_sensitivity.py`；validation 为 `data/validation/connector_trade_sector_sensitivity_validation.json/.md`，状态 PASS。

#### 7.6.1 Alternative time windows

四条 `flow_id` 为 `china_to_connector`、`east_asia_to_connector`、`connector_to_usa` 和 `china_to_usa`。三个 `window_spec_id` 为：

| Specification | Base | Comparison | 原因 |
|---|---|---|---|
| `primary_post` | 2014-2017 | 2020-2024 | 与 M3.2/M3.4 主口径一致 |
| `exclude_2024` | 2014-2017 | 2020-2023 | 2024 同时是数据边界和 Section 301 review 年，必须排除检查 |
| `shock_only` | 2014-2017 | 2018-2019 | 判断变化方向是否已在最初 tariff-shock 期出现 |

所有 level 使用窗口内年度值的算术平均：

```text
pre_trade_scale_usd        = mean(x_t, base years)
comparison_trade_scale_usd = mean(x_t, comparison years)
level_change_usd           = comparison_trade_scale_usd - pre_trade_scale_usd
dh_growth                  = 2 * level_change_usd
                             / (comparison_trade_scale_usd + pre_trade_scale_usd)
log_growth                 = ln(comparison_trade_scale_usd)
                             - ln(pre_trade_scale_usd)
```

`log_growth` 仅在两个端点严格大于 0 时定义；两端均为 0 时 DH/log 均 missing；仅一端为 0 时 DH 为 `±2`、log missing。当前 1,092 行没有零端点，1,092 个 log growth 全部定义。

Coverage 不平均年度 share：

```text
included_value_share_window
  = sum(eligible_value_t)
    / [sum(eligible_value_t) + sum(excluded_value_t)]
```

窗口内稳定性变量为：

| Canonical name | Stata name | 定义 |
|---|---|---|
| `pre_trade_scale_usd` | `scale_pre` | 2014-2017 annual mean |
| `comparison_trade_scale_usd` | `scale_comp` | 当前 specification comparison annual mean |
| `annual_growth_transition_count` | `ann_tr_n` | comparison 窗口内相邻年份 DH growth 的可用转移数 |
| `annual_dh_growth_sd` | `ann_dh_sd` | 相邻年份 DH growth 的 sample SD，`ddof=1` |
| `positive_growth_year_share` | `posyr_sh` | comparison 窗口内正相邻年份 level change 比例 |
| `primary_level_change_usd` | `prim_dlev` | 同一 flow 的 `primary_post` level change |
| `level_change_difference_from_primary_usd` | `dlev_dprim` | 当前 specification 减 primary |
| `dh_growth_difference_from_primary` | `dh_dprim` | 当前 DH 减 primary DH |
| `log_growth_difference_from_primary` | `log_dprim` | 当前 log growth 减 primary log growth |
| `same_level_change_direction_as_primary` | `dlev_same` | 三方向 sign 是否一致 |
| `same_dh_growth_direction_as_primary` | `dh_same` | 三方向 sign 是否一致 |

`shock_only` 只有 2018→2019 一个年际转移，所以 364 行 `annual_dh_growth_sd` 按 sample-SD 定义保持 missing；`positive_growth_year_share` 可由一个转移定义。这个 missing 不能填 0。当前三个 specifications 的负 level-change counts 为：

| Specification | China→connector | East Asia→connector | connector→USA | China→USA |
|---|---:|---:|---:|---:|
| `primary_post` | 3 | 5 | 6 | 26 |
| `exclude_2024` | 3 | 5 | 6 | 26 |
| `shock_only` | 13 | 12 | 13 | 26 |

`china_to_usa` 是在 connectors 间重复的 common benchmark；`flow_is_common_benchmark` 和 `common_benchmark_not_additive_across_connectors` 均为 true，禁止跨 connector 求和。

#### 7.6.2 Source-bloc definitions

| `source_bloc_id` | Members | Self-trade rule |
|---|---|---|
| `china_only` | CHN | 当前 connector 集合不含 CHN，无 self-trade |
| `extended_east_asia` | CHN, KOR, JPN, TWN | connector 为 KOR/TWN 时排除本国 origin |

Source 表把两种定义映射到同一 generic schema，包括 `input_value_usd_pre/post`、`input_gain_usd`、raw DH/log、small-base/eligibility/abnormal flags、input-to-export ratios、active/weighted product counts、普通/weighted correlations、both-legs shares 和 triple-condition shares。核心 aliases 为：

| Canonical name | Stata name | 说明 |
|---|---|---|
| `source_bloc_id` | `src_bloc` | source 定义 |
| `source_bloc_members_configured` | `src_members` | 分号分隔的配置成员 |
| `connector_self_trade_excluded` | `self_excl` | KOR/TWN 在 extended East Asia 定义下为 true |
| `input_value_usd_pre/post` | `input_pre/input_post` | source→connector annual-mean levels |
| `input_gain_usd` | `input_gain` | post-pre，负值保留 |
| `input_dh_growth_raw` | `input_dh` | raw DH，不 winsorize |
| `input_to_export_ratio_change` | `d_sx` | source-input / connector-export ratio 的变化 |
| `product_change_correlation` | `prod_cor` | source input 与 connector export 的 HS6 change correlation |
| `input_gain_usd_difference_from_china_only` | `dgain_cn` | 当前 definition 减 China-only |
| `same_input_gain_direction_as_china_only` | `gain_same` | sign agreement |
| `source_bloc_comparison_is_nested` | `src_cmpnest` | 当前全部 true |

Extended East Asia 包含 China，因此两定义不是两个独立样本。`extended_east_asia - china_only` 的 level difference 只表示额外 KOR/JPN/TWN origins（并应用 self-trade exclusion）的贡献。当前负 input gains 为 China-only 3 行、extended East Asia 5 行；KOR/TWN self-trade-excluded rows 为 14；两口径在 input gain、DH、input-export-ratio change、product correlation 上方向一致的 connector-sector cells 分别为 89、89、73、89。

#### 7.6.3 Exposure definitions

| `exposure_definition_id` | `exposure_measure_unit` | `exposure_measure_value` |
|---|---|---|
| `tariff_overlap` | `share_0_1` | post connector export value 中 tariffed products 的份额 |
| `exposure_weighted_rate` | `ad_valorem_rate` | observed-exposure products 内，以 connector export value 加权的连续 exposure |
| `positive_exposure_gain_share` | `share_0_1` | observed-exposure positive export gain 中，exposure > 0 产品的份额 |
| `top_quartile_exposure_gain_share` | `share_0_1` | observed-exposure positive export gain 中，sector positive-exposure p75 以上产品的份额 |

前两种 definitions 有 `exposure_measure_pre/post/change`；后两种是 gain-based estimands，pre/post/change 三列设计性 missing，正式值写在 `exposure_measure_value`。所有 definition 均保留 `numerator_usd_*`、`denominator_usd_*` 和 observed-value coverage，以便 Stata 独立复算。

| Canonical name | Stata name | 说明 |
|---|---|---|
| `exposure_definition_id` | `expo_def` | 四种定义 |
| `exposure_measure_pre/post` | `expo_pre/expo_post` | 仅 level-based definitions 适用 |
| `exposure_measure_change` | `d_expo` | post-pre，允许为负 |
| `exposure_measure_value` | `expo_value` | 当前 definition 的正式 measure |
| `measure_value_basis` | `value_basis` | `post_level` 或 `positive_export_gain` |
| `pre_post_missing_by_design` | `pp_na` | gain-based definitions 为 true |
| `value_coverage_share_pre` | `cov_pre` | pre observed-value coverage |
| `value_coverage_share_post_or_gain` | `cov_comp` | post 或 positive-gain coverage |
| `high_exposure_threshold_value` | `expo_thr` | 0、missing continuous threshold 或 sector p75 |
| `cross_definition_numeric_difference_forbidden` | `cross_forbid` | 当前全部 true |

四种 definitions 虽然正式值都位于 `[0,1]`，但 estimand 和单位不完全相同，不能直接互减或把数值大小解释成同一种 exposure。M3.6 明确不构造 cross-definition numeric difference 或 rank。28 个 exposure-missing products 仍保持 missing；按七个 sectors 求和，每个 connector 都有 28 个，未填 0。`tariff_overlap` 和 `exposure_weighted_rate` 的负 pre-post change 分别为 47 和 32 个 cells。

#### 7.6.4 Validation 与 Stata 接口

- 三张表主键 duplicate 均为 0，13 connectors × 7 sectors 全部保留。
- 时间表的 annual means、coverage ratio-of-sums、level/DH/log、annual SD、positive-year share 和 primary differences 独立复算；金额最大差额为 0，比例最大差额为 0。
- Source 表的 M3.5 字段保留、机械 growth、China-only differences、direction flags 和 nested-level inequality 均独立复算；最大差额为 0。
- Exposure 表的 numerator/denominator ratio 独立复算，最大浮点差额为 `2.22e-16`，小于 `1e-12`。
- TWN 在 time/source/exposure 表分别有 84/14/28 行，proxy flag 全部保留。
- 56/64/47 个 Stata aliases 均完整、唯一、不超过 32 字符，实际最长为 13/11/12。
- 三张 Parquet 在项目 F 盘临时目录第二次构建，SHA256 逐一完全一致；candidate 和 determinism 临时目录均已删除。
- `sensitivity_variables_constructed=true`、`ranking_variables_constructed=false` 在三张输出中对所有行成立；`.dta` 仍须等到 M7。

## 8. M4 production-side 标准化变量

目标文件：`production_validation_long.parquet`。采用长表保存来源、指标与单位；禁止把不同概念合并相加。

### 8.1 通用 long schema

| Canonical name | Stata name | 定义 |
|---|---|---|
| `country_iso3` | `country_iso3` | host/country |
| `analysis_sector` | `ana_sector` | 共同 sector |
| `year` | `year` | 年份 |
| `source_name` | `source` | icio/amne/bea_mne/bea_fdi/mexico_fdi |
| `metric_name` | `metric` | 指标名 |
| `value` | `value` | 原单位数值 |
| `unit` | `unit` | current USD/current million USD/thousand persons/fraction |
| `frequency` | `freq` | annual/quarterly/H1 |
| `direction` | `direction` | FDI inward/outward 或 affiliate trade direction |
| `parent_country_iso3` | `parent_iso3` | AMNE parent，适用时 |
| `direct_or_allocated` | `direct_alloc` | direct/allocated/unavailable |
| `suppressed_flag` | `suppressed` | BEA |
| `confidential_flag` | `confidentl` | Mexico |
| `aggregate_flag` | `is_agg` | geography/sector aggregate |
| `proxy_flag` | `is_proxy` | coarse source-sector proxy |
| `source_file` | `src_file` | provenance |

### 8.2 ICIO metrics

| Metric | Stata metric label | Unit | Additivity/use |
|---|---|---|---|
| `gross_output` | `gross_output` | current million USD | production level |
| `value_added` | `value_added` | current million USD | production validation；允许 accounting negatives |
| `exports` | `exports` | current million USD | source-consistent export level |
| `imports` | `imports` | current million USD | source-consistent import level |
| `intermediate_inputs` | `intermed_inputs` | current million USD | IO intensity |
| `taxes_less_subsidies` | `tax_less_sub` | current million USD | accounting；允许负值 |
| `accounting_residual` | `acct_resid` | current million USD | quality diagnostic |

ICIO 只有 2017、2018、2022。禁止线性插值得到 2019 或 annual panel。

### 8.3 AMNE metrics

| Metric | Unit | Direct/allocated | 用途 |
|---|---|---|---|
| `affiliate_output` | current million USD | direct bilateral | MP activity 主指标 |
| `affiliate_value_added` | current million USD | allocated to parent | production validation |
| `affiliate_exports` | current million USD | allocated | affiliate trade |
| `affiliate_imports` | current million USD | allocated | affiliate input |
| `foreign_affiliate_output_total` | current million USD | host-sector total | foreign activity scale |
| `parent_affiliate_output_share` | fraction | derived direct output share | allocation provenance |
| `affiliate_employment` | unavailable | unavailable | `PROHIBITED` as zero/imputed |

### 8.4 BEA MNE metrics

| Metric | Unit | 用途 |
|---|---|---|
| `employment` | thousand employees | labor validation |
| `sales` | million current USD | affiliate activity |
| `value_added` | million current USD | production |
| `capital_expenditures` | million current USD | investment/activity |
| `goods_exports_to_us` | million current USD | affiliate -> U.S. direction |
| `goods_imports_from_us` | million current USD | U.S. -> affiliate direction |

每个 metric 同时保留 suppression 和 small-value flag。aggregate geography 先排除。Transportation equipment 若作为 autos robustness，必须 `proxy_flag=1`。

### 8.5 BEA FDI metrics

| Metric | Temporal type | Unit | 规则 |
|---|---|---|---|
| `position` | stock | million current USD | 不跨年求和 |
| `flows` | annual flow | million current USD | 允许负 reversal |
| `income` | annual flow | million current USD | 与 position/flow 分开 |

必须保留 `direction`。不能构造 `total_fdi = position + flows + income`。

### 8.6 Mexico FDI metrics

| Metric | Stata name | 规则 |
|---|---|---|
| `fdi_quarterly_usd` | `fdi_q_usd` | quarterly flow，负值保留 |
| `fdi_annual_usd` | `fdi_a_usd` | 仅四季度完整且均非 confidential 时求和 |
| `fdi_h1_usd` | `fdi_h1_usd` | 2024 与历史 H1-to-H1 比较 |
| `fdi_complete_year_flag` | `fdi_yr_ok` | 2006-2023 full-year；2024 detail false |
| `fdi_confidential_quarter_count` | `fdi_conf_n` | confidential quarter count |
| `fdi_disclosed_composition_share` | `fdi_discsh` | 只描述 disclosed cells，不能解释为完整 national share |

Mexico national total 与 detailed composition 必须存为不同 source/metric，不能用 disclosed detail 替代全国 total。

## 9. M4-M5 production changes 和覆盖变量

对每个 source-metric 在其实际可用年份内构造变化，不能强迫所有来源使用同一连续窗口。

| Canonical name | Stata name | 公式/规则 |
|---|---|---|
| `value_level` | `value` | 原始 level |
| `value_lag` | `value_lag` | 同 source-country-sector-metric 上一期 |
| `value_change` | `d_value` | `value-value_lag` |
| `value_dh_growth` | `gdh_value` | 非负 level 适用；signed FDI 不使用 DH level formula |
| `value_log_growth` | `gln_value` | 两期均正时 |
| `signed_flow_change` | `d_flow` | signed FDI flow 的 level change |
| `post_pre_mean_change` | `d_postpre` | 在 source 可覆盖窗口内年度平均差 |
| `coverage_year_count` | `cover_yn` | 有效年份数 |
| `missing_value_count` | `miss_n` | missing 数 |
| `suppressed_value_count` | `supp_n` | suppressed 数 |
| `confidential_value_count` | `conf_n` | confidential 数 |

M5 coverage flags：

| Canonical name | Stata name |
|---|---|
| `has_trade` | `has_trade` |
| `has_icio` | `has_icio` |
| `has_amne` | `has_amne` |
| `has_bea_mne` | `has_beamne` |
| `has_bea_fdi` | `has_beafdi` |
| `has_mexico_fdi` | `has_mexfdi` |
| `has_any_production` | `has_prod` |
| `has_direct_activity_measure` | `has_direct` |
| `has_only_financial_evidence` | `fin_only` |
| `source_count_available` | `source_n` |

`has_only_financial_evidence=1` 的 cell 不能标为 production confirmed。

## 10. M6 connector ranking

### 10.1 组件

推荐先把 raw components 转为同一比较组内的 percentile rank `[0,1]`，减少单位和极端值影响，同时永久保留 raw variables。

| Component | Candidate raw inputs | 经济含义 |
|---|---|---|
| `score_exposure` | exposure overlap、sector tariff exposure | 是否集中在受冲击产品 |
| `score_us_gain` | connector-US level gain、DH growth | 对美出口扩张 |
| `score_source_gain` | China/East-Asia input gain、DH growth | source-to-connector link |
| `score_replacement` | China decline + connector gain、replacement ratio | U.S. import replacement |
| `score_comovement` | both/triple product share、weighted correlation | 两条贸易腿同步性 |
| `score_scale` | pre/post trade scale | 经济规模 |
| `score_stability` | positive-year share、negative volatility | 时间稳定性 |
| `score_production` | direct activity measures | 生产侧验证 |

### 10.2 至少两种排名方案

方案 A，推荐主结果：透明 equal-weight percentile score。

```text
rank_score_equal =
mean(score_exposure,
     score_us_gain,
     score_source_gain,
     score_replacement,
     score_comovement,
     score_scale,
     score_stability)
```

优点：透明、可复核、对单位不敏感。缺点：默认各维度同等重要。

方案 B，推荐稳健性：rerouting-core score，减少规模权重。

```text
rank_score_rerouting =
0.20 exposure
+ 0.20 us_gain
+ 0.20 source_gain
+ 0.20 comovement
+ 0.10 replacement
+ 0.05 scale
+ 0.05 stability
```

优点：更贴近两段式 rerouting 机制。缺点：权重含研究判断，必须报告替代权重。

production evidence 不建议直接混入主 trade ranking；更清楚的做法是先得到 trade ranking，再给出 `production_validation_grade`。如果合成总分，必须作为第三套扩展结果。

### 10.3 Ranking outputs

| Canonical name | Stata name | 状态 |
|---|---|---|
| `rank_score_equal` | `score_eq` | planned M6 |
| `rank_position_equal` | `rank_eq` | planned M6 |
| `rank_score_rerouting` | `score_rr` | planned M6 |
| `rank_position_rerouting` | `rank_rr` | planned M6 |
| `rank_top3_equal` | `top3_eq` | planned M6 |
| `rank_top3_rerouting` | `top3_rr` | planned M6 |
| `rank_stability_across_specs` | `rank_stab` | planned M6 |
| `rank_component_min` | `score_min` | planned robustness |
| `ranking_spec` | `rank_spec` | planned M6 |

所有 rank 必须在包含 core connectors 和 comparators 的完整共同样本上计算，不能先删掉低排名观察。

## 11. M6 rerouting facts 和 production validation

### 11.1 Rerouting classification

| Canonical name | Stata name | 定义 |
|---|---|---|
| `china_us_decline_flag` | `cnus_dropf` | China-US post < pre，且 level decline 达阈值 |
| `connector_us_gain_flag` | `conn_gainf` | connector-US post > pre |
| `source_input_gain_flag` | `src_gainf` | China/East Asia -> connector post > pre |
| `rerouting_two_leg_flag` | `rr_2leg` | connector gain + source input gain |
| `rerouting_three_condition_flag` | `rr_3cond` | China decline + connector gain + source input gain |
| `high_exposure_rerouting_flag` | `rr_hiexp` | triple condition + high exposure |
| `rerouting_evidence_grade` | `rr_grade` | none/weak/moderate/strong，规则写入 config |

Evidence grade 必须由预先固定的规则生成，不能根据结果手工改标签。

### 11.2 Production validation

| Canonical name | Stata name | 定义 |
|---|---|---|
| `output_growth_positive` | `out_pos` | ICIO/direct output change >0 |
| `value_added_growth_positive` | `va_pos` | VA change >0 |
| `affiliate_activity_growth_positive` | `aff_pos` | AMNE/BEA activity >0 |
| `employment_growth_positive` | `emp_pos` | available employment >0 |
| `capex_growth_positive` | `capex_pos` | BEA capex >0 |
| `fdi_flow_increase` | `fdi_pos` | signed flow change >0 |
| `direct_activity_signal_count` | `direct_n` | output/VA/affiliate/employment/capex positive count |
| `financial_signal_count` | `fin_n` | FDI flow/position/income signals |
| `production_confirmed_flag` | `prod_conf` | 至少一个 direct activity signal，不能只靠 FDI |
| `financial_support_only_flag` | `fin_supp` | 只有 financial evidence |
| `production_validation_grade` | `prod_grade` | none/financial-only/partial/multiple-source |

推荐 grade：

- `none`：无生产或金融支持；
- `financial_only`：只有 FDI；
- `partial_direct`：至少一个 direct activity metric 同向；
- `multiple_direct`：至少两个不同 source 或不同 direct activity families 同向；
- `conflicting`：trade 与 production signals 方向冲突。

## 12. Structural moments 和 Scenario A/B/C

必须区分“观测 moment”和“model shock/parameter”。数据不会直接观测 `hgamma`。

### 12.1 Trade-cost candidates

| Canonical name | Stata name | 公式 | 状态 |
|---|---|---|---|
| `gross_tariff_factor_hat` | `htau_gross` | `(1+tariff_rate_post)/(1+tariff_rate_pre)` | structural target only |
| `exposure_factor_hat` | `htau_expo` | `(1+exposure_post)/(1+exposure_pre)` | robustness candidate |
| `tariff_rate_change_pp` | `d_trf_pp` | `100*(rate_post-rate_pre)` | descriptive moment |
| `tariff_exposure_change_pp` | `d_exp_pp` | `100*(expo_post-expo_pre)` | descriptive moment |

最终 `h_tau` 选择必须与模型中 iceberg trade cost 或 tariff wedge 的定义一致，不能仅因为变量名相似就直接导入。

### 12.2 MP/production targets

| Moment | 观测来源 | 用途 |
|---|---|---|
| foreign affiliate output share change | AMNE | incumbent MP-intensive adjustment |
| affiliate output growth | AMNE | Scenario B target |
| affiliate sales/VA/employment/capex growth | BEA MNE | direct activity validation |
| gross output/value added growth | ICIO | broader production response |
| FDI position/flow change | BEA/Mexico | Scenario C financial upper-bound support |

Candidate names：

- `mp_affiliate_output_share_change` -> `d_affshr`
- `mp_affiliate_output_dh_growth` -> `gdh_affout`
- `bea_affiliate_activity_index` -> `bea_affidx`
- `production_activity_index` -> `prod_idx`
- `fdi_financial_index` -> `fdi_idx`

这些是 moments，不是 `hgamma` 本身。模型校准后才生成：

- `hgamma_scenario_b`
- `hgamma_scenario_c`

并必须记录 calibration mapping、normalization、elasticity、target source 和 solver result。

### 12.3 Structural moment table

目标字段：

| Field | 含义 |
|---|---|
| `moment_id` | 稳定唯一标识 |
| `scenario` | A/B/C |
| `country_iso3` | country/connector |
| `analysis_sector` | sector |
| `moment_name` | 名称 |
| `moment_value` | 数值 |
| `unit` | 单位 |
| `source_name` | 来源 |
| `sample_start`, `sample_end` | 样本期 |
| `formula_version` | 公式版本 |
| `direct_or_proxy` | direct/proxy/allocated/financial |
| `can_enter_model` | 是否允许进入模型 |
| `exclusion_reason` | 不允许时原因 |
| `validation_status` | PASS/FAIL |

## 13. Controls、fixed effects 和 robustness 变量

这些变量用于后续实证，不应与核心 outcome 混合。

| Family | Variables |
|---|---|
| time | year、post2018、post2020、pre/shock/post indicators |
| connector FE | connector_iso3 categorical |
| sector FE | analysis_sector categorical |
| baseline scale | log pre trade level only when positive；pre level raw |
| baseline China dependence | sector China share 2017 |
| baseline exposure | 2017/2018 sector exposure |
| proxy/scope | TWN proxy、BEA autos proxy、medical unsupported |
| coverage | has source flags、missing/suppression/confidential counts |
| small base | pre_zero、small_base、log_defined |
| alternative windows | M3.6 已构造：2014-2017 vs 2020-2024、2020-2023 exclude-2024、2018-2019 shock-only |
| source bloc | M3.6 已构造：China-only vs nested extended East Asia，KOR/TWN self-trade excluded |
| policy/exposure | M3.6 已构造四个非等价 estimands：tariff overlap、continuous weighted exposure、positive-exposure gain share、top-quartile-exposure gain share |

2024 可能同时受政策 review 和数据时间边界影响。所有包含 2024 的结果要有 exclude-2024 robustness。

## 14. 不允许的变量和解释

| 禁止项 | 原因 |
|---|---|
| 把 Census 15-origin 合计命名为 world imports | 分母范围错误 |
| 把 Census quantity zero 当真实数量 | source unavailable |
| 把 suppression/confidential missing 填 0 | 改变官方含义 |
| 把 BEA position + flow + income 相加 | stock/flow/概念不同 |
| 把 FDI increase 命名为 plant entry | financial evidence 不能证明实体进入 |
| 把 trade rerouting flag 命名为 production relocation | 缺少 direct production evidence |
| 把 allocated AMNE VA/exports/imports 称为直接 bilateral observations | 来源口径错误 |
| 把 repeated China-US benchmark 跨 connector 求和 | 机械重复 |
| 把 rate/share/exposure 直接求和到 sector | 应重算分子分母 |
| 给 many-to-many concordance 等权拆分且不披露 | 无经验依据且会伪精细 |
| 用 arbitrary epsilon 让 ratio/log 看似完整 | 隐藏 undefined denominator |
| 将 Scenario C 称为 structurally identified entry margin | 当前模型不是 endogenous fixed-cost entry model |

## 15. Stata 文件、主键和验证合同

### 15.1 计划交付

| DTA | Stata `isid` | 用途 |
|---|---|---|
| `m2_product_treatment.dta` | `isid hs6 year` | policy product panel |
| `m2_connector_trade.dta` | `isid conn_iso3 hs6 year` | product-level trade |
| `m3_trade_sector_year.dta` | `isid conn_iso3 ana_sector year` | sector-year trade |
| `m3_trade_sector_window.dta` | `isid conn_iso3 ana_sector window_id` | pre/shock/post |
| `m3_trade_sector_window_comparison.dta` | `isid conn_iso3 ana_sector` | pre/shock/post comparison and post-pre growth |
| `m3_trade_sector_growth_diagnostics.dta` | `isid conn_iso3 ana_sector flow_id` | small-base、异常增长和 winsorized sensitivity diagnostics |
| `m4_production_long.dta` | source-specific composite key | production evidence |
| `m5_connector_evidence.dta` | `isid conn_iso3 ana_sector year` | integrated interface |
| `m6_connector_ranking.dta` | `isid conn_iso3 ana_sector rank_spec` | ranking |
| `m6_structural_moments.dta` | `isid moment_id scenario` | model handoff |

### 15.2 Storage types

- monetary levels：`double`；
- rates/shares/growth：`double`；
- year：`int`；
- month/quarter/flags：`byte`；
- counts：按范围使用 `int` 或 `long`；
- ISO3：`str3`；
- HS6：`str6`；
- sector/source/status：固定上限字符串，不使用易丢信息的过短类型。

### 15.3 必须运行的 Stata 检查

```stata
version 18
clear all
set more off

use "data/processed/stata/m3_trade_sector_year.dta", clear
describe
isid conn_iso3 ana_sector year
assert inrange(year, 2014, 2024)
assert cn_us_val >= 0 if !missing(cn_us_val)
assert cn_conn_val >= 0 if !missing(cn_conn_val)
assert ea_conn_val >= 0 if !missing(ea_conn_val)
assert conn_us_val >= 0 if !missing(conn_us_val)
assert inrange(sec_expo, 0, 1) if !missing(sec_expo)
assert qty_ok == 0 if !missing(qty_ok)

count
summarize cn_us_val cn_conn_val ea_conn_val conn_us_val sec_expo
display "DATA_HANDOFF_VALIDATION_SUCCESS"
```

最终 `.do` 要逐表检查 rows、keys、ranges、missing counts、totals 和 success marker，并把 log 写入项目 F 盘。

## 16. 每个变量完成后的登记模板

```text
Canonical name:
Stata name:
Status:
Output file:
Grain and key:
Source fields:
Formula:
Window:
Unit:
Additivity:
Zero rule:
Missing rule:
Negative-value rule:
Suppression/confidentiality rule:
Denominator rule:
Small-base rule:
Winsorization/standardization:
Purpose:
Allowed interpretation:
Prohibited interpretation:
Validation checks:
Validation result:
Output hash:
Reviewer/date:
```

## 17. 当前施工顺序

1. M3.1 已构造 connector-sector-year levels、coverage 和 sector treatment；
2. M3.1 product-to-sector value reconciliation 与确定性检查已通过；
3. M3.2 已构造 complete-window annual means、coverage/policy summaries、post-pre change、DH/log growth 和 mechanical zero/defined flags；
4. M3.3 已固定并构造 zero/small-base、异常增长和 winsorized sensitivity diagnostics，raw levels/growth 全部保留；
5. M3.4 已构造 replacement、source input、exposure overlap 和 HS6 co-movement，三张自然粒度输出 validation PASS；
6. M3.5 已在共同面板中保留全部 13 个 connectors/comparators × 7 sectors，并明确不做 outcome/top-rank/complete-case 筛选；
7. M3.6 已生成窗口、source bloc 和 exposure sensitivity 三张自然粒度接口，未构造 ranking；
8. 下一步 M4 逐来源建立 production long，须等待用户确认；
9. M5 逐来源 left join 和 coverage；
10. M6 先 trade ranking，再 production grade，最后 structural moments；
11. M7 导出 Stata、运行 `.do`、冻结 release。

## 18. 版本记录

| Version | Date | Change |
|---|---|---|
| v0.1.0 | 2026-07-27 | 建立 M2 已验证变量、M3-M6 planned variables、公式、用途、缺失规则、排名方案、structural moment 边界和 Stata handoff 合同。 |
| v0.1.1 | 2026-07-27 | 与完整数据处理审计档案建立双向合同；规定 M3-M7 每步必须同步登记实际输出、validation、hash 和 Stata 接口。 |
| v0.2.0 | 2026-07-28 | 完成 M3.1 变量合同：登记 1,001 行 connector-sector-year 输出、70 个 canonical/Stata aliases、实际公式、flow-specific coverage、17/11 个 treatment denominator 异常、non-additive flags、validation 和确定性输出 hash；M3.2-M3.6 保持 planned。 |
| v0.3.0 | 2026-07-28 | 完成 M3.2 变量合同：登记 273 × 79 long window 和 91 × 142 comparison 两表接口、complete 4/2/5-year annual means、ratio-of-sums coverage、policy summaries、post-pre change/DH/log growth、zero/defined flags、17/11 denominator 异常、79/142 个 Stata aliases、两张确定性输出 hash 和 M3.3 边界。 |
| v0.4.0 | 2026-07-28 | 完成 M3.3 变量合同：登记 364 × 64 flow-level diagnostics、USD 25 million absolute threshold、sector-flow nearest-rank p10、China→USA relative-threshold exception、robust-z/MAD 与 mechanical extreme flags、flow-level p5/p95 winsorized sensitivity、64 个 Stata aliases、异常计数和确定性 output hash。 |
| v0.5.0 | 2026-07-28 | 完成 M3.4 变量合同：登记 55,081 × 56 产品窗口、91 × 92 部门重组指标和 91 × 49 产品共变三表接口；固定 USD 25 million replacement denominator、signed numerator、China/East Asia source ratios、28 个 exposure missing、positive/p75 exposure overlap、产品正增量分母、Pearson/weighted correlations、56/92/49 aliases 和三个确定性 hashes。 |
| v0.6.0 | 2026-07-28 | 完成 M3.5 变量合同：登记 91 × 152 共同面板、M3.4 两张同粒度表的 one-to-one join、完整 13 × 7 网格、21/49/21 组别行数、角色/稳定排序/source-match/no-selection flags、26/65 replacement defined/missing 状态、152 aliases 和确定性 output hash。 |
| v0.7.0 | 2026-07-29 | 完成 M3.6 变量合同：登记 1,092 × 56 alternative-window、182 × 64 source-bloc 和 364 × 47 exposure-definition 三表接口；固定 primary/exclude-2024/shock-only、nested China/East-Asia self-trade rule、四种非等价 exposure estimands、annual stability/primary-difference 状态、56/64/47 aliases、独立复算和三个确定性 hashes；明确不构造 ranking。 |

下一次强制更新：M4.1 ICIO production-side 标准化长表完成时，补齐 source-sector join、变量公式、suppression/accounting 状态、输出 hash、validation 和 Stata 接口；同时更新审计档案并重建两份 PDF。
