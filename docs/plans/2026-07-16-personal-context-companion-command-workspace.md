# 下一阶段设计：个人上下文、系统精灵与命令式行动工作台

- 状态：Phase A-E 已完成并通过最终交付审计
- 日期：2026-07-16
- 当前基线：后端完整测试 175/175 通过；前端测试 10/10 通过；Vite production build 与桌面端、390px 浏览器闭环验收通过

## 1. 目标

把虚空系统从“多个功能页面的集合”升级为一个可迁移的个人成长 Workspace Core：

1. 系统能理解用户，但每条理解都有来源、置信度和用户控制权。
2. 长期记忆能区分事实、偏好、经历与推断，不把一次行为永久固化。
3. 上下文按目的和预算组装，可解释本次读取了什么、为什么读取。
4. 任务以 Goal -> Plan -> Run -> Evidence -> Review 形成闭环，不再暴露旧的单任务、任务链、自动任务三套模型。
5. 前端使用自然语言和直接操作呈现能力，不向普通用户暴露 provider、RAG、chain、数据库字段等实现术语。

## 2. 非目标

本轮不做以下事情：

- 不重新发明另一套任务持久化；继续使用已经完成的 Goal / Run / Step / Command 核心。
- 不让 LLM 直接写入“最终画像”。模型只能生成候选推断，最终有效画像由规则、证据和用户覆盖共同决定。
- 不在本轮接入所有外部平台。先定义可移植的 Observation Adapter 接口，再逐个平台实现。
- 不让系统精灵默认读取全部数据。知识库和奖励数据继续默认关闭。

## 3. 统一领域模型

### 3.1 画像链路

`Observation -> Claim -> User Override -> Effective Profile`

- **Observation**：收藏、反馈、任务完成、对话确认、资料导入等可追溯行为证据。Observation 本身不是人格结论。
- **Claim**：由一条或多条 Observation 支持的候选认知，带领域、置信度、证据引用、首次/最近观察时间和审核状态。
- **User Override**：用户明确确认、修正或否定的内容，独立保存，优先级高于系统推断。
- **Effective Profile**：读取时合并原始候选与用户覆盖得到的有效视图；保留 raw/effective 双视图，避免用户看不到系统原始判断或覆盖发生漂移。

画像按非临床层次组织：

- 基本事实
- 兴趣与回避
- 工作和学习方式
- 沟通偏好
- 价值倾向与驱动力
- 当前阶段

兴趣、作品、收藏标签只能作为证据层，不能直接堆成性格描述；不输出 MBTI、病理标签或临床判断。

### 3.2 长期记忆

保留四种记忆类型：

- `fact`：稳定事实
- `preference`：可变化的偏好
- `episode`：带时间的经历
- `inference`：系统推断，必须带置信度和证据

每条记忆必须支持：来源、证据引用、置信度、是否参与上下文、状态、更新时间、用户确认/否定。归档是默认删除方式，永久删除需要显式操作。

### 3.3 上下文工程

上下文不是“把数据库内容全部塞给模型”，而是一个可审计的 Context Compiler：

1. 调用方声明 purpose、允许的 section 和预算。
2. 权限层过滤不可访问数据。
3. 各模块通过公开 Interface 提供候选项，系统精灵不直接查询其他模块数据表。
4. 选择器按相关性、时效性、置信度、敏感度和多样性分配预算。
5. 输出携带 provenance、freshness、sensitivity、reference 和 truncation。
6. 每次读取写入 access audit，用户可在前端查看。

默认允许：profile、goals、runs、growth、memories。
默认关闭：knowledge、rewards。

### 3.4 行动命令模型

现有 Task Execution 是唯一执行真相：

`Goal -> Run -> Step graph -> Action/Event/Artifact/Approval`

前端与系统精灵使用五个用户命令入口，不新增五套后端架构：

