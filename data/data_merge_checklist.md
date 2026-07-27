# 数据合并与变量构造执行清单

## Material Passport

- Origin Skill: `academic-research-suite/experiment-agent`
- Origin Mode: `plan`
- Origin Date: `2026-07-19`
- Verification Status: `ANALYZED`（M0-M2 validation 均为 PASS；M3-M7 待执行）
- Version Label: `data_merge_plan_v1`
- Working Branch: `data-processing-variables`

## 目标与当前状态

目标是把已经验证的 source-specific `data/interim/` 数据，转化为可审计、可重复生成的 `data/processed/` 合并数据，并在此基础上构造 connector ranking、rerouting facts、production-side validation 和 structural moments。

当前阶段：`M0-M2 已完成并验证；M3.1 尚未开始`。

勾选规则：只有代码、输出、validation 和说明文件同时完成，任务才从 `[ ]` 改为 `[x]`。部分完成、仅生成文件、仅跑通代码或仍有未解释的 many-to-many join，都不能打勾。

正式指导材料：

- `docs/data_processing_audit_trail.md`：记录从 source/raw/interim 到 processed 的完整处理链、输入输出、主键、异常、验证和版本。
- `docs/variable_construction_catalog.md`：逐项登记变量的粒度、公式、单位、用途、允许解释、禁止解释、缺失/负值/suppression 规则及 Stata 交付合同。
- `output/pdf/data_processing_audit_trail.pdf` 和 `output/pdf/variable_construction_catalog.pdf`：交给合作者审查的固定版 PDF。

审计与变量合同规则：从 M3.1 开始，每完成一个 checklist 项目，必须在同一工作批次内同时更新上述两份 Markdown。审计档案要补充阶段记录、输出注册表、异常/决策日志和版本记录；变量目录要把本阶段变量从 `PLANNED_*` 更新为已构造状态，并补齐实际输出、公式实现、validation 和 hash。两份 PDF 及其 build summary 也必须重建并完成视觉检查。任一项未同步时，该 checklist 项目不得打勾。

## 不可违反的合并规则

1. `data/raw/`、`archive/`、`legacy/` 和 `_staging*` 保持只读，不移动、不覆盖、不清理。
2. `data/interim/` 继续保留 source-specific 口径；所有跨库合并结果写入 `data/processed/`。
3. 下载与 raw-to-interim 脚本继续放在 `code/data_build/`；新的 interim-to-processed 合并与变量构造代码放在 `code/data_processing/`。
4. 不直接生成一个包含全部来源的“超级宽表”。先按研究粒度分别建立产品冲击表、connector trade 表和 production-side 表，最后只在明确主键上合并。
5. 任何 many-to-many concordance 必须有显式权重；权重在每个 source code 内加总为 1，并报告未映射率和贸易额覆盖率。
6. BEA suppression、Mexico `C`、AMNE allocated fields 和其他缺失值不能改成 0；必须保留原始 flag 和处理规则。
7. Section 301 只解释为 gross statutory exposure；Mexico/BEA FDI 只解释为 financial-flow/position evidence，不能直接解释为 plant entry 或 production relocation。
8. 大型中间文件、日志和缓存全部留在本项目 F 盘目录，不写入 C 盘。

## 为什么不能把所有数据一次性直接 merge

核心数据具有四种不同粒度：

| 数据块 | 原始粒度 | 主要合并用途 |
|---|---|---|
| BACI、Census、Section 301 | product × country/flow × time | 产品冲击、两段式贸易流和 connector ranking |
| OECD ICIO | country × OECD sector × year | gross output、value added 和 IO baseline |
| OECD AMNE、BEA MNE | parent/host × sector/industry × year | foreign-affiliate activity 和 MP validation |
| BEA FDI、Mexico FDI | country × industry/sector × year/quarter | 金融投资变化的外部验证 |

如果直接横向拼接，会把产品层贸易额重复到每个 production/FDI cell，产生机械性重复和错误总量。正确做法是先统一维度和口径，在各自自然粒度上聚合，再建立 country-sector-year 层的研究接口。

## 目标数据结构

