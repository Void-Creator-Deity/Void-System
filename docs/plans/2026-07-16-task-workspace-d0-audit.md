# Phase D0：行动工作台调用与迁移审计

- 日期：2026-07-16
- 状态：SUPERSEDED（历史审计；2026-07-18 后不再作为运行合同）
- 范围：行动工作台、规划页、canonical Task Execution / Task Automation、legacy task 兼容路由
- 原则：本审计不改变运行时行为

## 1. 用户入口

| 入口 | 当前职责 | 写入目标 | D1-D5 处理 |
| --- | --- | --- | --- |
| `/tasks` | 目标、执行记录、步骤、确认、调整要求、定时启动 | canonical Goal / Run / Trigger / Run Command | 保留为唯一行动工作台，补齐计划子流程、成果和复盘 |
| `/advisor` | 生成并编辑 Goal draft + Run specification | `/api/plans`、`/api/goals`、`/api/goals/{id}/runs` | 保留兼容路由，作为工作台的规划子流程；发布后回到具体 Run |
| 系统精灵建议 | 跳转到目标或执行 | 目前主要读取 | 继续链接 canonical Goal / Run，不创造任务类型 |

## 2. 前端写入审计

### Canonical 写入

- `goalsApi`：创建和更新 Goal。
- `plansApi`：生成可审核的 Goal draft + Run specification。
- `runsApi`：创建 Run，控制 Run / Step 生命周期，处理 Approval，提交 Run Command。
- `triggersApi`：创建、编辑、暂停、恢复和删除 Trigger。

### Legacy 写入

代码搜索未发现当前行动工作台或规划页调用以下接口：

- `POST /api/tasks`
- `PUT /api/tasks/{task_id}/progress`
- `DELETE /api/tasks/{task_id}`
- `POST /api/task-chains`
- `DELETE /api/task-chains/{chain_id}`
- 旧 automatic-task 写入

结论：前端主流程已经完成 canonical 写入切换。后续工作的重点是用户旅程、失败恢复、成果和复盘，不再重复迁移接口。

## 3. 后端契约矩阵

| 领域 | 现有 Interface | 当前能力 | 缺口 |
| --- | --- | --- | --- |
| Goal | `/api/goals` | 创建、列表、详情、更新状态和内容 | 创建与首次 Run 发布尚无统一草案/恢复标识 |
| Plan | `POST /api/plans` | 生成 Goal draft + Run specification | 前端历史只在 localStorage；发布状态不可恢复 |
| Run | `/api/goals/{goal_id}/runs`、`/api/runs/*` | 创建、开始、暂停、继续、取消、详情、事件 | 需要面向用户的发布幂等和复盘读模型 |
| Step | `/api/runs/{run_id}/steps/*` | 开始、完成、跳过、失败、重试 | 完成表单没有友好的成果输入；前端未展示 output_data |
| Artifact | Step 完成请求 + Run 详情读取 | 文本/文件/链接元数据持久化，owner-scoped | 缺少聚合后的成果展示和交付物完整性提示 |
| Approval | 请求与处理接口 | durable pending/approved/rejected | UI 需要展示影响、详情和已处理历史 |
| Event | `GET /api/runs/{run_id}/events` | append-only 时间线 | 需要翻译为用户可读事件，不暴露内部枚举 |
| Run Command | `/api/runs/{run_id}/commands` | durable instruction + acknowledgement | UI 文案需统一为“调整要求”，区分待采纳和已采纳 |
| Trigger | `/api/triggers` | schedule/event、幂等 firing、生命周期 | UI 文案仍是“自动安排/自动执行”，需改为条件启动 |
| Review / Evaluation | legacy task workflow 为主 | proof、self/AI evaluation、reward settlement | canonical Run 尚无完整 Review Interface 与读模型 |
| Reward | legacy completion 和 marketplace settlement | 原子结算能力存在 | canonical Run 复盘尚未直接暴露结算结果 |

## 4. Legacy 兼容面

后端仍保留：

