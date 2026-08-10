# M4.6 跨来源 production evidence long validation

- Validation status: **PASS**
- Checks: **137/137 PASS**
- Full registry: `data/processed/harmonized/production_validation_long.parquet`，113,302 × 83，SHA256 `4b27154fe00c75b44f23724f7940799363be4212b72c83757a5a389111a6c69a`
- Main host activity: `data/processed/harmonized/production_validation_main_host_sector_year_long.parquet`，73,368 × 83，SHA256 `2ca54343f0d5bef9c42532a1c79c0d4864f32764f35f4d5a7751170b6c44a27d`

## 设计结论

完整 registry 一对一保留六张 M4.1-M4.5 analysis/financial/benchmark 输入。严格 main 表只保留 ICIO、AMNE 与 BEA MNE main-sector 的 host-country activity rows。BEA FDI、Mexico FDI 与 autos proxy 继续存在于 registry，但不会进入 main host activity 表。

物理主键为 `source_table, source_observation_id`。旧的 `country_iso3, analysis_sector, year, source_name, metric_name` 只对严格 main host activity 子集唯一，不能识别 BEA FDI direction、Mexico parent 或 period。

## 核验快照

| 项目 | 结果 |
|---|---:|
| 完整 registry 行数 | 113,302 |
| 严格 main host activity 行数 | 73,368 |
| value 可用行 | 96,186 |
| value 缺失行 | 17,116 |
| suppressed 行 | 4,604 |
| confidential 行 | 12,344 |
| observed negative 行 | 1,224 |
| numeric zero 行 | 18,886 |
| proxy 行 | 3,807 |
| financial-only 行 | 37,552 |
| 国家数（main union） | 87 |
| sector 数（main union） | 6 |

## 使用边界

- `join_role` 明确区分 host main、host proxy、origin-country financial、country-year benchmark 和 source-native-only。
- BEA FDI inward 的 `country_iso3` 是 foreign investor origin；Mexico parent 的 `country_iso3` 是 reported parent origin。两者均不能当作当地 production。
- `suppressed_flag` 与 `confidential_flag` 分列保存；`suppressed_or_confidential_flag` 仅为便捷标记。所有 17,116 个缺失值均保留为缺失，未补零。
- 所有行 `can_sum_across_source_records=false`；不同 source、metric、unit、period type 不得相加。
- M4.6 未构造 growth、ranking、production grade、structural moments、welfare inputs 或 `.dta`。

## Determinism

- Full registry second-build hash match: **True**
- Main host activity second-build hash match: **True**
- Task-owned temporary directories cleaned: **True**
