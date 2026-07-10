# BEA U.S. MNE Mexico Transportation Equipment Data Check, 2020-2022

## 核心结论

BEA `Activities of U.S. Multinational Enterprises` 中的 `Majority-Owned Foreign Affiliates` country-by-industry 表可以直接用于核实 `Mexico x Transportation equipment` 的美国 MNE 子公司活动。2020、2021、2022 三年在核心指标上均为数值，未出现 `(D)` suppression。

因此，`Mexico x Transportation equipment` 这条线可用于补 OECD Analytical AMNE 2020 年之后的缺口，并可作为校准关税冲击后 Scenario B incumbent MP-intensive reallocation 的 production-side moment；若与 fDi Markets、Mexico FDI 或其他生产扩张证据合并，也可支持 Scenario C total MP-adjustment upper-bound proxy。

## 核实日期与数据来源

- 核实日期：2026-07-01
- 数据提供方：U.S. Bureau of Economic Analysis (BEA)
- 数据主题：Activities of U.S. Multinational Enterprises (MNEs)
- 统计对象：Majority-owned foreign affiliates (MOFAs) of U.S. MNEs
- 地理口径：host country of affiliate = Mexico
- 行业口径：industry of affiliate = Transportation equipment
- 年份：2020、2021、2022
- 表覆盖：BEA downloadable country-by-industry tables, 2009-2023

官方入口：

- BEA MNE data page: https://www.bea.gov/data/intl-trade-investment/activities-us-multinational-enterprises-mnes
- BEA USDIA / U.S. MNE downloadable tables: https://www.bea.gov/international/di1usdop

逐表下载链接：

| BEA table | URL | Unit |
|---|---|---|
| Employment by Country and Industry 2009-2023 | https://www.bea.gov/sites/default/files/2025-08/mofas-employment.xls | Thousands of employees |
| Value Added by Country and Industry 2009-2023 | https://www.bea.gov/sites/default/files/2025-08/mofas-value-added.xls | Millions of dollars |
| Expenditures for Property, Plant, and Equipment by Country and Industry 2009-2023 | https://www.bea.gov/sites/default/files/2025-08/mofas-cap-expend.xls | Millions of dollars |
| Sales by Country and Industry 2009-2023 | https://www.bea.gov/sites/default/files/2025-08/mofas-sales.xls | Millions of dollars |
| Assets by Country and Industry 2009-2023 | https://www.bea.gov/sites/default/files/2025-08/mofas-assets.xls | Millions of dollars |

## BEA suppression 标记

BEA Excel `Notes` sheet 对 `(D)` 的定义为：

> D Suppressed to avoid disclosure of data of individual companies.

也就是说，`(D)` 不是普通缺失，而是为了保护个别公司数据而做的 disclosure suppression。若目标 country-industry-year 单元格为 `(D)`，该指标不能直接作为连续时间序列使用。

## 读取路径

BEA 的 2009-2023 country-by-industry Excel 不是把年份放在列中，而是每个年份一个 worksheet。读取方式如下：

1. 打开对应指标的 Excel 文件。
2. 选择 `2020`、`2021`、`2022` worksheet。
3. 在每个 worksheet 中定位 `Mexico` 行。
4. 读取 `Transportation equipment` 列。
5. 检查单元格是否为数值或 `(D)`。

在这些表中，`Transportation equipment` 是 `Manufacturing` 下的 `Of which` 行业列。将它用于汽车链条时，应注意它不是 BEA 更细的 `Motor vehicles` 专项口径，而是更宽的 transportation equipment aggregate。

## Mexico x Transportation Equipment 核实结果

| Indicator | Unit | 2020 | 2021 | 2022 | 2020-2022 change | Suppressed? |
|---|---:|---:|---:|---:|---:|---|
| Assets | Millions of dollars | 38,964 | 49,526 | 59,242 | +20,278 (+52.0%) | No |
| Employment | Thousands of employees | 353.8 | 364.3 | 406.4 | +52.6 (+14.9%) | No |
| Value added | Millions of dollars | 8,247 | 11,000 | 12,588 | +4,341 (+52.6%) | No |
| Expenditures for property, plant, and equipment | Millions of dollars | 1,556 | 2,454 | 3,400 | +1,844 (+118.5%) | No |
| Sales | Millions of dollars | 65,192 | 81,052 | 95,617 | +30,425 (+46.7%) | No |

