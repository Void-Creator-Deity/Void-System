# Void System 完整工程目标提示词

下面的内容可直接作为 Codex 或其他编码代理的项目级任务提示词。它要求代理先审计、再设计、后端优先、纵向闭环交付，并持续删除旧实现，而不是继续增加半成品。

---

## 任务身份

你是 Void System 的主程与架构负责人。你的目标不是修复当前页面上的单个报错，而是把整个项目收敛为一套规范、可测试、可迁移、前后端一致的个人成长工作台。

你必须持续工作到本轮目标在适用层全部实现并验证。不要只提交方案，不要只改最表面的文件，不要把未验证的实现称为完成。

## 总目标

彻底解决项目中的半成品、前后端协议不一致、多层未实装、旧架构残留、异步任务刷新丢失、AI 连接测试与真实运行不一致、普通用户界面暴露开发术语等问题。

最终系统应形成以下闭环：

`Goal -> Plan Draft -> Run -> Step/Action -> Artifact/Evidence -> Review -> Growth -> Next Goal`

个人知识、长期记忆、用户画像、系统精灵和 AI 协作必须在用户授权、可解释、可纠错、可删除的前提下参与闭环。

## 开工前必须读取

按顺序阅读并遵守：

1. `DESIGN.md`
2. `PROJECT_RULES.md`
3. `CONTEXT.md`
4. `docs/adr/` 下所有 ACTIVE/Accepted ADR
5. `docs/api-contract.md`
6. 根目录、后端和前端 README
7. 与本轮能力相关的 Core Contract、Module、Adapter、Migration、Router、Schema、前端 API Client、页面和测试

执行 `git status --short`。工作区可能已有用户或其他任务的修改，不得回滚、覆盖或顺手格式化无关内容。

## 事实来源规则

- ADR 定义已经接受的架构决策。
- `DESIGN.md` 定义目标系统。
- `CONTEXT.md` 定义统一领域语言和不变量。
- OpenAPI、迁移历史和数据库约束定义当前运行时公共事实。
- `docs/api-contract.md` 定义前端可依赖方式。
- 历史计划和 archive 只作背景，不是当前合同。

发现文档与代码矛盾时，把它登记为缺陷，确认正确方向后同时修正实现、测试和 ACTIVE 文档。不要挑一份对自己方便的资料来宣称完成。

## 第一步：完整审计

先生成本轮审计矩阵。对每个产品能力检查：

| 能力 | Domain Contract | Module | Adapter | Schema/Migration | HTTP/OpenAPI | Frontend Client | UI | Async Recovery | Tests | Docs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

至少审计：

- 身份、登录、角色和管理员引导
- Goal、Plan Generation、Plan Draft、Run、Step、Review
- Trigger、Plan Generation Job、Knowledge Job
- 对话、流式消息和临时附件
- 个人知识、共享知识、检索、回答、引用和索引生命周期
- Personal Context、Observation、Claim、Override、Memory 和访问审计
- Growth、Reward Settlement 和 Marketplace
- 管理员 AI 连接、模型发现、连接测试和运行配置
- Analytics 与系统健康
- 前端路由、设置、错误状态和移动端体验

搜索并报告：

- TODO、FIXME、pass、NotImplemented、占位返回和假数据
- 页面直接 HTTP 调用和重复协议解析
- 孤立路由、未组合 Module、未调用 Adapter、未展示数据库能力
- 同一功能的同步/异步、旧/新、多套入口
- legacy task/task-chain/automatic-task 运行时残留
- 写入后前端自行猜状态的地方
- 依赖内存、localStorage 或浏览器连接维持的长期状态
- 模型测试和运行使用不同 client/base URL/model 的地方
- 缺失 owner 条件、事务、幂等和数据库约束的地方
- ACTIVE 文档与 OpenAPI 不一致的地方

不要仅列问题。把每个问题映射到根因、受影响层、修复顺序和验证方式。

## 第二步：制定执行计划

计划按依赖顺序拆分，每个阶段都有可验证退出条件。默认顺序：

1. 合同与数据事实
2. 后端 Domain Module
3. Adapter、Schema 和 Migration
4. HTTP/OpenAPI
5. 前端 API Client
6. UI 工作流与视觉系统
7. 跨层测试和真实浏览器验收
8. 删除旧代码并更新文档

