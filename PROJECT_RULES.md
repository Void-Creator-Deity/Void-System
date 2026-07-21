# Void System 项目规则

- 状态：MANDATORY
- 最近更新：2026-07-18
- 适用对象：开发者、代码代理、评审者和自动化工具

## 1. 开工规则

修改代码前必须依次阅读：

1. `DESIGN.md`
2. `CONTEXT.md`
3. 与改动相关的 `docs/adr/`
4. `docs/api-contract.md`
5. 目标 Module、Adapter、Router、前端 client、页面和测试

先执行 `git status --short`，确认工作区已有改动。不得回滚、覆盖或格式化用户和其他任务留下的无关修改。

开始实现前写出本轮范围、根因、受影响层和验证方式。小修也要判断是否存在跨层影响，不能只修改报错最明显的一行。

## 2. 一个能力只能有一条规范路径

- Task Execution 只使用 Goal、Run、Step、Action、Event、Artifact、Approval。
- Trigger 只创建 canonical Run；正在进行的行动通过明确状态变更、成果提交和复盘推进。
- 旧任务、任务链、自动任务只允许存在于一次性迁移代码或明确归档资料中。
- 不允许新旧表双写、双路由并存、前端按接口可用性偷偷回退。
- 临时兼容必须由 ADR 记录负责人、截止时间、数据迁移和删除条件。
- 完成迁移后必须删除旧路由、Module、Repository、Schema、前端 client、测试夹具和死文档。

## 3. 纵向完整交付

每个功能先建立以下检查表，并按后端优先顺序推进：

1. Domain Contract 与状态机
2. Module 用例和事务
3. Adapter 与外部依赖
4. Schema、Migration 和约束
5. HTTP Router、Schema、OpenAPI 和错误码
6. 前端领域 client
7. 页面/组件完整用户流程
8. 异步进度、刷新恢复、取消、重试和失败处理
9. Module、Adapter、HTTP、前端和浏览器测试
10. ACTIVE 文档

适用项未完成时，不得用“基本完成”“接口已经有了”代替明确状态。进度报告必须区分已实现、已验证、未实现和阻塞。

每轮重构以一个可验收的领域能力为最小批次，并在开始前记录到 `docs/audits/`。记录必须包含现状证据、根因、受影响层、规范路径、旧路径删除条件、数据策略和验收命令。不得在同一批次中随意穿插多个没有共同验收标准的功能；发现新的阻塞根因时，暂停下游界面修改并将根因提升为独立批次。

## 4. 根因修复

- 先复现和定位最早出现错误的层，再修改。
- 修复一个协议问题时搜索全部调用方、同类端点和共享解析器。
- 同一问题在两个以上调用方出现时，应收敛到公共 Interface 或 Adapter，而不是复制补丁。
- 修复数据形状时同时处理写入、读取、历史迁移、数据库约束和前端解析。
- 修复 AI 兼容问题时同时检查模型发现、连接测试、运行调用、流式解析、结构化输出和错误映射。
- 不吞异常，不用空对象或假成功掩盖缺失实现。

## 5. Module 与 Interface

- HTTP Router 只处理鉴权、传输和错误映射。
- 领域规则、状态转换、权限判断和跨记录事务属于 Domain Module。
- Adapter 只实现外部技术细节，不改写领域语义。
- 页面不拥有后端状态机；前端 domain helper 只处理展示和客户端流程。
- Module 应通过小而稳定的 Interface 提供较多行为。删除一个 pass-through Module 若只会让同样复杂度散到多个调用方，则该 Module 有价值；否则应合并。
- 新增 Interface 前说明第二个 Adapter、测试替身或替换需求。不要为形式上的分层制造浅封装。

## 6. API 规则

- 第一方页面只能调用 `void-system-frontend/src/api/` 中的命名方法。
- 禁止在页面、store 或组件中直接写 `axios.get/post` 和字符串 URL。
- 普通 JSON 端点使用统一响应 envelope；流式端点使用统一 SSE event。
- 写请求返回权威资源快照，或返回可持久读取的 resource/job id。
- 业务分支依赖稳定 `error_code`，不解析错误文本。
- 删除、替换或新增路由时，同步更新 OpenAPI 测试、client、页面、`docs/api-contract.md` 和相关 README。
- 不允许“测试连接”与“真实运行”使用不同的 base URL、认证、model id 或 client 构造规则。

## 7. 数据库与迁移规则