| 层 | 计划输出 | 唯一主键 | 用途 |
|---|---|---|---|
| Concordance | `data/processed/concordances/country_crosswalk.parquet` | `source_name, source_country_id` | 统一 ISO3、aggregate 和特殊地区标记 |
| Concordance | `data/processed/concordances/product_sector_crosswalk.parquet` | `analysis_hs6` | HS2012/CEPII 产品到唯一 `analysis_sector`，并独立保留 BEC end-use 与歧义状态 |
| Concordance | `data/processed/concordances/source_sector_crosswalk.parquet` | `source_name, source_sector_level, source_sector_code` | OECD、BEA、SCIAN 到共同 sector 口径；歧义和汇总层级不赋伪权重 |
| Product treatment | `data/processed/harmonized/product_treatment_hs6_year.parquet` | `analysis_hs6, year` | Section 301 暴露和产品处理状态 |
| Connector trade | `data/processed/harmonized/connector_trade_hs6_year.parquet` | `connector_iso3, analysis_hs6, year` | China→connector 与 connector→USA 两条贸易腿 |
| Trade-sector | `data/processed/harmonized/connector_trade_sector_year.parquet` | `connector_iso3, analysis_sector, year` | ranking 和 rerouting facts 的共同贸易面板 |
| Production-side | `data/processed/harmonized/production_validation_long.parquet` | `country_iso3, analysis_sector, year, source_name, metric_name` | 产出、增加值、affiliate activity、employment、capex、FDI 等长表 |
| Integrated evidence | `data/processed/harmonized/connector_evidence_country_sector_year.parquet` | `connector_iso3, analysis_sector, year` | 贸易与生产侧证据的最终研究接口 |
| Moments | `data/processed/moments/structural_moments.parquet` | `moment_id, scenario` | `h_tau`、`h_gamma` 和 Scenario A/B/C 输入 |
| Stata handoff | `data/processed/stata/*.dta` | 与对应 canonical Parquet 相同 | 合作者后续实证分析；配套变量字典和验证 `.do` 文件 |

最终使用两层 sector 口径：

- `model_sector`：尽量保持 OECD ICIO 50-sector 接口，用于后续结构模型。
- `analysis_sector`：用于跨 BACI、AMNE、BEA 和 Mexico FDI 的共同经验口径。第一版优先保留 electronics、electrical equipment、machinery、autos、medical devices、textiles/apparel 和 other manufacturing。

采用两层口径的原因是：如果强行以最粗的 BEA 16/20 industry 作为唯一口径，会损失产品暴露信息；如果强行以 OECD 50 sectors 作为所有来源口径，则 BEA 和 SCIAN 会产生不可辩护的伪精细映射。

## 执行 Checklist

### M0. 输入冻结与接口审计

- [x] M0.1 核心公开数据下载阶段结束，并确认国家统计补充数据不属于当前完成条件。
- [x] M0.2 核对八个核心 Parquet 的实际行数、字段和自然粒度：BACI、Census HS6、Section 301、ICIO、AMNE、BEA MNE、BEA FDI、Mexico country-sector FDI。
- [x] M0.3 生成 input manifest，记录路径、文件大小、SHA256、行数、schema、数据版本、时间覆盖和生成脚本。
- [x] M0.4 对每个输入执行主键唯一性、字段类型、非负值、缺失值、aggregate rows、suppression/confidentiality 和单位检查。
- [x] M0.5 固定第一版分析样本：核心 connector、比较组、priority sectors、pre/shock/post 时段和结构基准年份。

完成门槛：形成机器可读 manifest 和 Markdown validation report；所有异常都有“修复、保留并解释、或排除”的明确处理决定。

### M1. 建立统一维度和 concordance

- [x] M1.1 建立 country master：ISO3、source-specific country labels、BACI 特殊代码、BEA area type、Mexico residual/total flags。
- [x] M1.2 标记并隔离 World、Total、Other、International organizations、地区合计等 aggregate geography，禁止它们与国家行重复加总。
- [x] M1.3 建立时间规则：月度 Census 保留月度表并按年求和；季度 Mexico FDI flow 按年求和；stock/position 不做错误的期间加总。
- [x] M1.4 建立 HS revision bridge，明确 BACI HS2012、Section 301/BACI HS2017 和逐年 Census HTS/HS6 的版本关系。
- [x] M1.5 建立 HS-to-sector 映射，并为 intermediate/final-use 分类保留独立字段，避免把 sector 与 BEC 用途混为一谈。
- [x] M1.6 建立 OECD ICIO 50-sector、OECD AMNE sector、BEA MNE industry、BEA FDI industry 和 Mexico SCIAN 到 `analysis_sector` 的映射。
- [x] M1.7 对每张 concordance 验证唯一性、many-to-many 权重和未映射记录。
- [x] M1.8 生成 concordance coverage report，至少报告“代码覆盖率、贸易额覆盖率、生产值覆盖率、FDI 值覆盖率”。

