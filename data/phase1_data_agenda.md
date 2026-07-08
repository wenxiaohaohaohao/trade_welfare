# Phase 1 Data Agenda

## Purpose

第一阶段只判断数据事实是否足够支撑后续 JIE 版本的模型迁移。该阶段的工作边界是经验事实构造、数据验证和结构矩约束整理，不进入完整模型、不跑福利反事实、不写论文正文。

## Completion Rule

五个任务全部完成并打勾后，第一阶段 data 工作即结束。除非另有明确决定，不继续扩展新任务。

## Phase 1 Checklist

- [ ] 1. 构造 connector ranking：判断哪些国家-部门最像 connector。
- [ ] 2. 构造 rerouting facts：判断中国 -> connector 与 connector -> 美国是否同步上升。
- [ ] 3. 构造 production-side validation：判断 connector 是否有增加值、产出、FDI、MNE 活动增长。
- [ ] 4. 构造 structural moment table：整理哪些经验事实可以约束 `h_tau` 和 `h_gamma`。
- [ ] 5. 判断是否进入模型迁移：评估数据是否足够支撑 JIE 版本。

## Task Definitions

| Task | Core question | Main output | Completion evidence |
|---|---|---|---|
| Connector ranking | 哪些国家-部门在 exposed flows 中最像第三方 connector？ | Country-sector connector ranking table | 排名指标、样本窗口、国家-部门口径、稳健性定义已记录。 |
| Rerouting facts | 中国 -> connector 与 connector -> 美国是否在同一国家-部门上同步上升？ | Rerouting fact table or figure | 至少给出前后期变化、同步性指标、主要 connector 的方向性证据。 |
| Production-side validation | connector 的贸易增长是否对应真实生产或跨国生产活动增长？ | Production-side validation table | 增加值、产出、FDI、MNE/AMNE 或 BEA evidence 中至少一种可用，并说明缺口。 |
| Structural moment table | 哪些事实约束 trade-cost channel，哪些事实约束 MP/production channel？ | Structural moment table | 每个 moment 标明数据来源、经济含义、对应 `h_tau` 或 `h_gamma`、是否可进入模型输入。 |
| Model migration decision | 数据是否足以进入 JIE 版本模型迁移？ | Go / no-go decision memo | 明确给出进入、暂缓或停止模型迁移的理由。 |

## Scope Exclusions

第一阶段不做以下工作：

- 不迁移完整 MATLAB 模型。
- 不估计完整结构模型。
- 不跑 welfare counterfactual。
- 不写论文正文。
- 不把 FDI、fDi Markets 或 MNE extensive-margin evidence 直接解释为模型内生 entry equation。

## Decision Standard

只有同时满足以下条件，才进入模型迁移：

1. connector ranking 在合理暴露定义下基本稳定。
2. rerouting facts 显示中国 -> connector 与 connector -> 美国在关键国家-部门上同步上升。
3. production-side validation 说明 connector 不是单纯转口或统计重标记。
4. structural moment table 能清楚区分约束 `h_tau` 的 trade rerouting facts 与约束 `h_gamma` 的 production / MP facts。
5. 数据口径、国家-部门映射、样本窗口和缺失值处理足够透明，可以转换为后续模型输入。

若以上任一条件失败，第一阶段结论应是暂缓或停止模型迁移，而不是继续扩大模型任务。