- **目标**：创建或澄清 Goal。
- **规划**：调用 Planning Engine 生成可审阅 Run 草稿。
- **执行**：批准并启动 Run，Step 可串行、并行、重试或等待批准。
- **调整**：通过 durable Run Command 向进行中的 Run 补充要求。
- **复盘**：汇总 Evidence/Artifact，评估结果并结算成长与奖励。

旧的“单任务 / 任务链 / 自动任务”只作为兼容展示：

- 单任务 = 一个 Step 的 Run
- 任务链 = Step 依赖图
- 自动任务 = Trigger 创建的 agent-mode Run

## 4. Module 与 Interface

### Personal Context Module

负责权限、记忆语义、画像合并、上下文编译和访问审计。

公开 Interface：

- settings
- memories
- profile view
- context snapshot
- briefing
- access log

### Profile Evidence Adapter

外部平台收藏、点赞、浏览、导入文件等只通过 Adapter 写入标准 Observation。Adapter 不直接修改 Claim 或有效画像。

### Task Execution / Planning / Growth / Knowledge

继续作为独立深 Module。Personal Context 只调用它们的公开 Interface，不依赖 SQLite 表或具体模型供应商。

## 5. 前端信息架构

新增“系统精灵”工作台，第一屏直接提供可用能力：

- 今日简报和当前重点
- 继续执行 / 开始规划 / 创建目标等建议动作
- 画像认知：已确认、待确认、已否定
- 长期记忆：新增、编辑、归档、忘记
- 数据权限：按 profile/goals/runs/growth/memories/knowledge/rewards 开关
- 本次使用了什么：来源、更新时间、敏感度和访问记录

视觉方向：安静、精炼、工作区式。使用中性灰白底，绿色表示已确认/完成，蓝色表示行动，琥珀色表示待确认；不使用 AI 光球、紫色渐变、嵌套卡片或开发者控制台式表单。

## 6. 实施顺序

### Phase A：后端基线与 Personal Context

- [x] companion settings、权限与暂停状态
- [x] 分类长期记忆 CRUD
- [x] budgeted context snapshot 与 access audit
- [x] deterministic briefing
- [x] 数据库 migration 13
- [x] 后端完整回归测试通过

### Phase B：画像证据与有效视图

- [x] 定义 Observation / Claim / Override contract
- [x] 添加 migration 14 与 owner-scoped 持久化
- [x] 实现 raw/effective profile 合并规则
- [x] 实现确认、修正、否定、恢复与可逆覆盖
- [x] 将长期记忆转为首批可追溯证据源
- [x] 添加 HTTP 接口与回归测试

### Phase C：系统精灵前端

- [x] companion API client
- [x] briefing、focus、suggestions
- [x] profile cognition review
- [x] memory management
- [x] permissions and access explanation
- [x] route、desktop/mobile navigation
- [x] 桌面端与移动端真实登录验收

### Phase D：行动工作台闭环重构

本阶段只改行动工作流及其直接依赖，不同时扩展知识库、商店、画像 Adapter 或模型推理。后端继续以 Task Execution 和 Task Automation 为唯一执行真相；前端不再创造“单任务 / 任务链 / 自动任务”三套产品概念。

#### D0：现状审计与冻结写入范围

- [x] 列出行动工作台、规划页及导航中所有任务相关读取和写入。
- [x] 标记 `/api/tasks`、`/api/task-chains`、旧 automatic-task 接口的调用者；确认新代码不得增加这些写入。
- [x] 记录 Goal、Plan、Run、Step、Artifact、Approval、Event、Run Command、Trigger 的现有 HTTP 契约和缺口。
- [x] 建立迁移审计表：每个旧入口对应到 Goal / Run / Step / Trigger 的展示或兼容策略。

验收：得到可检索的调用清单，能够证明后续新增写入只经过 `/api/goals`、`/api/plans`、`/api/runs`、`/api/triggers` 及其子资源。