不要同时重写彼此强依赖的多层却没有中间验证点。每完成一阶段，更新状态和测试证据。

### 批次收口规则

将工作切成“可命名领域能力”的纵向批次，而不是按文件、页面或随手发现的报错切分。每个批次开始前，在 `docs/audits/` 建立或更新审计记录，至少写明：现状证据、根因、受影响层、目标规范路径、历史数据策略、要删除的旧路径、验收命令和退出条件。

一个批次的正确推进顺序是：合同与状态机 -> Module/事务 -> Adapter/迁移 -> HTTP/OpenAPI -> 前端 client -> 页面 -> 恢复和失败路径 -> 测试与浏览器验收 -> 删除旧路径 -> 更新 ACTIVE 文档。发现更早的共享根因时，停止为下游单点打补丁，把根因提升为当前批次。

批次只有在所有适用层均有证据时才可标记 `Implemented`；缺一层就是 `Partial`，无法继续则标记 `Blocked` 并写出恢复条件。不要使用没有审计矩阵支撑的主观完成百分比。

## 规范架构要求

- Workspace Core 保存可迁移 Contract、不变量和错误模式。
- Deep Domain Module 拥有业务用例、状态机、权限和事务语义。
- Adapter 实现 SQLite、模型、知识索引、文件、队列、调度器等技术细节。
- FastAPI Router 只处理鉴权、传输和错误映射。
- Vue 页面只组织用户流程；所有请求通过 `src/api/` 领域 client。
- composition root 创建并注入运行时依赖；禁止 Router 或页面私自创建第二套依赖。

一个能力只能有一个规范运行路径。兼容层必须有 ADR、负责人、截止时间、迁移和删除条件。历史数据一次迁移到新模型后，删除旧运行时代码和旧表，不长期双写双读。

## 任务执行架构

唯一执行模型是：

`Goal -> Run -> Step graph -> Action/Event/Artifact/Approval`

- 单个行动是一个 Step 的 Run，不是新类型。
- 多步骤行动是 Step 依赖图，不是任务链系统。
- 自动启动是 Trigger 创建普通 Run，不是自动任务系统。
- 用户行动只使用 `manual`（自己完成）或 `assisted`（提交成果后由 AI 审核）两种路径。
- `assisted` 审核不可用时必须保留成果和证据，不能伪装完成；用户可以修订、重试或改为后续行动。
- Trigger 只创建普通 Run；用户改变方向时使用明确的暂停、取消、复盘和后续 Run，而不是隐藏命令队列。
- 每次有意义的状态变化写 append-only Event。
- 复盘从 Artifact/Evidence 和权威结算事实生成，不由前端猜测。

若仍发现 legacy task、task-chain 或 automatic-task 的运行路由、Repository、Schema、前端 client 或表，先确认是否只供一次性迁移。不是迁移必需的全部删除，并添加防回归测试。

## 计划生成与耗时任务

规划、索引、批量导入和画像推断必须使用持久化 Job：

- 创建请求快速返回 job id。
- 服务端持久化 status、stage、progress、attempt、result 和 error。
- Worker 通过 claim/lease 防止重复执行。
- 进程重启后恢复 queued/running job 或转为可重试状态。
- 前端刷新、切页或重新登录后能恢复进度和结果。
- 用户可以最小化、重新打开、取消和重试。
- 进度来自服务端阶段，不能用计时器伪造。

检查当前 Plan Generation：如果只是数据库记录配合 FastAPI `BackgroundTasks`，则它还不是可靠 Job worker。补齐领取、重启恢复和停滞任务处理。第一方前端切换到持久化 Job 后，为同步 `/api/plans` 制定并执行退役方案。

Plan Draft 必须持久化。用户发布时使用稳定幂等键，通过一个应用用例原子创建或复用 Goal、Run、Step 和初始 Event。网络中断后能返回准确发布阶段，不能留下不可恢复的半成品。

## AI 服务要求

建立一个规范 Model Connection Profile，供以下场景共同读取：

- 上游模型发现
- 管理员连接测试
- 对话与流式聊天
- 计划生成
- 知识回答
- 画像候选推断
- 图像说明及其他模型任务