- `api/http/routers/task_workspace.py`：legacy task / task-chain CRUD 与进度写入。
- `api/http/routers/tasks.py`：legacy status、proof、evaluation 与 AI evaluation。
- `adapters/sqlite/task_execution_projection.py`：把 legacy 写入投影为 canonical Goal / Run / Step / Event / Approval。
- migration 10/11/12：历史投影、奖励关联和 Trigger / Run Command。

处理决定：D5 前不删除路由、表或投影。新行为不得加入 legacy Module；数据库删除必须另立 ADR。

## 5. 已确认风险

1. 计划发布分为创建 Goal、创建 Run、开始 Run 三次请求；中途失败会留下半发布 Goal。
2. Advisor 使用基于当前时间的 Run 幂等键，重试发布不能稳定复用同一 Run。
3. 计划历史只存 localStorage，无法表达“草案、Goal 已创建、Run 已创建、已开始”等发布状态。
4. Run 已返回 artifacts、approvals、steps.output_data，但工作台基本没有成果聚合和最终复盘。
5. 评价和奖励仍依赖 legacy task identity；不能在前端凭 completed 状态猜测结算结果。
6. “自动安排”“自动执行”“mode/kind”仍有实现导向文案，需要翻译成用户意图。
7. `/advisor` 和 `/tasks` 是两个平行页面，用户完成规划后只能回到列表，不能直接落到刚创建的 Run。

## 6. 冻结规则

从 D1 开始执行以下规则：

1. 新任务写入只允许 canonical clients。
2. legacy task/task-chain 前端写入保持为零。
3. 不删除 legacy 表、路由或历史数据。
4. 不在页面临时计算评价、奖励或伪造复盘结论。
5. 每个子阶段完成后更新统一规划、测试证据与回退点。
6. LM Studio 只用于 D6 最终可选集成测试。

## 7. D1 输入

D1 以此审计为依据收口页面职责：

- `/tasks` 是唯一行动工作台。
- `/advisor` 是可兼容访问的规划子流程。
- 主旅程固定为：目标 -> 计划草案 -> 确认 -> 执行 -> 成果 -> 复盘。
- Trigger 是“何时启动”；Run Command 是“调整要求”；mode/kind 只留在传输契约中。

## 8. 风险关闭与最终状态

| D0 风险 | 最终处理 |
| --- | --- |
| Goal / Run / start 分段发布可能留下半成品 | 草稿保存稳定 Goal 与 Run 幂等键，按阶段恢复，已经创建的资源不会重复创建 |
| Run 幂等键依赖当前时间 | 改为由稳定草稿身份生成并持久化，刷新和重试保持一致 |
| 计划历史只有 localStorage | 草稿保留阶段状态和 canonical 资源标识；失效资源只复位对应阶段 |
| 成果与步骤产出没有面向用户的聚合 | canonical Run Review 汇总 Artifact、output、Approval、Reward 与完成条件；工作台提供成果完整性提示和复盘 |
| 评价与奖励依赖 legacy identity | canonical 复盘读取后端结算事实，不在前端按 completed 状态猜测奖励 |
| 页面暴露 mode、kind、command、automatic 等术语 | 普通用户界面统一为“自己完成 / 和系统一起 / 交给系统”“成果”“调整要求”“启动条件”；内部值只保留在合同与管理界面 |
| /advisor 与 /tasks 平行 | /tasks?view=plan 成为唯一规划入口；/advisor 仅作兼容跳转 |

最终搜索确认前端主流程不调用 legacy task / task-chain 写入。旧路由、表和投影继续作为兼容面存在，删除策略仍需独立 ADR；新功能不得回写旧模型。完整闭环已在真实浏览器验证，后端 175/175、前端 10/10、生产构建均通过。


## 9. 后续替代说明

2026-07-18 的迁移已经完成历史 task/task-chain 数据校验与一次性转换，并删除旧运行路由、Repository、投影层和数据库表。本文件第 4、6、8 节中“继续保留兼容面”的内容只描述 2026-07-16 当时的阶段决策。当前实现与后续工作必须遵守根目录 `DESIGN.md`、`PROJECT_RULES.md`、`CONTEXT.md` 和现行 OpenAPI，不得恢复旧运行时。