回退点：D0 仅产出审计记录，不改变运行时行为。

#### D1：统一用户旅程与页面职责

- [x] 固定唯一主旅程：`目标 -> 计划草案 -> 用户确认 -> 执行 -> 成果证据 -> 复盘`。
- [x] 行动工作台负责目标、执行、调整、证据和复盘；规划能力成为工作台中的明确子流程，不再作为平行任务架构。
- [x] 保留 `/advisor` 的兼容路由，但入口和提交结果明确回到行动工作台；不再让用户理解内部 `mode`、`kind`、chain 等术语。
- [x] 将执行策略翻译为用户语言：自己完成、协助完成、交给系统；将 Run Command 呈现为“调整要求”。
- [x] 将 Trigger 呈现为“定时或条件启动”，而不是“自动任务”。

验收：用户从创建目标到看到待执行 Run 只走一条可理解路径；页面上不出现单任务、任务链、automatic、chain、provider 等实现概念。

回退点：保留现有路由和 API client；页面收口可逐个入口回退，不修改 canonical 数据。

实施证据（2026-07-16）：`/advisor` 已兼容跳转到 `/tasks?view=plan`；规划组件嵌入唯一行动工作台；独立导航入口已移除；发布回调与 URL 同步按顺序执行；执行方式、Run Command 与 Trigger 已改为用户语言。Vite production build 通过（1540 modules）；Playwright 验证 1440px 与 390px 视口无横向溢出、无控制台错误，视图切换保持 `view` 查询参数。

#### D2：计划草案与 canonical 写入收口

- [x] 将计划生成结果规范为可编辑的 Goal draft + Run specification；发布前允许修改目标、步骤、依赖、交付物和确认点。
- [x] 发布顺序固定为先创建 Goal，再从同一草案创建 Run；失败时显示可恢复状态，避免重复 Goal 或半发布结果。
- [x] 所有新增任务写入仅使用 `goalsApi`、`plansApi`、`runsApi`、`triggersApi`。
- [x] 旧 `/api/tasks` 与 `/api/task-chains` 前端写入降为零；后端兼容投影继续保留，暂不删除数据库表。
- [x] 为草案归一化、发布幂等/失败恢复及 owner 隔离补测试。

验收：创建一项简单行动和一项多步骤行动，数据库最终都表现为 Goal + Run + Step graph；前端网络请求中没有 legacy 写入。

回退点：旧接口仍可兼容读取；若新发布流程失败，可恢复原规划页面但不恢复旧写入。

实施与验收证据（2026-07-16）：新增前端草稿规范层 `src/domain/planDraft.js`，保存稳定草稿 ID、Goal/Run 幂等键、步骤依赖图、交付物与确认点；草稿发布按 Goal -> Run -> start 三段执行，并在资源不存在时只复位失效阶段。后端为 `task_goals` 增加 owner-scoped `idempotency_key` 及唯一索引，SQLite 创建使用 `BEGIN IMMEDIATE`，相同用户和键重试复用同一 Goal，不同用户隔离。真实服务发布了一项多步骤知识库行动（Goal `fd67a63d-baf9-4a54-81ca-62e024993e82`，Run `ac61d7db-980e-4512-8047-d0aad1002ac3`）和一项单步骤行动（Goal `35c90476-3e14-4ee6-8b79-5f8fc5aeeafd`，Run `e211f89d-db92-46b6-ac42-e376ea661da8`），网络写入均仅为 `POST /api/goals`、`POST /api/goals/{goal_id}/runs`、`POST /api/runs/{run_id}/start`，未出现 legacy 写入；同键重放返回原 Goal 和 Run。多步骤 Run 保留依赖、确认要求与交付物。`npm test`（4/4）和 `npm run build` 均通过；后端迁移与 HTTP 测试 9/9 通过。真实 Edge 390px 验证页面 `scrollWidth === clientWidth === 375`、所有非浮层元素在视口内、顶部视图标签可横向滚到末项且不遮挡刷新按钮、控制台无错误。`POST /api/plans` 当前因规划模型不可用返回 503，按约束保留为 D6 的 LM Studio 可选 AI 集成验收事项，不影响本阶段 canonical 发布链路。