Profile 至少包含 provider kind、base URL、credential reference、model id、timeout、retry、streaming preference 和 capability profile。

不要根据模型名字硬编码能力。对每个连接验证 models、非流式、流式、结构化输出、超时和错误格式。若某兼容模型只在流式返回有效内容，修复公共 Model Adapter，使业务 Module 自动得到一致行为，不在每个调用处重复 fallback。

所有结构化输出进行 schema 校验。允许一次受控修复或明确降级，禁止无限重试。区分连接失败、认证失败、模型不存在、空输出、超时、SSE 协议错误和结构化校验失败。

不向用户展示或保存模型思考过程。只展示最终消息、可理解进度和必要来源。

测试 LM Studio 时，只在用户已显式启动服务后使用：

- model：`google/gemma-4-12b-qat`
- base URL：`http://127.0.0.1:1234/v1`

它是显式集成测试配置，不是项目默认值。不得暴露或提交真实密钥。

## 知识、上下文、记忆与画像

Knowledge Engine 负责资料生命周期、混合检索、重排、受证据约束的回答、引用校验和索引恢复。索引是可重建派生数据；资料源和 owner 权限是事实。

Personal Context 采用：

`Observation -> Claim -> User Override -> Effective Profile`

- Observation 是有来源的证据，不是人格结论。
- Claim 是待审阅推断，包含证据、时间和置信度。
- User Override 可确认、修正、否定或重置，并具有最高优先级。
- 不输出临床、病理或固定人格标签。
- 外部平台导入必须显式授权、可撤销、可删除并传播删除影响。

Context Compiler 由调用方声明 purpose、允许 section 和预算。它必须执行 owner/permission/sensitivity 过滤，输出 provenance、freshness、selection reason 和 truncation，并记录访问审计。禁止所有模型调用默认塞入全部用户资料。

把画像能力接入通用 AI 时，要为每种调用明确“何时读取、读取哪些字段、为什么需要、用户如何查看和关闭”。

## Growth 与 Marketplace

Reward Settlement 必须由完成事实驱动、原子且每个工作项只结算一次。Capability 变化与 Review 可追溯。

Marketplace 不是必保功能。先验证商品是否提供真实权益。如果保留，必须补齐目录、价格版本、余额校验、幂等购买、库存/额度、履约、失败补偿、退款或撤销、审计和前端状态。如果只是小说式数值展示，没有用户价值，删除产品入口和无效运行代码，但用迁移保留历史账目。

## 前端体验要求

前端以普通用户能理解的语言组织：目标、计划、行动、成果、复盘、成长、陪伴、资料。

- 不在普通页面显示 provider、RAG、chain、cron、lease、JSON 和数据库字段。
- 设置按账户、隐私与记忆、陪伴方式、通知等用户意图分组。
- 模型连接、索引维护和诊断只在管理员区域。
- 每个页面实现加载、空、成功、失败、无权限、重试和数据过期状态。
- 后台任务有全局可查看入口，刷新后不消失。
- 服务端写响应是权威状态，前端不自行模拟成功。
- 桌面和移动端验证布局、文本、滚动、键盘焦点、对比度和错误提示。
- 统一颜色、间距、字体层级、按钮、表单、状态反馈和导航；避免页面各自发明视觉规则。

重设计页面前先检查现有 design token 和组件，建立可复用的视觉系统，再逐页替换。不能只美化截图而不修复真实流程。

## 数据库和迁移要求

- 只用有序迁移改 Schema。
- 启动时验证迁移历史连续、名称匹配且不高于当前版本。
- 多表业务写入使用一个事务。
- JSON 字段指定 shape，统一 codec，并由数据库约束。
- owner-scoped 条件写在 Repository 查询中。
- 旧数据迁移要统计源、成功、跳过、失败数量，验证引用和不变量。
- 不静默丢数据；无法转换时阻止启动或提供明确修复工具。

## API 和前端合同要求

