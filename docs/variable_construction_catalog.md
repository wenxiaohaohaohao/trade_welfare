# Connector Economies 变量构造目录与使用指南

## Material Passport

- Origin Skill: `stata-latex-research`
- Origin Date: `2026-07-27`
- Verification Status: `VERIFIED_THROUGH_M3.1`
- Version Label: `variable_catalog_v0.2.0`
- Current Data Stage: `M0-M3.1 completed`
- Next Construction Stage: `M3.2 not started`
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

- `EXISTING_VALIDATED`：M2 或 M3.1 已存在且 validation PASS；
- `PLANNED_M3` 至 `PLANNED_M6`：已经定义但尚未构造，必须在对应阶段完成后补充实际 output hash 和 validation；
- `STRUCTURAL_TARGET_ONLY`：只能作为模型校准目标或输入候选，不能直接解释为已经识别的结构参数。

凡是本目录未登记的正式变量，不应直接写入最终 processed data。临时探索变量可以存在于 `tmp/` 或交互式 Stata session，但进入正式输出前必须补齐本目录。

本目录与 `docs/data_processing_audit_trail.md` 构成同一套审查材料。本目录不重复数据来源和完整处理历史，而是引用审计档案中的输入、输出和 validation 证据；审计档案也不能替代这里的变量级公式、用途和解释边界。M3-M7 任一阶段完成时，两份 Markdown、两份 PDF 和对应 build summary 必须同步更新。

## 1. 状态、粒度和可加总性代码

### 1.1 状态

| 状态 | 含义 |
|---|---|
| `EXISTING_VALIDATED` | 已在 processed Parquet 中存在，主键和 validation 已通过 |
| `PLANNED_M3` | M3.2-M3.6 的窗口、增长、replacement 和 ranking inputs 尚未构造 |
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
| `window_id` | `window_id` | str8 | window | pre/shock/post | planned M3 |
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

不同窗口长度不相等：pre 4 年、shock 2 年、post 5 年。因此 level comparison 使用年度平均值，不使用窗口总和。

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

每条贸易腿构造：

| Family | Pre level | Shock level | Post level | Level change | DH growth | Positive-base log growth |
|---|---|---|---|---|---|---|
| China -> USA | `cnus_pre` | `cnus_shk` | `cnus_post` | `d_cnus` | `gdh_cnus` | `gln_cnus` |
| China -> connector | `cncn_pre` | `cncn_shk` | `cncn_post` | `d_cncn` | `gdh_cncn` | `gln_cncn` |
| East Asia -> connector | `eacn_pre` | `eacn_shk` | `eacn_post` | `d_eacn` | `gdh_eacn` | `gln_eacn` |
| connector -> USA | `cnusx_pre` | `cnusx_shk` | `cnusx_post` | `d_cnusx` | `gdh_cnusx` | `gln_cnusx` |

Stata 名称必须在生成前再次检查不超过 32 characters，并在 variable labels 写出完整方向。

### 6.1 zero 和 small-base flags

| Canonical name | Stata name | 定义 | 用途 |
|---|---|---|---|
| `pre_zero_flag` | `pre_zero` | pre annual mean = 0 | 区分新贸易与连续增长 |
| `post_zero_flag` | `post_zero` | post annual mean = 0 | 区分退出 |
| `small_base_flag` | `smallbase` | pre level 低于 M3 config 明确阈值 | 防止 ratio/rank 爆炸 |
| `log_growth_defined` | `logg_ok` | pre>0 and post>0 | log sample |
| `years_observed_pre` | `pre_yn` | pre 窗口实际 years | coverage |
| `years_observed_post` | `post_yn` | post 窗口实际 years | coverage |

small-base threshold 必须写入 M3 config，至少报告：

- absolute USD threshold；
- sector-relative percentile threshold；
- 不使用 threshold、只用 DH growth 的结果。

推荐主排名使用 level change + DH growth，不依赖单一百分比增长。

## 7. M3.3-M3.6 贸易重组和排名输入变量

### 7.1 Import replacement

```text
china_us_decline = max(cnus_pre - cnus_post, 0)
connector_us_gain = cnusx_post - cnusx_pre
replacement_ratio = connector_us_gain / china_us_decline
```

`replacement_ratio` 只有在 `china_us_decline` 大于明确的 denominator threshold 时定义；否则 missing。主结果同时保留 level gain 和 decline，不能只报告 ratio。

| Canonical name | Stata name | 用途 | 状态 |
|---|---|---|---|
| `china_us_decline_usd` | `cnus_drop` | China displacement level | planned M3 |
| `connector_us_gain_usd` | `conn_gain` | connector gain level | planned M3 |
| `replacement_ratio` | `repl_ratio` | connector gain 相对 China decline | planned M3 |
| `replacement_ratio_defined` | `repl_ok` | denominator 是否可用 | planned M3 |
| `replacement_capped_for_rank` | `repl_cap` | 仅 ranking 的 winsorized/capped version | planned M3 |

### 7.2 Source-to-connector input growth