#### D3：执行、调整与确认

- [x] 工作台默认突出“现在要做什么”，次级区域显示目标和历史记录，避免把状态管理做成开发控制台。
- [x] Run 生命周期提供开始、暂停、继续、取消和重试；Step 提供开始、完成、跳过、失败处理。
- [x] Approval 使用清晰的“需要你确认”区域，展示影响、待确认内容和确认结果。
- [x] Run Command 统一显示为“调整要求”，展示待处理、已采纳与历史记录，不暴露 command 状态字段。
- [x] Trigger 只配置何时启动和使用哪个已验证计划；暂停、恢复、编辑、删除不影响已有 Run。

验收：运行中追加调整要求后可在事件历史中追溯；暂停/继续和确认操作刷新后仍保持正确状态；重复操作不破坏状态机。

实施与验收证据（2026-07-16）：新增 `POST /api/runs/{run_id}/retry`，仅允许失败 Run 从首个仍可重试的失败 Step 恢复，保留原 Run、Step、事件和交付物，重试耗尽时返回明确的 `409 RUN_RETRY_NOT_AVAILABLE`。工作台将确认、下一步、失败原因和恢复入口置于行动主线；“调整要求”分为等待处理与已采纳，不展示内部状态字段。真实浏览器依次验证了确认等待、确认通过、Step 失败、Run 级恢复、调整要求提交和已采纳状态；验收 Goal `ce10e199-8c5e-41d2-afd4-1766bac2b924` 已在验证后归档。390px 刷新验证页面 `scrollWidth === clientWidth === 390`，抽屉宽度为 390px，顶部标签可独立横向访问且不遮挡刷新控件。前端 `npm test` 为 4/4 通过、`npm run build` 通过；后端迁移与执行 HTTP 测试 10/10 通过。

回退点：执行命令逐项增强，不更改后端状态枚举；可按控件回退到当前详情抽屉。

#### D4：Evidence 与 Review 闭环

- [x] 将 Step 输出和 Artifact 汇总为用户可查看的“成果”，支持文本、文件、链接和结构化摘要。
- [x] 完成 Run 前明确显示交付物是否齐全、未完成步骤和待确认项。
- [x] Run 结束后提供可见的“复盘”状态：结果摘要、完成情况、证据、评价、奖励结算和下一步建议。
- [x] 复盘只读取 canonical Event / Artifact / evaluation / reward 数据，不根据前端临时状态拼结论。
- [x] 允许从复盘创建后续 Goal 或新的 Run，但不得修改已完成 Run 的历史证据。

验收：一个完成的 Run 能回答“做了什么、产出了什么、谁确认了什么、结果如何、下一步是什么”；刷新或换设备后信息一致。

实施与验收证据（2026-07-16）：新增 SQLite migration 16 与 owner-scoped `task_run_reviews`，将用户评价、1-5 评分、笔记和下一步意图与不可变 Step、Artifact、Approval、Event 分离保存。新增 `GET /api/runs/{run_id}/review` 和仅终态可写的 `PUT /api/runs/{run_id}/review`；读模型从 canonical Run、Step completion criteria、Artifact、Approval、Event 与既有 reward settlement 聚合成果完整性、待确认项、缺失交付物、步骤输出、确认记录和奖励，不由浏览器临时拼结论。行动详情抽屉为所有 Run 显示“成果准备情况”；终态 Run 显示成果、步骤产出、确认记录、奖励结算、评价、复盘笔记和可预填的后续行动，保存复盘只追加 `run.review_updated` 事件，不修改历史证据。后端迁移与执行 HTTP 测试 12/12 通过；前端 `npm test` 4/4 与 production build 通过。隔离服务 `http://127.0.0.1:8011` 的真实 HTTP 验收完成了一条带 `Acceptance record` 交付物的 Run：完成前 `ready=false`，完成并记录 Artifact 后 `ready=true`、deliverables 为 `complete`；复盘保存 5 分和“达成”后刷新仍保留，并能读取 `run.review_updated`。验收 Goal 已归档。