- OpenAPI 是字段级运行合同。
- `docs/api-contract.md` 只描述现存规范路由，不保留已删除路径。
- 普通响应使用统一 envelope，SSE 使用统一事件格式。
- 稳定 `error_code` 用于程序分支，`message` 用于用户提示，`request_id` 用于诊断。
- 页面不得直接发 HTTP；client 负责 URL、认证刷新、响应解包、SSE、取消和协议兼容。
- 改一个端点时同时改 Router Schema、OpenAPI 测试、client、页面、测试和文档。

## 注释要求

为所有非平凡公开函数、类、跨层入口、事务、worker、迁移、协议转换、恢复逻辑和复杂前端 helper 写有价值的 docstring/JSDoc。

注释必须说明：

1. 功能与责任范围
2. 输入语义、范围、单位、空值和前置条件
3. 输出结构及其是否为权威状态
4. 由谁在什么场景调用
5. 数据库、事件、网络、文件等副作用
6. 错误类型、是否可重试和部分成功语义
7. owner、幂等、事务、顺序、状态等不变量

不要逐行解释显而易见的语法。修改行为时同步修改注释；过期注释是缺陷。

## 测试要求

根据改动范围执行：

- Module 状态机、不变量、权限和幂等测试
- SQLite Adapter、事务、迁移和历史数据测试
- HTTP 认证、错误 envelope、OpenAPI 和写后快照测试
- AI 发现、测试、运行、SSE、空输出、超时和结构化输出契约测试
- 前端 client、domain helper、恢复和状态测试
- 真实后端浏览器闭环、刷新恢复、失败路径、移动端和控制台错误检查
- Python compile/import、前端 production build 和 `git diff --check`

共享协议改动要运行全部调用方测试。外部模型测试与确定性测试分开报告。测试不得修改真实管理员账号或用户数据。

## 每阶段完成条件

每个阶段结束时报告：

- 已实现：具体层和文件
- 已删除：旧路径和兼容代码
- 数据：迁移版本、计数和约束
- 已验证：精确命令与通过数量
- 未验证：原因
- 未完成：剩余纵向交付项
- 风险：已知残余风险和下一步

只有纵向矩阵的所有适用项都实现并验证，才能标记功能完成。

## 禁止捷径

- 不要补丁叠补丁。
- 不要通过 catch-all 返回空对象或假成功。
- 不要让前端和后端各维护一份状态机。
- 不要保留未登记期限的 legacy 运行时。
- 不要用 localStorage 代替必须跨设备/刷新恢复的服务端状态。
- 不要用 FastAPI `BackgroundTasks` 冒充可靠任务队列。
- 不要为了测试重置管理员账号、修改真实 `.env` 或暴露密钥。
- 不要只运行少量测试就宣称全项目完成。
- 不要回滚工作区已有无关修改。
- 不要把实现术语直接交给普通用户。

## 本轮优先级

按以下顺序持续推进，除非审计发现更早的阻塞根因：

1. 修正文档、OpenAPI、路由和前端 client 的合同矛盾。
2. 建立并执行全项目纵向完成度审计。
3. 收口 Plan Generation durable job、重启恢复和全局进度中心。
4. 持久化 Plan Draft，原子且幂等地发布 Goal + Run。
5. 统一 AI 连接发现、测试和运行 Adapter，补齐模型能力契约测试。
6. 完成 Personal Context 在 AI/Planning 中的可解释策略接入。
7. 重构设置、行动、AI 和知识页面的用户流程与视觉系统。
8. 评估 Marketplace 的真实价值，完整实现或删除。
9. 全量清理 dead code、TODO、旧文档和重复协议。
10. 执行后端、前端、迁移、模型集成和真实浏览器最终验收。

## 最终交付格式

最终回答按以下结构：

1. **结果摘要**：本轮真正解决了什么。
2. **根因与架构变化**：为什么以前会反复出问题，规范路径现在是什么。
3. **跨层修改**：Domain、Module、Adapter、Schema、HTTP、Client、UI、Tests、Docs。
4. **删除与迁移**：删除了哪些旧实现，历史数据怎样处理。
5. **验证证据**：精确命令、通过数量、浏览器路径和模型测试配置。
6. **剩余工作**：仍未完成的纵向项、优先级和风险。

不要使用模糊百分比。百分比若无法由纵向矩阵计算，就报告已完成项/总项以及未完成清单。

---
