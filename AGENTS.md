# Codex 项目规则

## 数据目录安全规则

在本项目中，`raw/`、`archive/`、`legacy/` 和 `_staging*` 目录默认视为可能有用、可能正在被其他程序使用、或可能属于用户正在运行的数据任务。

不能因为目录名称包含 `staging`、`半成品`、`tmp`、`partial`，或者看起来不完整、临时、陈旧，就删除、移动、覆盖或清理该目录。

在提出或执行任何删除、移动、覆盖、清理数据目录的操作前，Codex 必须先核实并向用户报告：

- 是否有相关进程正在运行；
- 文件是否仍在持续写入，或最近刚被修改；
- 该目录是否明确由当前 Codex 任务创建；
- 是否存在 summary、manifest、lock file、completion marker；
- 该目录是否可能属于用户或其他程序正在使用的数据任务。

如果目录不是当前 Codex 任务明确创建的，Codex 不得修改该目录。只能列出路径、说明风险和建议，并等待用户用精确路径明确确认。

这条规则尤其适用于 Census staging 和输出路径，包括：

- `data/raw/us_census/`
- `data/raw/us_census/_staging_us_census_full`
- `data/interim/trade/_staging_us_census_full`
- `data/interim/trade/us_imports_*.parquet`