完成门槛：所有 source code 都有明确状态；核心结果的映射值覆盖率原则上不低于 95%，低于 95% 时必须单独解释并获得继续执行的理由；任何映射权重都不能导致总量膨胀。

### M2. 构造产品冲击与贸易合并底表

- [x] M2.1 将 Section 301 HS2017 exposure 映射到统一 `analysis_hs6`，保留原始 list、rate、China share 和 mapping provenance。
- [x] M2.2 从 BACI 构造 China→USA、China/East Asia→connector、connector→USA 三类年度产品流量。
- [x] M2.3 将 Section 301 treatment 与 BACI 产品流合并，验证 join cardinality 和合并前后贸易总额守恒。
- [x] M2.4 将 Census HS6 月度数据作为美国进口时点验证，生成年度表但同时保留月度事件研究接口。
- [x] M2.5 明确 Census 15-origin scope；不把它当作 all-origin denominator。
- [x] M2.6 将 2024 review exact HTS 表保持为独立扩展，不在没有正式 modern-HTS concordance 时强行并入历史主面板。

完成门槛：生成 `product_treatment_hs6_year.parquet` 和 `connector_trade_hs6_year.parquet`；主键无重复；合并前后总额差异可解释；未映射值及其占比完整报告。

### M3. 聚合到 connector-country-sector-year 贸易面板

- [ ] M3.1 使用带权 product-sector concordance 将产品流量聚合到 `analysis_sector`。
- [ ] M3.2 构造 pre `2014–2017`、shock `2018–2019`、post `2020–2024` 的 levels、changes、growth 和 shares。
- [ ] M3.3 对极小基期、零贸易和异常增长率建立统一规则；同时保留 level change，避免只靠百分比增长排名。
- [ ] M3.4 构造四类基础指标：U.S. import replacement、connector export growth、source-to-connector input growth、Section 301 exposure overlap。
- [ ] M3.5 对 MEX、VNM、CAN 与 comparators 生成共同面板，不只保留排名靠前的观察。
- [ ] M3.6 验证不同暴露定义、source bloc 和时间窗口下的结果敏感性。

完成门槛：生成 `connector_trade_sector_year.parquet`；每个 key 唯一；所有排名变量有公式、单位、样本和缺失处理说明。

### M4. 构造 production-side 标准化长表

- [ ] M4.1 ICIO：保留 country-sector-year 的 gross output、value added、exports、imports 和 accounting residual 信息。
- [ ] M4.2 AMNE：保留 parent-host-sector-year 明细，同时构造 host-sector foreign-affiliate totals；allocated variables 必须标记。
- [ ] M4.3 BEA MNE：先过滤 aggregate geographies，再映射 country 和 industry；保留 employment、sales、value added、capex、affiliate trade 及 suppression flags。
- [ ] M4.4 BEA FDI：分别保留 outward/inward direction、position、flows 和 income；stock、flow 和 income 不混为同一指标。
- [ ] M4.5 Mexico FDI：季度 flow 按年求和；保留 parent-country、SCIAN sector、confidential 和 total/residual flags。
- [ ] M4.6 把各来源转换为统一 long schema：`country, sector, year, source, metric, value, unit, direct_or_allocated, suppressed_or_confidential`。
- [ ] M4.7 不人为补齐 ICIO 缺失年份；ICIO 仅在 2017、2018、2022 作为可观察 benchmark，其他来源保留各自覆盖期。

完成门槛：生成 `production_validation_long.parquet`；所有值都能回溯到 source file；missing、suppressed、confidential 和 allocated 状态不会在聚合中丢失。

### M5. 合并贸易与生产侧证据

- [ ] M5.1 在 `connector_iso3 × analysis_sector × year` 主键上建立 trade master。
- [ ] M5.2 以 left join 方式逐个加入 ICIO、AMNE、BEA MNE、BEA FDI 和 Mexico FDI 标准化指标，并记录每一步 matched/unmatched 数量。
- [ ] M5.3 生产侧来源以 metric/source 后缀或 long format 保持可区分，禁止把 output、affiliate sales 和 FDI flow 相加。
- [ ] M5.4 建立 coverage flags：哪些 country-sector-year 有 trade、ICIO、AMNE、BEA 和 Mexico evidence。
- [ ] M5.5 对合并前后各来源总量、行数和唯一键执行 reconciliation。