- 只通过有序迁移修改 Schema。
- 每个迁移必须可在旧版本数据库上运行，并验证目标版本、数据数量和关键不变量。
- 迁移不得依赖 HTTP 路由或运行时 legacy Module。
- 历史数据转换采用一次性迁移；禁止为了读取旧数据永久保留旧 Repository。
- JSON 列必须指定 object/list/scalar shape，使用统一 codec，并在数据库层约束。
- 多表业务写入必须由一个 Adapter 事务完成。
- 所有 owner 数据查询都必须在 SQL/Repository 层带 owner 条件，不能读取后再由前端过滤。
- 破坏性迁移需要备份/回退说明；不得静默丢弃无法转换的数据。

## 8. 异步任务规则

- 模型生成、索引重建、批量导入和画像推断不得依赖浏览器连接或单个请求存活；普通用户 Goal/Run 不是后台 Worker。
- Job 状态、阶段、进度、结果和错误必须持久化。
- 进程重启后能够恢复 queued/running job，或将其明确转换为可重试失败。
- 后台 Job Worker 使用原子 claim 或 lease；禁止两个 Worker 重复推进同一 Job。
- 前端刷新后通过 job id 恢复，不只存组件内状态。
- 取消是后端状态，不是隐藏前端加载框；worker 应在安全点响应取消。
- 进度来自服务端阶段，不用定时器制造假百分比。

## 9. AI 与上下文规则

- 连接配置只有一个规范化读取入口。
- Provider、base URL、credential、model 和 capability profile 必须一同传递。
- 模型能力通过探测或配置确认，不根据名称硬编码。
- 所有结构化模型输出进行 schema 校验，失败最多进行一次受控修复或明确降级。
- 不展示或持久化模型思考过程；只保存最终消息、必要状态和可审计调用元数据。
- Context Compiler 根据 purpose、权限、敏感度和预算选择上下文。
- 画像推断只能创建待审阅 Claim；User Override 优先。
- 模型错误必须区分连接、认证、模型不存在、超时、协议、空输出和结构化校验失败。
- LM Studio 只在显式集成测试中使用用户指定模型，不写成默认生产配置。

## 10. 前端与 UX 规则

- 普通用户界面使用产品语言，不显示 RAG、provider、chain、cron、JSON、lease 等实现词。
- 页面必须覆盖 loading、empty、success、error、permission、retry 和 stale 状态。
- 耗时操作提供后台任务入口，刷新后仍能查看进度和结果。
- 设置按用户意图组织；管理员连接和诊断与普通偏好分开。
- 写操作后以服务端返回为准，不在本地猜测最终状态。
- 图标用于常见工具命令，文本用于明确业务动作；不使用无意义装饰卡片。
- 桌面和移动端都要验证无横向溢出、遮挡、不可达按钮和文本截断。
- 键盘焦点、表单标签、对比度、禁用状态和错误提示必须可用。

## 11. 代码注释与文档字符串

注释用于解释合同、原因和风险，不复述语法。以下对象必须有完整 docstring/JSDoc：

- 对外公开且行为非平凡的函数、类和 Module 方法
- 跨层调用入口、状态机入口、事务入口
- Adapter 的外部协议转换和兼容逻辑
- 异步 worker、迁移和数据修复函数
- 复杂前端 domain helper、SSE 解析器和恢复逻辑

完整说明至少包含：

1. **功能/责任**：它拥有哪段行为，明确不负责什么。
2. **输入**：参数语义、允许范围、单位、是否可空和前置条件。
3. **输出**：返回结构、权威性、持久化结果或事件。
4. **调用情况**：由哪些 Router、Module、worker、client 或页面在什么场景调用。
5. **副作用**：数据库写入、事件、网络调用、缓存或文件变更。
6. **失败行为**：可能抛出的领域错误、重试性和部分成功语义。
7. **不变量**：幂等、owner、事务、顺序、状态或安全要求。

Python 推荐格式：

```python
def publish_plan(...):
    """将已审阅方案幂等发布为 Goal 和 Run。

    Inputs:
        generation_id: 当前用户拥有且状态为 ready 的生成任务标识。
        idempotency_key: 刷新或网络重试时保持稳定的发布键。
    Returns:
        服务端权威 Goal、Run 及发布阶段快照。
    Called by:
        Planning HTTP Adapter；用户在方案确认页点击“开始推进”时调用。
    Side effects:
        在一个事务中创建或复用 Goal、Run、Step 和初始 Event。
    Raises:
        PLAN_NOT_READY、PLAN_NOT_FOUND、PLAN_INVALID。
    Invariants:
        同一用户和幂等键不能创建两个 Run；不读取 legacy task 表。
    """
```

