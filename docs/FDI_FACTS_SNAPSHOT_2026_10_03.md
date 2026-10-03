# fDi facts 阶段快照：2026-10-03

现有数据支持的描述性 facts 已形成可供讨论、可核对的阶段版本。当前优先固定这套结果，选择最有解释力的核心比较，并完成 MP 可观测量到模型对象的对应；不再以增加一般性图表作为阶段目标。

这一判断不等于 JIE Gate 2、Gate 3 或福利量化已经完成。研究合同记录在数据权威历史 `c46c671:docs/JIE_PROJECT_GOAL.md`，该文件不在当前 `facts` 工作分支中。本快照不合并另一条数据处理分支，也不是完整项目或 M7 数据交付。

## 阅读入口

优先阅读 [完整中文图表说明](../output/fdi_facts_reader_2026_10_03/index.html) 或 [Markdown 正文](../output/fdi_facts_reader_2026_10_03/FACTS_READER.md)。每组采用“表格 → 图表 → Notes → 文字解释”，共 9 张表、6 组图：年度数量与来源份额、四组来源构成、项目类型、母公司历史、月份与缺失，以及 MP 经营指标附录。

## 当前完成边界

| 内容 | 本次状态 | 保留的边界 |
|---|---|---|
| fDi 描述性基线 | 已完成 2014—2022 年分阶段整理、图表与独立复算 | 项目记录不是企业数量、实际产出或福利 |
| 后两年探索 | 已纳入当前交付的 2023—2024 年全部 Manufacturing 记录及统一 1—9 月比较 | 覆盖仍待供应商确认；墨西哥中国来源份额方向随月份窗口改变 |
| 类型与母公司历史 | 类型数量、份额、正向历史匹配及其分母均已说明 | 2024 年没有类型和母公司字段；New 不等于企业首次进入 |
| MP 准备 | 已整理 AMNE、BEA、ICIO 的候选指标，并选出美国母公司—墨西哥—机械试点 | `next_test_ready=false`；尚未估计 hgamma、弹性或福利 |
| 论文核心联合事实 | 原有 F01—F04 已做共同国家—部门与时间窗口比较 | 可比贸易条件下的生产差异及聚合联系的企业解释仍需收紧，不能宣布 Gate 2 通过 |

原有 F01—F04 已使用 72 个非 proxy 国家—部门单元和 2014—2017 对 2020—2023 年窗口，本轮无需从头重做全部对齐。其 F02 的基期外资份额差中位数为 11.63 个百分点、留一国家预测 R² 为 −0.223，说明条件可比性和预测关系仍弱；F04 的既有联系是聚合联系，不能直接解释为在位企业。原有 stylized-facts 文件属于此前独立工作，保持本地原状，不包括在本次提交中。

剩余实质工作限制为三项：从已有结果中确定核心联合比较；完成一个小型 MP 测量与模型对应；供应商补数后复核会改变结论的 fDi 单元。详细疫情识别放在后续经验设计阶段，不作为本次描述性成果固定的前置条件。

## 本次版本控制范围

- `code/analysis/fdi_facts/`：fDi 构建、绘图、文字整理和验证脚本。
- `code/analysis/mp_pilot_prepare_2026_10_03.py`：已有经营数据的候选目标准备。
- `output/fdi_facts_2026_10_02/`：原描述性基线的聚合表、图、报告及审核记录。
- `output/fdi_research_baseline_2026_10_03/`：分阶段与 2024 年探索结果，保留聚合产物。
- `output/fdi_facts_reader_2026_10_03/`：本次主要阅读版本及 9 张显示表、6 份绘图数据。
- `output/mp_pilot_prepare_2026_10_03/`：可观测指标、分母、行业对应和披露检查。
- `output/audits/fdi_markets_2026_10_02/`：不包含企业逐行例子的聚合审核记录。

原始 Excel、三个企业/项目逐行派生表、企业明细形式的重复诊断及日志不提交；本地文件保留。具体名单写入项目 `.gitignore`。历史审核报告可能引用这些本地文件及其哈希，这不表示这些文件随 Git 分发。