回退点：先新增只读成果与复盘视图，不迁移或删除 Event、Artifact、reward 数据。

#### D5：兼容层审计与旧概念退场

- [x] 对迁移后的 legacy task/task-chain 数据做数量、owner、状态和关联 Run 审计。
- [x] 旧任务页面若仍存在，只允许只读跳转到对应 Goal / Run，不再提供创建、进度更新或删除写入。
- [x] 后端 legacy 路由保持兼容但加弃用说明和自动化测试，禁止承载新行为。
- [x] 删除前端不再使用的旧状态、表单和文案；数据库表删除另立 ADR，不在本阶段执行。

验收：代码搜索和浏览器网络记录均证明主流程无 legacy 写入；旧数据仍能找到对应的新执行记录。

实施与验收证据（2026-07-16）：旧 `/api/tasks` 与 `/api/task-chains` 保持兼容，但由 `legacy-task-execution-projection` 明确标注为适配层；所有成功与错误响应均包含 `Deprecation: true`、`Sunset: Fri, 16 Jul 2027 00:00:00 GMT`、successor `Link` 以及 `/api/goals`、`/api/runs`、`/tasks` 替代路径。旧 task 响应会返回对应 `goal_id`、`run_id`、`step_id`，旧 chain 响应会返回 `goal_id`、`run_id`；新增仅管理员可读的 `/api/admin/task-execution/legacy-audit`，按 owner 汇总数量和状态，并列出 legacy ID 到 canonical 记录的映射。前端对 `src` 与 `tests` 的搜索未发现 `tasksApi`、`taskChainsApi`、`/api/tasks`、`/api/task-chains`、`taskChains` 或 `task_chains`，主工作台仅使用 Goal / Run / Trigger API。后端兼容、投影、旧工作流和迁移测试共 12/12 通过。


回退点：兼容路由和旧表不删除，因此可恢复读取入口；任何数据删除必须等独立 ADR。

#### D6：阶段验收

- [x] 后端完整 unittest 通过，数量不得低于当前 143 项。
- [x] 前端 production build 通过。
- [x] Playwright 验证桌面端和移动端：创建目标、确认计划、开始执行、追加调整、完成步骤、查看成果、完成复盘。
- [x] 检查无横向溢出、文字遮挡、无效按钮、控制台错误和未处理请求错误。
- [x] LM Studio 为可选集成验收；本阶段未改 AI 路径，保持确定性替身而未调用。
- [x] 完成变更清单、迁移说明和回退说明；Git 提交与推送由用户单独确认。

实施与验收证据（2026-07-16）：后端 `python -m unittest discover -s tests` 为 150/150 通过；输出中的离线数据库、视觉服务失败和向量清理失败均为对应测试主动注入的降级分支。前端在 `npm_config_prefix=D:\app\nodejs` 下 `npm test` 4/4 通过、`npm run build` 通过。D4 已在隔离服务完成真实 Edge 验收，覆盖桌面与 390px 视口的创建、确认、执行、调整、完成、成果与复盘；D5 未改变该工作台行为，仅新增旧接口的兼容元数据与管理员审计。当前代码在新启动的 `http://127.0.0.1:8012` 上真实验证：`GET /api/tasks` 返回 `Deprecation: true`、2027-07-16 的 Sunset 和 Goal/Run successor Link，管理员审计端点返回 37 条 task 映射与 6 条 chain 映射。LM Studio 未调用，因为本阶段无 AI 路径改动，保持确定性测试隔离。迁移回退边界保持不删除旧表或旧接口：移除调用方可回到旧读取入口，数据删除另立 ADR。Git 提交与推送按用户当前意图单独执行，不在本阶段验收中自动发生。

