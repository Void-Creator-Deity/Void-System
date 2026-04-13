# Void System

Void System 是一个面向学习与成长场景的全栈应用，整合了任务管理、AI 对话和文档问答能力。

## 项目简介

项目采用“系统终端”交互理念，将目标管理、任务执行、过程反馈与知识问答统一到一个工作台中。  
该设计源于“系统化成长”概念，但产品目标是严肃、可落地的学习与训练效率提升。

适用场景：

- 将长期目标拆分为可执行任务
- 在执行过程中保持连续反馈
- 管理个人资料并进行知识检索问答
- 将学习、健身、技能训练等规划型目标持续推进

## 核心功能

- **任务模块**：根据目标生成任务模板，支持发布与历史回溯
- **系统精灵**：基于历史会话实现连续对话
- **文档问答**：支持文档上传、检索与 RAG 问答
- **状态面板**：集中展示任务和阶段信息

## 面向用户

- 学生、自学者、备考人群
- 需要稳定推进计划的个人成长用户（如健身、技能训练、职业成长）
- 需要沉淀并复用个人知识资料的用户

当前阶段以学习与知识管理场景为核心，后续将扩展到更广泛的个人规划场景。

## 技术栈

- 后端：Python、FastAPI、LangChain、SQLite、ChromaDB
- 前端：Vue 3、Vite、Element Plus、Axios
- 包管理：`uv`（后端）+ `npm`（前端）

## 环境要求

- Python 3.11+
- Node.js 18+
- `uv`
- 可用模型服务（按 `LLM_PROVIDER` / `EMBEDDING_PROVIDER` 配置）

## 拉取与安装

```powershell
# 1) 拉取仓库
git clone <your-repo-url>
cd <repo-folder>

# 2) 安装后端依赖
cd void-system-backend
uv sync

# 3) 安装前端依赖
cd ..\void-system-frontend
npm install
```

如需检查前端依赖安装是否完整，可执行：

```powershell
cd void-system-frontend
npm run build
```

## 首次配置

在 `void-system-backend` 目录创建 `.env`（可基于 `.env.example`）：

```powershell
cd void-system-backend
copy .env.example .env
```

建议至少确认以下字段：

- `SECRET_KEY`
- `LLM_PROVIDER`
- `CHAT_MODEL`
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`（兼容接口时）
- `EMBEDDING_PROVIDER`（建议 `ollama` 或 `openai`）

说明：

- 后端会优先读取 `void-system-backend/.env`
- `EMBEDDING_PROVIDER` 如配置为 `ollama`，请确保本机 Ollama 服务可用

## 启动项目

### Windows 一键启动（推荐）

在仓库根目录直接运行：

```bat
start-dev.bat
```

该脚本会启动两个终端：

- 后端：`uv run main.py`
- 前端：`npm run dev`

### 手动启动（任意平台）

后端：

```powershell
cd void-system-backend
uv run main.py
```

前端：

```powershell
cd void-system-frontend
npm run dev
```

默认地址：

- 后端：`http://127.0.0.1:8000`
- API 文档：`http://127.0.0.1:8000/docs`
- 前端：`http://localhost:5173`

## 使用教程（标准流程）

完成启动后，建议按以下顺序体验：

1. **账户初始化**：注册并登录系统  
2. **任务生成**：在任务页面输入目标，生成并发布任务  
3. **连续对话**：在系统精灵页面发起多轮对话  
4. **文档入库**：上传文档并确认处理状态为完成  
5. **知识问答**：在问答页面针对文档提问并验证结果

若以上流程全部正常，说明项目主功能链路已可用。

## 常用命令

```powershell
# 后端启动
cd void-system-backend
uv run main.py

# 前端启动
cd void-system-frontend
npm run dev

# 前端构建
npm run build
```

## 联调检查清单

- 后端日志中 `LLM_PROVIDER` 与 `EMBEDDING_PROVIDER` 正确
- 前端页面可加载且登录成功
- `/api/*` 请求返回非 404/502
- `http://127.0.0.1:8000/docs` 可访问

## 常见问题

- **前端请求失败/跨域**：确认后端在 `127.0.0.1:8000`，并通过 Vite 代理访问 `/api`
- **AI 调用无响应**：检查 `.env` 模型配置、`OPENAI_BASE_URL` 和密钥
- **RAG 效果异常**：确认文档上传后已完成向量化
- **启动脚本不可用**：改用手动启动命令分别运行前后端
- **DeepSeek 调用失败**：确认 `OPENAI_BASE_URL` 使用兼容接口地址且包含 `/v1`

## 部署建议

- 后端建议使用 `uvicorn` 多 worker 并置于反向代理后（Nginx/Caddy）
- 前端执行 `npm run build` 后进行静态托管
- 生产环境关闭调试、单独管理密钥并配置备份

## 项目结构（顶层）

```text
.
├── start-dev.bat
├── void-system-backend/
├── void-system-frontend/
└── docs/
```

## 文档入口

- 后端：`void-system-backend/README.md`
- 前端：`void-system-frontend/README.md`
- 项目理念：`docs/project-concept.md`
- 历史资料：`docs/archive/README.md`

## 安全说明

- 不要提交真实密钥、用户数据、数据库快照
- 本地敏感配置仅放在 `.env`，并确保被 `.gitignore` 屏蔽
