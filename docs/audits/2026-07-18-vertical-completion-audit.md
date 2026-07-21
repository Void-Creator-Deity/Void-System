# 2026-07-18 纵向完成度审计

- 状态：ACTIVE
- 审计日期：2026-07-18
- 范围：`void-system-backend`、`void-system-frontend`、迁移、HTTP 合同、当前用户工作流
- 判定标准：`DESIGN.md` 第 15、17、18 节与 `PROJECT_RULES.md` 第 3、13 节

## 结论

项目已经完成了任务执行模型从 legacy task/task-chain/automatic-task 向 `Goal -> Run -> Step -> Action -> Event -> Artifact -> Approval` 的大部分收口，也已将方案生成从请求内 `BackgroundTasks` 改造成持久化 Job + Worker Lease。但系统仍不能称为“后端彻底完成”：AI 调用合同、全局异步体验、上下文注入策略、知识生命周期和 Marketplace 的产品闭环仍在不同层缺失或不一致。

目前最危险的模式不是单个异常，而是“表、路由、页面各有一部分，缺少一个权威用例”。后续必须按本审计的批次顺序收口，禁止继续为旧页面增加客户端补偿逻辑。

## 状态含义

- `Implemented`：所有适用纵向层已实现并有本轮验证证据。
- `Partial`：存在规范路径，但至少一个适用层、恢复路径或测试缺失。
- `Missing`：没有可用的规范实现，或只有孤立代码。
- `Blocked`：依赖外部决策/服务，当前不能安全继续；必须写出解除条件。

## 纵向矩阵