补充审计（2026-07-16）：个人上下文模块已按真实实现复核。`ContextAssembler` 通过 Task、Growth、Knowledge 的公开读取接口组装上下文，按用户授权和固定条目预算选择信息；每一项带来源、更新时间、敏感度和选择理由。新增 migration 17，把每次访问的来源决策、被选资源引用和未纳入原因写入用户隔离的访问记录，不保存原始记忆或正文；陪伴页用自然语言显示“已使用、未授权、未纳入本次范围”。个人画像保持 Observation -> Claim -> Override -> Effective Profile，用户修正和否定优先，记忆归档默认可恢复。定向 HTTP 与迁移回归 10/10 通过。

### Phase E：第一方画像与长期记忆
进展补充（2026-07-16）：本期画像只使用虚空系统内、归属明确的第一方 Workspace 证据：目标与计划调整、Run/Step 执行、复盘和下一步、暂停/恢复/重试，以及用户主动保存的记忆或反馈。不接入 B 站或其他外部平台。任务复盘通过 TaskReviewObservationAdapter 以稳定来源键写入 task_run_review Observation；用户对画像候选的确认、修正、否定或重置通过 profile_claim_review Observation 写入。两类记录均按 owner_id + source_type + source_ref 幂等更新，复盘备注和修正后的原文不复制到通用证据属性中。

已完成：

- [x] 平台无关的内部 Observation 基线与来源去重；Migration 18 为来源检索增加索引
- [x] 只基于聚合指标的任务行为候选：执行完成、复盘后的下一步、多步骤推进、暂停后恢复、审批决策与目标计划调整
- [x] 候选必须由用户确认、修正或否定；确认后保留结构化行为值，否定会停止展示同一模式
- [x] 目标调整历史只记录调整类别和字段名，不复制目标文本、复盘、成果、记忆内容或审批备注
- [x] 候选证据同时带回最早/最晚观察时间；待处理审批不计入审批决策率，候选与持久化 Claim 保留同一时间范围

验证补充（2026-07-16）：新增聚合时间范围与待处理审批排除测试，并覆盖候选 HTTP 返回和确认后的 Claim 持久化。确定性后端全量测试为 160/160 通过；LM Studio 未调用。

验收补充（2026-07-16）：陪伴界面已显示基于行动记录的待确认候选，并提供“采用、调整、停止使用这类模式”操作。长期记忆与画像采用双重明确同意：记忆可单独参与协助，只有用户主动开启“帮助系统理解我”才会形成可撤回的画像项；未确认的系统候选不进入有效画像上下文。后端确定性全量测试 160/160 通过，前端既有单测 4/4 通过，Vite production build 通过；LM Studio 未调用。

收尾补充（2026-07-16）：已修复候选建议与已保存待审核理解的重复状态。恢复一条被否定的理解为“待审核”后，系统不会再次创建同一候选；新增 HTTP 回归覆盖这一流程，并在前端审核或修正后统一刷新画像与候选列表。后端 `160/160`、前端既有单测 `4/4` 及 Vite production build 均通过；本地后端 `/api/health` 与前端应用壳均返回 `200`。当前运行环境无法在保持浏览器沙箱开启的前提下执行无头截图，因此本轮未将自动视觉截图作为验收证据。

下一步：

- [x] 为候选补充可解释的最早/最晚观察时间；每个候选只携带支撑该聚合指标的事件时间范围，不引入自动衰减或隐式权重。
- [x] 将“停止使用此模式”以用户可见的覆盖/否定操作呈现到陪伴界面；候选现可采用、调整或停止使用，普通长期记忆只有在用户明确开启“帮助系统理解我”后才会进入画像
- [x] 扩展计划调整、审批/复盘偏好和用户主动记忆的候选规则，但保持非临床、非人格化表述
- [x] 仅在有可靠的知识使用事件后，才把知识使用模式纳入候选；绝不以原文内容直接推断画像