| Canonical name | Stata name | 定义 |
|---|---|---|
| `china_input_gain_usd` | `cnin_gain` | China -> connector post-pre level change |
| `east_asia_input_gain_usd` | `eain_gain` | East Asia -> connector post-pre level change |
| `china_input_dh_growth` | `gdh_cnin` | China input DH growth |
| `east_asia_input_dh_growth` | `gdh_eain` | East Asia input DH growth |
| `source_export_ratio_pre` | `srcx_pre` | source-to-connector / connector-to-USA，pre |
| `source_export_ratio_post` | `srcx_post` | 同一 ratio，post |
| `source_export_ratio_change` | `d_srcx` | post-pre |

ratio denominator 为 0 时保持 missing；不能用 arbitrary epsilon 生成正式值。若 ranking 需要 finite score，先用 percentile of level/growth components，而不是偷偷给 ratio 加常数。

### 7.3 Product-level co-movement

在 connector-sector 内先对每个 HS6 计算 pre/post changes，再聚合：

| Canonical name | Stata name | 公式/用途 |
|---|---|---|
| `both_legs_positive_product_share` | `both_psh` | China/East Asia input gain >0 且 connector-US gain >0 的 HS6 share |
| `both_legs_positive_value_share` | `both_vsh` | 上述产品按 pre/post trade value 加权 share |
| `china_decline_connector_gain_share` | `rerout_psh` | China-US decline 且 connector-US gain 的 product share |
| `triple_condition_product_share` | `triple_psh` | China-US decline、source input gain、connector-US gain 同时成立 |
| `product_change_correlation` | `prod_corr` | source-input change 与 connector-export change 的 HS6 correlation |
| `weighted_product_change_correlation` | `wprod_cor` | 以 pre China-US 或 connector trade weights 加权 |

相关系数至少要求有效 products 达到 config 中的 minimum count；否则 missing + `corr_low_n_flag=1`。

### 7.4 Exposure overlap

| Canonical name | Stata name | 公式 |
|---|---|---|
| `connector_export_tariff_overlap_pre` | `ovlp_pre` | pre connector-US exports 中 tariffed/exposed product 的 value share |
| `connector_export_tariff_overlap_post` | `ovlp_post` | post share |
| `connector_export_exposure_weighted` | `ovlp_expo` | connector export weights 下的 product tariff exposure |
| `gain_in_high_exposure_products_share` | `gain_hiexp` | export gain 来自 high-exposure products 的份额 |

“high exposure” threshold 必须在 config 中固定，例如 top quartile 或 positive exposure；两种定义均应报告。

### 7.5 稳定性和规模

| Canonical name | Stata name | 用途 |
|---|---|---|
| `pre_trade_scale_usd` | `scale_pre` | 排名时防止只由小基数增长驱动 |
| `post_trade_scale_usd` | `scale_post` | 经济规模 |
| `annual_growth_sd` | `growth_sd` | 年度增长波动 |
| `positive_growth_year_share` | `posyr_sh` | post 期间正增长年份比例 |
| `rank_window_sensitivity` | `rank_sens` | 替代窗口下 rank 变化 |
| `source_bloc_sensitivity` | `bloc_sens` | China-only 与 East-Asia source 定义差异 |
| `exposure_definition_sensitivity` | `expo_sens` | rate/exposure/tariffed share 差异 |

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
| alternative windows | 2014-2017 vs 2020-2023；exclude 2024；shock-only |
| source bloc | China-only vs extended East Asia |
| policy | rate vs exposure vs tariffed share |

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
3. 下一步 M3.2 构造 window annual means；
4. M3.3 固定 zero/small-base/growth rules；
5. M3.4 构造 replacement、source input、exposure overlap 和 co-movement；
6. M3.5 保留所有 connectors/comparators；
7. M3.6 生成窗口、source bloc 和 exposure sensitivity；
8. M4 逐来源建立 production long；
9. M5 逐来源 left join 和 coverage；
10. M6 先 trade ranking，再 production grade，最后 structural moments；
11. M7 导出 Stata、运行 `.do`、冻结 release。

## 18. 版本记录

| Version | Date | Change |
|---|---|---|
| v0.1.0 | 2026-07-27 | 建立 M2 已验证变量、M3-M6 planned variables、公式、用途、缺失规则、排名方案、structural moment 边界和 Stata handoff 合同。 |
| v0.1.1 | 2026-07-27 | 与完整数据处理审计档案建立双向合同；规定 M3-M7 每步必须同步登记实际输出、validation、hash 和 Stata 接口。 |
| v0.2.0 | 2026-07-28 | 完成 M3.1 变量合同：登记 1,001 行 connector-sector-year 输出、70 个 canonical/Stata aliases、实际公式、flow-specific coverage、17/11 个 treatment denominator 异常、non-additive flags、validation 和确定性输出 hash；M3.2-M3.6 保持 planned。 |

下一次强制更新：M3.2 完成时，补齐窗口年度均值、窗口覆盖、缺失规则和实际 output/validation/hash；同时更新审计档案并重建两份 PDF。
