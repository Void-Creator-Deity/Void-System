# Void System

Void System 是一个面向个人成长、学习与长期目标推进的工作台。它把目标、可执行行动、知识资料、AI 协作和成长记录放在同一套可追踪流程中，而不是把任务、自动任务和任务链做成彼此独立的系统。

## 当前产品闭环

1. 用户创建一个 Goal，描述真正想完成的结果。
2. Planning Engine 将目标整理为可审阅的 Run 和 Step 图。
3. 用户发布并推进 Run；Step 可以依赖、跳过、重试、暂停、等待确认或由 Agent 执行。
4. Action、Event、Artifact、Approval、Checkpoint 记录执行过程和可恢复状态。
5. 完成结果经过证据与评估后触发一次性 Reward Settlement，更新积分、经验与能力成长。
6. 首页、行动工作台和成长页读取同一份执行事实，形成计划、执行、反馈和下一步的闭环。

## 核心能力

- **目标与行动**：Goal → Run → Step 是唯一的新执行模型，支持编辑、归档、重开和多次执行。
- **行动规划**：将自然语言目标转换为可审阅方案，再由用户决定是否发布。
- **自动安排**：Trigger 负责定时或事件触发 Run，不再维护另一套自动任务状态。
- **Agent 执行基础**：Worker Lease、Heartbeat、Checkpoint、Run Command 和事件流支持可恢复执行与用户中途干预。
- **对话协作**：分组、会话、临时附件和流式回复。
- **资料与问答**：个人资料生命周期、共享资料维护、检索、引用、支持度和索引修复。
- **成长记录**：能力方向、积分余额与积分活动；当前版本不展示没有明确价值闭环的商城。
- **管理功能**：管理员可维护共享资料、模型连接和运行配置。

## 架构方向

- `Workspace Core` 保存可迁移的领域合同与规则。
- `Growth App` 是当前产品外壳，组合目标、行动、知识、成长和对话模块。
- HTTP 路由只负责鉴权、传输格式和错误映射。
- SQLite、Chroma、旧 advisor/task 实现通过 Adapter 接入；兼容接口不是新的业务事实源。
- 旧 `/api/tasks`、`/api/task-chains` 等路径暂时保留，但写入会投影到 Goal、Run、Step、Event 和 Approval。新前端只使用规范接口。

详细领域语言与不变量见 `CONTEXT.md`，架构决策见 `docs/adr/`，前端接口约束见 `docs/api-contract.md`。

## 技术栈

- 后端：Python 3.11+、FastAPI、SQLite、LangChain adapters、ChromaDB
- 前端：Vue 3、Vite、Vue Router、Pinia、Element Plus、Axios
- 包管理：`uv` 和 `npm`

## 快速开始

```powershell
# 后端
cd void-system-backend
copy .env.example .env
uv sync
uv run main.py

# 另一个终端启动前端
cd void-system-frontend
npm install
npm run dev
```

Windows 也可以在仓库根目录运行 `start-dev.bat`。

默认地址：

- 前端：`http://127.0.0.1:5173`
- 后端：`http://127.0.0.1:8000`
- API 文档：`http://127.0.0.1:8000/api/docs`

需要联调其他后端端口时，可在启动前端前设置 `VITE_API_PROXY_TARGET`，例如：

```powershell
$env:VITE_API_PROXY_TARGET = "http://127.0.0.1:8011"
npm run dev
```

## 配置

从 `void-system-backend/.env.example` 创建 `.env`。生产环境必须设置唯一且足够长的 `SECRET_KEY`，并显式配置 `CORS_ORIGINS`、持久化数据库、模型服务和文件存储。管理员引导账号、测试用户接口和旧 LangServe 路由默认关闭。

普通用户设置不暴露 provider、向量库、prompt 或数据库字段；模型连接和索引维护只出现在管理员页面。

LM Studio 仅用于显式集成测试。需要测试时加载 `google/gemma-4-12b-qat`，服务地址为 `http://127.0.0.1:1234/v1`，不要把它写成项目默认配置。

## 验证

```powershell
# 后端全量测试
cd void-system-backend
uv run python -m unittest discover -s tests -v

# 前端测试与生产构建
cd ..\void-system-frontend
node --test tests/*.test.js
& .\node_modules\.bin\vite.cmd build
```

测试必须使用按 pyproject.toml 和 uv.lock 同步过依赖的 Python 环境；不要用未安装项目依赖的全局 Python 判断回归结果。当前 Windows 工作区可直接使用 void-system-backend\.venv313\Scripts\python.exe。

显式 LM Studio 冒烟测试：

```powershell
cd void-system-backend
$env:RUN_LMSTUDIO_INTEGRATION = "1"
uv run python tools/test_lmstudio_gemma.py
```

## 文档入口

- `CONTEXT.md`：领域语言、架构不变量和迁移方向
- `docs/api-contract.md`：前端可依赖的接口合同
- `docs/adr/`：已确认的架构决策
- `docs/next-iteration-product-loop.md`：商城、系统伙伴、上下文工程、长期记忆和用户画像的下一迭代范围
- `void-system-backend/README.md`：后端开发与部署
- `void-system-frontend/README.md`：前端页面与联调

## 安全说明

- 不要提交 `.env`、真实密钥、数据库、用户文件或向量索引。
- 管理员账号必须通过环境变量显式引导或由部署流程创建；仓库不提供固定生产密码。
- 用户数据访问必须保持 owner-scoped；管理员操作和 Agent 执行都应可审计。