本次快照只保存相关代码、聚合数据和可阅读产物。既有 `README.md`、`AGENTS.md`、导师材料、原 stylized-facts 材料等其他工作区修改未纳入。此文是本次 fDi 状态入口；历史 README 的“fDi 尚未处理”描述不适用于这个新增快照。

## 从已提交的聚合结果重建读者报告

在项目根目录执行，报告生成与读者报告独立验证只依赖 Python 标准库。以下命令使用已提交聚合表，不需要原始商业工作簿或企业逐行明细：

```powershell
python code/analysis/fdi_facts/build_reader_report.py
python code/analysis/fdi_facts/validate_reader_report.py
```

需要重新画图时，先运行以下命令，再生成和验证报告。绘图需要 `matplotlib` 及 Microsoft YaHei 字体。更换绘图环境后，应重新查看中文、排版并更新视觉审核，不把历史人工审核自动视为本次通过。

```powershell
python code/analysis/fdi_facts/plot_reader_facts.py
python code/analysis/fdi_facts/build_reader_report.py
python code/analysis/fdi_facts/validate_reader_report.py
```

`index.html` 已内嵌六张 PNG，直接打开即可阅读；同目录 CSV、SVG、PDF 提供表格与图形下载。输出目录设置 `-text` Git 属性，保留原文件字节，避免 Windows 自动转换换行符导致审核 SHA-256 失配。

## 完整源数据复算的额外依赖

完整 fDi 复算须自行提供有使用权限的 `data/raw/fDi_Markets .xlsx`（文件名含空格），且哈希应与审核记录相符。它还依赖本地既有 F03/F04 文件：首版构建用它们保护既有结果，MP 准备使用其聚合指标进行核对。相关脚本使用 `openpyxl`、`pandas`、`numpy`；图形使用 `matplotlib`，PDF 视觉检查使用 Python PDF 库。

首版构建所需的本地 F03/F04 文件为两个 `fact.json`、`F03/parent_contributions.csv` 和 `F04/country_components.csv`。已有输入满足条件后，先运行 `build_fdi_facts.py` 生成本地逐行派生表，再运行 `build_staged_fdi.py`；`build_exploratory_fdi_2024.py` 读取原始 Excel 两个工作表。对应数值检查分别由 `validate_fdi_facts.py`、`validate_staged_fdi.py`、`validate_exploratory_fdi.py` 完成。完整验证可能需要这些不随 Git 分发的本地逐行产物。

MP 准备另外需要 harmonized AMNE/BEA/ICIO parquet、行业 crosswalk、既有 moment bank、F03/F04 汇总及 ICIO 模型接口数据。精确输入与哈希见 [MP manifest](../output/mp_pilot_prepare_2026_10_03/MANIFEST.json)。这些大表及其权威数据处理实现不随本次提交加入；只有已提交聚合结果的报告重建是当前快照独立支持的复现层级。

供应商更新文件后，先重新核对 schema、年份、来源覆盖、类型、标识及原始文件哈希，再建立新快照。当前脚本锁定了审核输入，不应仅更换哈希绕过审核。

原始工作簿的首次审计在本次归档中作为冻结审核记录保留；其早期生成器及逐行缓存位于本地临时目录，不随本次快照分发，也不宣称已经提供从零重建该早期审计的入口。

## 验证证据

- [读者报告独立审核](../output/fdi_facts_reader_2026_10_03/READER_INDEPENDENT_REVIEW.json)：1,054 项检查通过，9 表、6 份图形数据与来源一致，HTML/Markdown 和嵌入图像一致。
- [2024 年探索结果独立审核](../output/fdi_research_baseline_2026_10_03/EXPLORATORY_INDEPENDENT_REVIEW.json)：17,016 项字段/数值检查通过，所有原始行保留。
- [图形审核](../output/fdi_facts_reader_2026_10_03/FIGURE_VALIDATION.json)及[网页视觉检查](../output/fdi_facts_reader_2026_10_03/READER_VISUAL_REVIEW.json)。
- [MP 指标准备审核](../output/mp_pilot_prepare_2026_10_03/VALIDATION.json)：750 项检查通过；数值审核不替代识别或模型口径对应。