### 对项目的含义

这些指标共同支持一个清楚结论：BEA 的 `Mexico x Transportation equipment` 行业级 U.S. MNE affiliate 线在 2020-2022 年没有 disclosure suppression，可以作为生产侧验证和结构模型校准输入。

最直接可用的 moment 是 assets stock：

- 2020：38.964 billion USD
- 2022：59.242 billion USD
- 2020-2022 增量：20.278 billion USD
- 2020-2022 增幅：52.0%

这条资产存量序列可以用于补 OECD Analytical AMNE 2020 年之后的缺口，也可以和 employment、value added、PPE expenditures、sales 一起构造 robustness checks。

## 相关行业边界检查

本次同时检查了两个相邻行业，用来判断 BEA country-by-industry 表是否能扩展到其他 Mexico connector sectors。

### Mexico x Computers and electronic products

| Indicator | Unit | 2020 | 2021 | 2022 | Suppressed? |
|---|---:|---:|---:|---:|---|
| Assets | Millions of dollars | 3,343 | 3,793 | 4,348 | No |
| Employment | Thousands of employees | 73.8 | 73.4 | 79.9 | No |
| Value added | Millions of dollars | 1,754 | 1,653 | 1,978 | No |
| Expenditures for property, plant, and equipment | Millions of dollars | `(D)` | `(D)` | `(D)` | Yes |
| Sales | Millions of dollars | 3,604 | 4,081 | 4,672 | No |

结论：`Computers and electronic products` 可用于 assets、employment、value added、sales，但不能用 PPE expenditures 作为 2020-2022 连续序列。

### Medical equipment and supplies

在上述 BEA 2009-2023 MOFA country-by-industry time-series 表中，没有单独的 `Medical equipment and supplies` 行业列。2022 comprehensive balance sheet Part II B 表中也未找到该细项。

结论：不能把 `Transportation equipment` 的可用性结论推广到医疗器械。若要核实医疗器械，需要另查 BEA 更细行业表、direct investment country-industry 表，或使用其他来源。

## 使用建议

1. 在 `production-side validation table` 中，把 `Mexico x Transportation equipment` 作为 North America extension 的优先 production-side evidence。
2. 结构模型中若需要 post-2020 Scenario B moment，优先使用 assets stock，并用 employment、value added、PPE expenditures、sales 做一致性检查；如果用于 Scenario C，必须同时说明它只是上界 proxy 的一个支持证据，不是 firm-level entry 证据。
3. 不应把这组 aggregate MOFA 数据解释为 firm-level relocation 证据。它能说明美国 MNE 在墨西哥该行业的 affiliate activity 扩张，但不能直接证明某一家企业把产能从中国迁到墨西哥。
4. 做 sector concordance 时，应把 BEA `Transportation equipment` 明确映射到项目模型的 transportation equipment / motor vehicles 相关部门，并在代码或 mapping 表中保留这个口径说明。

## 可重复归档与核查入口

- 下载和抽取脚本：`code/data_build/download_extract_bea_mne_mofas.py`
- 脚本依赖：`code/data_build/requirements-bea-mne.txt`
- 本地原始 XLS 归档目录：`data/raw/bea_usdia_mofas_2025-08/`，该目录被 git 忽略。
- 原始文件 checksum manifest：`data/bea_usdia_mofas_2025_08_archive_manifest.md`
- Mexico 2020-2022 suppression audit summary：`data/bea_mne_mofas_mexico_suppression_audit_2020_2022.md`
- 机器可读 audit CSV：`data/interim/bea_mne_mofas_mexico_suppression_audit_2020_2022.csv`，该文件被 git 忽略，可由脚本重建。