JavaScript 推荐格式：

```js
/**
 * 恢复并订阅一个持久化生成任务。
 * Input: 当前用户拥有的 generationId，以及可取消的请求配置。
 * Output: 规范化 job 快照；调用方以它作为唯一显示状态。
 * Called by: 规划页首次进入、刷新恢复和后台任务抽屉。
 * Side effects: 发起 HTTP 请求并更新轮询生命周期。
 * Failure: 保留最后快照，并返回可按 errorCode 分支的错误。
 * Invariant: 不根据本地计时器伪造进度。
 */
```

不要为简单 getter、显然的赋值、模板标记逐行添加注释。注释与代码不一致视为缺陷，修改行为时必须同步更新。

## 12. 测试规则

按风险选择并执行适用测试：

- Core/Module：状态机、不变量、权限、幂等和错误模式
- Adapter：真实 SQLite 事务、迁移、JSON shape 和 owner 隔离
- HTTP：认证、响应 envelope、OpenAPI、错误码和写后快照
- AI contract：发现、测试、运行、SSE、空输出、结构化校验和超时
- Frontend unit：domain helper、client、恢复和协议解析
- Browser：真实后端下的核心用户闭环、刷新、失败、移动端和控制台错误
- Build：Python compile/import、前端 production build

不得只运行与改动文件同名的单测就宣称跨层功能完成。修复共享协议时必须运行所有调用方测试。

测试不得修改真实管理员账号、真实用户数据或默认 `.env`。外部模型测试必须显式开启，并与确定性测试分开报告。

## 13. 完成与报告规则

完成前必须：

1. 搜索旧名称、旧路由、TODO、pass、NotImplemented 和重复入口。
2. 检查 OpenAPI 与前端 client 的路由一致性。
3. 运行适用测试、构建、迁移和浏览器闭环。
4. 运行 `git diff --check`。
5. 复查 ACTIVE 文档。

最终报告必须包含：

- 根因
- 实际修改的层和关键文件
- 删除的旧路径
- 数据迁移与兼容影响
- 精确测试命令和结果
- 未完成项与残余风险

没有验证的内容使用“已实现，未验证”，不能写“已完成”。

对于全项目重构，报告还必须更新 `docs/audits/` 中的纵向矩阵。矩阵只能使用 `Implemented`、`Partial`、`Missing`、`Blocked` 四种状态，并为每个非 Implemented 项写清下一步、责任层和可执行的验证方式。没有审计证据，不得给出整体完成百分比。

## 14. 禁止事项

- 禁止补丁叠补丁而不收敛公共协议。
- 禁止新增隐藏 fallback、双写、双读或假成功。
- 禁止在前端复制后端状态机。
- 禁止为测试重置管理员账号或覆盖用户配置。
- 禁止提交 `.env`、密钥、数据库、上传资料、向量索引和测试隐私数据。
- 禁止无关重构、全仓格式化或回滚已有修改。
- 禁止用临时内存状态实现需要刷新恢复的产品功能。
- 禁止把历史计划文档当作当前运行合同。


## AI Runtime Contract

1. Provider-specific endpoint normalization, credentials, model validation, and
   request options belong only in core/model_connection_profile.py.
2. Administration discovery/test and every runtime factory must resolve the
   same profile. A connection test is incomplete if runtime does not use the
   identical endpoint, model, and request options.
3. Switching a profile must publish a complete settings replacement. Do not
   mutate shared RuntimeSettings field by field or retain AI-bound caches across
   a profile change.
4. Do not silently downgrade to another provider or another installed model.
   Return a stable AI_* error and preserve the selected profile in diagnostics.

5. Every AI entry point must receive an explicit RuntimeSettings snapshot or
   run inside a documented transitional scope. Streaming and async functions
   must capture their client before yielding; they must not re-read process
   global configuration after a request has begun.
6. SSE and HTTP AI failures must carry a safe stable AI_* code. Configuration
   failures are actionable; upstream failures must not expose credentials,
   prompts, or raw provider responses.


## AI Evaluation Boundaries

1. Model-produced task evaluations must be parsed into an explicit validated
   contract before application code uses their status, score, feedback, or
   rewards.
2. Invalid evaluation output must fail closed with an actionable user-facing
   message; it must never be treated as completion.
3. A failed evaluation cannot award a positive reward, regardless of the raw
   model payload.