收尾验证（2026-07-16）：行为候选继续只读取 owner-scoped 聚合指标与时间范围。审批只统计已作出的通过/拒绝决定；复盘只统计“是否含下一步”，不读取或复制复盘正文；计划调整只统计变更类别；知识候选只统计有来源和引用的可靠使用事件，绝不读取问题、文档正文或来源标识。长期记忆的有效期已通过 HTTP 回归覆盖：过期记忆仍可被用户查看和续期，但不会进入上下文，续期后才重新具备上下文资格。

未来若支持外部导入，必须作为独立迭代：按平台显式授权、可撤销、可删除来源数据、传播删除到派生候选、可审计且默认关闭。模型只能帮助生成待审阅候选，不能直接写入有效画像。

## 7. 本轮验收标准

本轮完成 Phase B + Phase C，且满足：

1. 用户能看见系统怎样理解自己，以及每项理解来自哪里。
2. 用户可确认、修正、否定并恢复候选画像。
3. 用户关闭某个权限后，新的 context snapshot 不再包含该 section。
4. 系统精灵暂停后不读取个人上下文。
5. 所有记忆和画像数据按 owner 隔离。
6. 后端完整测试通过，前端 production build 通过。
7. 桌面端和移动端无横向溢出、文字遮挡或不可达操作。
8. 不调用 LM Studio 完成确定性测试；仅在最终可选集成测试中使用指定模型。

## 8. 后续验收标准

Phase D 完成后，用户不需要理解“单任务、任务链、自动任务”的技术差异，只需理解目标、计划、执行、调整和复盘。Phase E 完成后，画像只基于第一方系统证据生成可审阅、可撤回的候选。未来若另行支持平台导入，必须显式授权、可撤销，并且删除来源数据时可以追踪并撤销由其支持的候选推断。

## 9. 最终交付回归（2026-07-16）

本轮已用真实管理员会话完成 Goal -> 计划确认 -> Run -> Step -> Artifact -> Review 闭环。验收 Run 的两个步骤均记录用户可读完成说明与成果，Run 自动进入 completed；复盘结果、满意度、笔记和下一步在刷新后保持持久化。验收目标随后通过正式 Goal 更新接口归档；后端没有提供破坏性 Run 删除接口，因此未直接修改数据库。

完成页的最后一轮展示收口包括：

- 将内部成果类型 result、link 等映射为“一般成果”“链接”等用户文案，未知类型统一降级为“成果”。
- 按名称合并多个步骤重复声明的约定成果；只有所有声明位置均已记录时，合并项才显示为已记录。
- 未完成提示基于合并后的成果列表生成，不再重复显示同名缺口。
- 桌面端与 390px 视口均无页面横向溢出；完成页、成果列表、复盘表单与操作按钮可达。

最终确定性验证：

- 后端：使用项目已同步环境 .venv313 执行完整 unittest，175/175 通过。系统全局 Anaconda Python 未安装 FastAPI，不能作为项目测试解释器。
- 前端：node --test tests/*.test.js，10/10 通过。
- 构建：Vite production build 成功，1543 modules transformed。
- 浏览器：刷新后的 console errors、page errors、HTTP errors 均为空；LM Studio 未调用。
- 清理：本轮创建的 .browser-test-runtime 与 .pnpm-store 已核验并删除。


> **Superseded on 2026-07-18:** D5's temporary compatibility decision is no longer current. Migration 23 verifies legacy task and reward mappings, moves all valid history to Goal / Run / Step records, and deletes the legacy task routes, repositories, projection layer, mapping links, and database tables. Historical notes above describe the earlier staged rollout only; they are not an operating contract.