| 能力 | 状态 | 已有证据 | 根因与缺口 | 受影响层 | 下一步与验收 |
| --- | --- | --- | --- | --- | --- |
| 身份、登录、角色与管理员引导 | Partial | `api/http/application.py` 统一注册身份路由；SQLite identity repository 存在；启动 Bootstrap 受显式配置约束 | 登录后的首屏、管理员诊断、普通用户设置仍需做真实浏览器与错误恢复验收；不得再通过测试重置管理员凭据 | Identity、HTTP、frontend route/settings、browser tests | 审核 owner/role 错误码、登录刷新、管理员设置入口；以普通用户和管理员两条浏览器流程验收 |
| Goal、Run、Step、Action、Event、Artifact、Approval | Partial | legacy task 路由、Repository 和 contracts 已删除；`task_execution_router` 是运行入口 | 现有数据如何完整映射、Review/Artifact/Approval 在 UI 与 API 的闭环证据不足；旧投影删除后的历史验证未形成报告 | Domain、migration、task module、HTTP、TaskWorkspace、tests、docs | 建立任务数据迁移计数与引用校验；跑 Goal 创建、Run 启动、行动完成、证据、Review 的浏览器闭环 |
| Plan Generation durable job | Partial | migration 26、SQLitePlanGenerationRepository、PlanGenerationWorker、GET /api/plan-generations、全局 backgroundProgress Store 与应用级后台进度抽屉已形成一条路径；repository/HTTP/前端 domain 测试已通过 | 全局 UI 当前只接入 Plan Generation；真实登录会话下的跨页、刷新、取消、重启和失败浏览器验收尚缺，知识索引尚未接入同一 read model | repository、worker、planning HTTP、plans client、backgroundProgress、App、Advisor、browser tests | 使用真实会话执行生成后离开规划页、刷新、从抽屉打开 Draft、取消、发布与重复提交；为知识索引补同类 Job adapter |
| Plan Draft 编辑与原子发布 Goal + Run | Partial | migration 27、SQLitePlanDraftRepository、PlanDraftService、/api/plan-drafts/*、plans.js 与 Advisor.vue 已形成规范路径；23 个后端 Plan Draft/Generation/Migration/HTTP 测试、27 个前端测试和 production build 通过 | 后端 owner、版本冲突、原子事务与幂等已验证；前端已删除 localStorage/sessionStorage 历史和 Goal -> Run -> start 发布链路，并可从后台进度以 draft_id 直达。仍缺真实浏览器的编辑、刷新、发布、重复点击验收 | schema、repository、planning module、HTTP、plans client、Advisor、global UI、browser tests | 使用真实后端执行生成、编辑、刷新、从后台进度打开、发布与重复提交；记录每一步资源计数和控制台错误 |
| Trigger、Run Command、Worker Lease、Checkpoint | Partial | 任务自动化路由仍被 application 注册；计划生成 Worker 有 claim、lease、heartbeat 和协作取消 | Run Command/Trigger 到 Goal/Run 的合同、可观测性和 UI 语义未完全审计；执行 checkpoint 是否服务端可恢复需逐条验证 | automation module/repository、execution module、HTTP、TaskWorkspace、tests | 明确 Trigger 只创建 Run、Run Command 只调度已有 Run；删除偏离该模型的残留入口，补重启/并发/取消测试 |
| 对话、SSE、临时附件 | Partial | conversations、documents、session files、AI 路由均被 application 组合；前端有 `api/streaming.js` 与流测试 | 流式输出、思考字段、断连、空输出、附件授权与实际运行模型的统一 contract 尚未完整验证 | AI adapter、SSE parser、routers、client、Companion/AIConsole、browser tests | 以统一连接 profile 重跑流式 contract；验证取消、断线重连、空输出不被伪装成成功 |
| 个人知识、共享知识、检索、引用与索引生命周期 | Partial | 统一资料馆授权模型、检索失败显式合同、持久化 Knowledge Job、SQLite lease/recovery、上传/重建/取消/重试 HTTP 合同、资料馆与全局后台进度状态已形成一条规范路径；后端全量 209、前端 28 项和生产构建通过 | 唯一剩余缺口是 BAT 启动后的真实浏览器验收：上传/刷新恢复/取消/重试/成功检索尚未被现场观察；不得以页面本地状态代替服务端任务快照 | knowledge module/adapters、schema、HTTP、client/UI、tests、browser acceptance | 按知识生命周期审计完成实机验收；若状态不一致，沿 persisted job -> worker lease -> document state -> UI snapshot 的规范链修复 |
| Personal Context、Observation、Claim、Override、Memory、访问审计 | Partial | personal_context module 已拆出 composition、policy、inference；Companion 页面调用 profile/suggestions/memories/access log | 画像尚非稳定的可审阅 Claim 引擎；Planning/Companion 的注入范围、来源展示、用户同意与覆盖规则需要统一并证明 | policy/inference/repository、AI context compiler、HTTP、Companion/Advisor、tests | 定义 purpose-scoped Context Compiler；每次注入返回来源摘要；补撤销、覆盖、删除、无授权不注入测试 |
| 管理员 AI 连接、模型发现、测试和运行 | Partial | administration、AI 路由与 `AIConfigurationManager` 存在；配置已向统一 runtime settings 收敛 | 所有调用面尚未证明共用同一 base URL、认证、model id、流解析和结构化输出；连接测试成功但运行失败的问题仍需全表审计 | runtime settings、llm factory、admin module、all AI routers/clients、tests | 为 discovery/test/chat/planning/profile/knowledge 建契约矩阵；统一 adapter 并新增跨上游 contract 测试。LM Studio 只作为显式外部测试 |
| Growth、Reward Settlement | Partial | growth router、repository、TaskWorkspace reward summary 存在 | Goal/Run Review 与 reward settlement 的事务边界、撤销/重复结算、可见性尚未在全闭环证明 | growth module/repository、task review、HTTP、Growth/TaskWorkspace、tests | 完成 Review -> settlement 的幂等事务与 UI 证据；覆盖重试和失败补偿 |
| Marketplace | Partial | reward marketplace repository 有 purchase transaction；路由仍自称保留 legacy shop paths | 商品权益履约、失败补偿、购买后能力变化和面向用户的价值没有完整产品闭环；保留入口会误导用户 | marketplace module/repository/router/schemas/client/UI/docs | 做产品决策：实现可验证权益履约与补偿，或删除商城入口和死代码；决策前不得扩展商品 |
| Analytics 与系统健康 | Partial | analytics、system 路由已组合，health module 存在 | 指标定义、job/AI 失败可观测性、管理员诊断和用户可理解状态尚未形成完整合同 | analytics/system modules、HTTP、admin UI、tests | 定义关键 SLI：Job 延迟、失败、重试、AI 合同失败；验证敏感信息脱敏 |
| 前端导航、设置、错误状态、移动端 | Partial | 已存在领域 API client，任务、顾问、AI 控制台、系统伙伴等页面已重构过部分视觉；Advisor 历史改为服务端草稿，Plan Generation 有跨页后台进度入口 | 其他耗时能力、路由和页面尚未做一次合同与移动端全审计；真实会话下的抽屉与核心流程浏览器验收尚缺 | frontend api/router/pages/styles/tests | 将知识索引等工作接入全局进度；逐页去开发术语、真接口验收、桌面/移动截图和 console error 检查 |

## 已确认的根因

1. **历史模型叠加**：旧任务、任务链、自动任务分别拥有表、路由和页面，后续在上面增加新模型，造成多套入口和状态投影。
2. **浏览器曾承担服务端职责**：方案历史、分步发布与进行中任务展示已分别迁移到服务端 Plan Draft 和全局进度 Store；其余耗时能力仍必须复用同一份服务端 Job 合同，不能再各自维护页面状态。
3. **AI 适配器缺少单一合同**：发现、连接测试、普通调用、SSE 和结构化输出曾在多个调用面分别处理，导致“测试成功，运行失败”或不同上游表现不一致。
4. **产品表面先于闭环**：Marketplace、画像、知识等功能有数据或页面，但缺少用户价值、授权、履约、恢复与验证链路。
5. **文档和实现没有作为一个交付物验收**：导致已有路由被误判为已完成能力，实际 Module、迁移、client 或 UX 仍缺失。

## 强制批次顺序

1. **P0：合同收口与审计执行**。清点 OpenAPI、第一方 client、路由注册和遗留名称，修复共享协议的最早断点。
2. **P1：Plan Draft 与发布事务**。已实现服务端草稿、原子发布和幂等恢复；待真实浏览器验收。
3. **P1：全局异步体验**。Plan Generation 已接入服务端驱动的后台进度中心；本批次仍待真实会话浏览器验收，并需要扩展到知识索引等耗时能力。
4. **P2：统一 AI Runtime Contract**。覆盖 discovery、test、chat、planning、profile、knowledge、SSE 和 structured output。
5. **P3：Personal Context 与知识闭环**。实现最小授权上下文注入、来源解释、纠错/撤销，以及可验证的知识索引生命周期。
6. **P4：Growth/Marketplace 决策**。先完成 Review/Settlement 事务，再根据权益履约结论实现或删除商城。
7. **P5：页面与视觉系统**。所有页面以规范 API 为前提收口，完成导航、设置、空状态、错误、移动端和无障碍验收。

## 本轮已验证证据

以下验证来自本轮前置重构，不能外推为全项目完成：

```powershell
cd "D:\文件仓库\VS Code  项目\虚空系统\void-system-backend"
.\.venv313\Scripts\python.exe -m unittest `
  tests.test_http_architecture `
  tests.test_plan_generation_repository `
  tests.test_sqlite_migrations `
  tests.test_http_planning -v
```

结果：29 个测试通过。

```powershell
cd "D:\文件仓库\VS Code  项目\虚空系统\void-system-frontend"
.\node_modules\.bin\vite.cmd build
```

结果：production build 通过，1549 个模块完成转换。

`npm run build` 当前受机器全局 npm 解析损坏影响；本项目本地 Vite 构建可用。这个环境问题不应被误判为前端产物失败，也不允许为了绕过它去修改项目运行时依赖。

## 本批次收口：持久化 Plan Draft 与原子发布

### 已实现

1. 后端事实源：migration 27 新增 owner-scoped plan_drafts、乐观版本、generation 引用、发布键和已发布 Goal/Run 引用；生成任务完成时与 Draft 创建在同一 SQLite 事务中完成。
2. 规范用例：PlanDraftService 对编辑使用 TaskExecution.normalize_plan_draft，对发布使用一条 SQLite 事务创建 Goal、Run、Step、依赖和初始事件；同一 draft/key 可安全重试。
3. HTTP 合同：GET/PATCH /api/plan-drafts 与 POST /api/plan-drafts/{draft_id}/publish 返回权威 Draft 快照；版本冲突、重复发布和 owner 隔离有稳定错误码。
4. 第一方客户端：Advisor 从服务端恢复近期草稿；进行中的 generation 由全局 backgroundProgress Store 恢复，完成后通过 job 的 draft_id 打开草稿；编辑走 PATCH，发布只走原子 publish。
5. 删除的旧路径：Advisor 不再使用 localStorage/sessionStorage 保存可恢复草稿或 generation 标识，不再从浏览器链式调用 Goal create、Run create 和 Run start。

### 已验证

后端：使用 .venv313 的 Python 执行 plan generation、plan draft、SQLite migration 与 planning HTTP 四组测试，23 个测试通过。
前端：node --test tests/*.test.js 通过 27 个测试；本地 Vite production build 通过，1549 个模块完成转换。
机器全局 npm 仍指向缺失的用户级包，不能作为本仓库构建命令；本地 Vite 依赖可用。

### 未完成与风险

- 尚未完成真实浏览器的生成、刷新、编辑、原子发布、重复点击验收。
- 全局后台进度当前只接入 Plan Generation；知识索引、批量导入和未来 Agent Run 尚未接入同一份服务端 Job read model。
- 已删除同步 `/api/plans` 与旧式 `/api/ai/advisor`：一方前端早已无调用方，现由 HTTP 404/OpenAPI 缺席测试阻止其被重新引入。

## 本批次增量：全局异步进度与恢复

### 已实现

1. `src/stores/backgroundProgress.js` 成为应用内唯一的 Plan Generation 恢复与轮询所有者：只读取 owner-scoped 服务端 Job；只有活跃 Job 存在时才轮询；退出登录会清除浏览器内存而不删除服务端工作。
2. `src/domain/backgroundWork.js` 定义最小公共 read model。Plan Generation 的进度、阶段、失败信息和 `draft_id` 只从服务端快照映射，浏览器不按时间猜进度。
3. `BackgroundProgressDrawer.vue` 已挂到 `App.vue` 的桌面侧栏与移动端标题栏。用户可从任意页面查看工作、停止生成，或以 `TaskWorkspace?view=plan&draft=...` 打开准备好的 Draft。
4. `Advisor.vue` 已删除页面私有的 `setTimeout` 轮询、`pollGeneration` 和页面卸载清理；提交、恢复和取消改为消费全局 Store。仍使用 Draft API 进行编辑和发布。

### 已验证

```powershell
cd "D:\文件仓库\VS Code  项目\虚空系统\void-system-frontend"
node --test tests\*.test.js
& .\node_modules\.bin\vite.cmd build
```

结果：27 个前端测试通过；Vite production build 通过，1549 个模块完成转换。

```powershell
cd "D:\文件仓库\VS Code  项目\虚空系统\void-system-backend"
& .\.venv313\Scripts\python.exe -m unittest `
  tests.test_plan_generation_repository `
  tests.test_plan_draft_repository `
  tests.test_sqlite_migrations `
  tests.test_http_planning -v
```

结果：23 个后端测试通过。测试环境存在 `StarletteDeprecationWarning`，不影响结果，但应在依赖升级批次处理。

### 未完成与风险

- 已登录浏览器会话在真实 UI 验收开始时失效并被正常送回登录页；未使用、修改或重置真实凭据，因此生成、刷新、抽屉直达、取消和发布的真人浏览器链路仍是 `Partial`。
- 当前公共 read model 只适配 Plan Generation。知识索引、批量导入和未来 Agent Run 尚未使用同一份 Job 合同，不能据此宣称“全局后台任务已完成”。
- 已完成旧同步规划路由退役；下一步仍需用浏览器验证 Plan Generation -> Plan Draft -> Publish 的刷新恢复与用户可见进度闭环。

### 退出条件

使用真实普通用户和管理员会话完成：提交生成 -> 离开规划页 -> 从任何页面打开后台进度 -> 刷新 -> 打开 Draft -> 编辑 -> 发布 -> 重复提交，且只产生一组 Goal/Run。随后为知识索引实现同样的服务端 Job Adapter，才可将“全局异步体验”标记为 `Implemented`。


## P2 Update: Canonical AI Runtime Connection

- Status: Partial
- Scope: administration configuration, model discovery/test, chat factory,
  planning evaluator, embeddings, knowledge resource lifecycle, and plan worker
  runtime settings capture.
- Root cause: administration probes and runtime factories each duplicated
  provider selection, endpoint defaults, and local-model options. Unknown
  providers could silently fall back to Ollama. AI-bound caches and the plan
  worker could retain a prior mutable settings object after a profile switch.
- Implemented: core/model_connection_profile.py now resolves one immutable
  profile. LM Studio uses normalized /v1, a local placeholder credential, and
  enable_thinking=false in both probes and ChatOpenAI. Runtime updates publish
  a replacement settings object and retire AI-bound knowledge caches. The plan
  worker resolves app.state.runtime_settings for each claimed job. User and
  system knowledge vector adapters now require injected RuntimeSettings.
- Deleted behavior: the evaluator's automatic retry with a different Ollama
  model; llm_factory's unknown-provider and unknown-embedding fallback.
- Verification: Python compile plus 58 targeted backend tests passed on
  2026-07-18, covering configuration discovery/test, LM Studio normalization and
  request options, snapshot replacement, no silent fallback, knowledge
  composition, task migration, persisted plan generation, plan drafts, and HTTP
  planning.
- Blocked evidence: an explicit local smoke test to http://127.0.0.1:1234/v1 on
  2026-07-18 was refused before model discovery, so google/gemma-4-12b-qat was
  not re-verified against a running LM Studio process in this batch. No project
  configuration or user data was changed by that test.
- Remaining follow-up: start or expose the local LM Studio server and rerun the
  administrator connection test; add a real-provider test fixture only when it
  is deterministic and opt-in.

## P2 AI Runtime Closure Evidence

- 2026-07-18 configured `gpt-5.6-luna` live check: discovery returned 7 upstream models including the selected model; connection verification returned visible text; and the runtime factory returned the same fixed visible response after custom OpenAI gateways were pinned to streamed chat-completion aggregation.

Status: Partial.

The code-level connection contract now covers administration discovery and
verification, runtime chat construction, planning, profile inference, persona
text and multimodal streaming, image caption, and knowledge-image extraction.
All feature paths resolve one canonical connection profile or receive the
request or job RuntimeSettings snapshot explicitly. Configuration errors map to
stable AI_* HTTP/SSE codes; no provider or model fallback is permitted.

Verified on July 18, 2026:

- python -m py_compile over the changed runtime, transport, inference, and
  knowledge modules.
- 63 targeted unittest cases covering AI configuration, factories, knowledge,
  planning, migrations, HTTP planning, and profile inference.
- 10 pytest cases covering AI SSE normalization, settings injection, and
  transport configuration errors.

The status remains Partial because the explicit local smoke test could not
connect to http://127.0.0.1:1234/v1 on July 18, 2026. No default settings,
credentials, or user data were changed. When LM Studio is serving
google/gemma-4-12b-qat, repeat model discovery and one non-streaming chat
request with chat_template_kwargs.enable_thinking=false.


### P2.3 Task Evaluation Boundary Repair

A real-path defect was found during cleanup: the task evaluator referenced an
undefined `TaskEvaluationResult`, allowing evidence review to fail before any
model invocation. The evaluator now validates model output with a concrete
Pydantic contract, fails closed when parsing or validation fails, clamps rewards
to non-negative integers, and zeroes all rewards for a `fail` decision.

Verified on July 18, 2026:

- `python -m py_compile services/ai_services/advisor_chain.py`
- 13 pytest cases covering AI HTTP transport, runtime injection, and evaluator
  boundary validation, including malformed non-JSON model output.
- 19 unittest cases covering runtime settings, durable planning, and HTTP
  composition.

The live LM Studio smoke-test status remains Partial: the listener at
`http://127.0.0.1:1234/v1` refused connections on July 18, 2026.


### P2.4 Knowledge Retrieval Failure Integrity

- Status: Partial
- Finding: the user semantic retrieval fallback and the user/system lexical
  retrieval adapters converted Chroma or embedding-provider exceptions into an
  empty list. That made an unavailable index indistinguishable from a valid
  search with no relevant material, so both the answer layer and the user could
  receive a misleading no-result state.
- Implemented: KnowledgeRetrievalError is now the retrieval-domain failure
  contract. User semantic retrieval retains its supported plain-similarity
  fallback, but raises the contract after both retrieval forms fail. User and
  system lexical adapters, and system semantic fallback, propagate the same
  contract instead of returning an empty list. The legacy user vector manager
  also propagates failed index access rather than silently returning an empty
  list.
- HTTP/UI behavior: knowledge search continues to map a failed index to a
  recoverable 503 KNOWLEDGE_SEARCH_FAILED. The document library now clears
  stale results on a new lookup and presents an in-page retry state when the
  service is unavailable, while a successful empty lookup remains a normal
  no-result outcome.
- Verification on 2026-07-18: 13 focused backend tests passed, covering all
  four retrieval channels, HTTP error mapping, document retention, and normal
  active-document filtering. Frontend Node tests passed (27), followed by a
  successful production Vite build.
- Environment note: the global npm launcher currently resolves a missing
  C:\Users\Void Creator Deity\AppData\Roaming\npm\node_modules\npm\bin\npm-cli.js.
  This is a local shell/tooling installation issue, not a frontend dependency
  failure: direct local Node tests and node_modules/.bin/vite.cmd build both
  completed successfully. Do not treat it as evidence that the application
  runtime is unavailable.
- Completed in the knowledge lifecycle closure: upload and rebuild now create
  owner-scoped durable jobs with worker leases, restart recovery, cancellation,
  retry, persistent progress, and document-status synchronization. The retired
  in-process and compatibility completion paths were removed.
- Verification: the full backend suite passed 209 tests and the frontend suite
  passed 28 tests, followed by a successful production Vite build on
  2026-07-20.
- Remaining follow-up: perform the real browser flow against the user BAT-started
  backend: upload, refresh while active, cancel, retry, and retrieve the
  completed document. The knowledge lifecycle remains Partial only because that
  live acceptance has not yet been observed.

### P2.5 Knowledge Lifecycle Durable Job Closure

- Status: Partial - implementation and automated verification complete; live browser acceptance pending.
- Canonical path: upload or rebuild -> persisted SQLite job -> lease-aware worker -> parse/index adapter -> authoritative job and document state -> document library and global progress recovery.
- Retired behavior: direct runtime ingestion coroutines, HTTP BackgroundTasks rebuild execution, and the lifecycle repository update_ingestion compatibility escape hatch.
- State correction: cancelling a processing job now records document parse_status=cancelled rather than misreporting the user-requested cancellation as a failure.
- Verification on 2026-07-20: full backend suite 209/209, frontend Node suite 28/28, and production Vite build passed. The lifecycle audit records exact commands and browser acceptance criteria.
- Remaining acceptance: a user-visible upload/rebuild flow against services launched from start-dev.bat, including refresh recovery, cancellation, retry, and successful knowledge retrieval.