完成门槛：生成 `connector_evidence_country_sector_year.parquet`；不存在意外 many-to-many expansion；每个来源的覆盖缺口和适用年份都可见。

### M6. 变量构造与第一阶段五项研究任务

- [ ] M6.1 Connector ranking：综合 exposure overlap、两条贸易腿、规模、同步性和稳定性；至少报告两种权重方案。
- [ ] M6.2 Rerouting facts：检验 China→connector 与 connector→USA 是否在相同 country-sector 上同步上升，并与 China→USA 下降对应。
- [ ] M6.3 Production-side validation：检查 gross output、value added、affiliate activity、employment、capex 或 FDI 是否与贸易增长同向；FDI 单独标为金融证据。
- [ ] M6.4 Structural moment table：每个 moment 写清来源、公式、样本、单位、对应 `h_tau` 或 `h_gamma`、Scenario A/B/C 和能否进入模型输入。
- [ ] M6.5 Model migration decision：依据 ranking 稳定性、rerouting、production evidence、moment 可用性和口径透明度形成 go/pause/no-go 结论。

完成门槛：上述五项与 `data/phase1_data_agenda.md` 一一对应；只有对应交付物和 validation 均完成时，才在两份 checklist 中同步打勾。

### M7. 全流程复现、版本冻结与交付

- [ ] M7.1 提供单一入口脚本，按 M0→M6 顺序运行，并在失败时停止，不继续生成下游结果。
- [ ] M7.2 为每个输出生成 build summary：输入 hash、输出 hash、行数、主键、覆盖期、missing/suppression 和 validation 状态。
- [ ] M7.3 在小样本上建立确定性测试；在完整数据上验证重复运行得到一致 schema、行数和核心统计量。
- [ ] M7.4 更新 `data/processed/README.md`、`docs/data_source_log.md` 和 `docs/variable_construction_catalog.md`。
- [ ] M7.5 固定第一版 processed-data release，记录 Git commit 和数据 manifest。
- [ ] M7.6 为每张最终分析表导出 Stata-compatible `.dta`；变量名不超过 32 字符，并核对 storage type、Unicode、日期、变量标签和值标签。
- [ ] M7.7 编写 Stata handoff 验证入口 `.do`：逐表 `use`、`describe`、`isid`、关键 `assert`、行数与数值汇总核对，并在日志中写入明确 success marker。
- [ ] M7.8 提供合作者交付说明：主数据、主键、单位、样本、缺失/保密规则、变量字典、推荐 merge 顺序和可直接运行的 Stata 入口。
- [ ] M7.9 将 `docs/data_processing_audit_trail.md` 和 `docs/variable_construction_catalog.md` 更新为最终 `VERIFIED` 版本，重建两份 PDF，并由 full-rebuild output hashes、Stata validation log 和 release manifest 支持最终签字。

完成门槛：从既有 `data/interim/` 能完整重建全部 `data/processed/` 交付；没有依赖 C 盘临时文件；没有修改 raw/archive/legacy/staging 内容。

## 推荐执行顺序及原因

1. **先完成 M0。** 输入未冻结时开始 merge，会在上游文件变化后无法解释结果差异。
2. **再完成 M1。** 国家、产品、行业和时间映射是所有下游合并的共同约束；先做排名、后补 concordance 会造成反复返工。
3. **先做 M2–M3 的贸易面板。** BACI、Section 301 和 Census 的识别链最直接，也能尽早判断 connector ranking 是否存在基本信号。
4. **再做 M4–M5 的生产侧合并。** 生产、affiliate activity 和 FDI 的定义差异更大，必须在贸易事实明确后逐源加入，不能用 FDI 替代生产指标。
5. **最后做 M6。** 变量和 structural moments 必须由经过验证的合并底表生成，不能在原始来源上临时计算。
6. **M7 是强制门槛。** 没有可重复构建和版本记录的数据结果，不进入模型迁移。

## 下一项工作

下一项唯一在做任务是 `M3.1：把 product-level trade/treatment 聚合到 analysis_sector`。M2 已全部完成：product treatment 为 57,222 行，connector trade 为 743,886 行，所有自然键重复为 0，贸易腿及 treatment merge 前后总额差均为 0；Census 月度/年度四个金额字段核对差为 0，排除 98/99 后可比进口值覆盖率为 99.997284%；2024 review 的 367 条 HTS8/HTS10 记录保持独立且无 `analysis_hs6`。M3.1 完成并验证前不构造 ranking。
