# Void System Backend

Void System 的后端服务，基于 FastAPI 提供认证、任务、对话、文档与知识问答相关 API。

## 功能范围

- 用户注册、登录与鉴权
- 任务与分类相关接口
- AI 对话与建议生成
- 文档上传、解析、向量化与检索问答

## 技术栈

- Python 3.11+
- FastAPI + Uvicorn
- SQLite（业务数据）
- ChromaDB（向量数据）
- LangChain（AI 业务编排）

## 运行前准备

- Python 3.11+
- 已安装 `uv`
- 已完成 `void-system-backend/.env` 配置
- 模型服务可用（按 `LLM_PROVIDER` 与 `EMBEDDING_PROVIDER`）

## 目录结构（核心）

```text
void-system-backend/
├── main.py
├── config.py
├── database.py
├── errors.py
├── api/
├── middleware/
├── services/
├── tools/
├── pyproject.toml
└── uv.lock
```

## 本地启动

```powershell
cd void-system-backend
uv sync
uv run main.py
```

默认地址：

- 服务地址：`http://127.0.0.1:8000`
- Swagger：`http://127.0.0.1:8000/docs`
- ReDoc：`http://127.0.0.1:8000/redoc`

## 使用教程（后端）

1. 访问 `http://127.0.0.1:8000/docs`
2. 先调用认证接口（注册/登录）获取 token
3. 在带鉴权的接口中填入 `Authorization: Bearer <token>`
4. 依次测试任务、对话、文档上传、知识问答接口

## 环境变量

复制并编辑：

```powershell
copy .env.example .env
```

建议优先确认这些项：

- `SECRET_KEY`
- `LLM_PROVIDER`
- `CHAT_MODEL`
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`（兼容接口时）
- `EMBEDDING_PROVIDER`（当前建议 `ollama` 或 `openai`）

关键说明：

- `SECRET_KEY` 必须使用安全随机值
- `OPENAI_API_KEY` 与 `OPENAI_BASE_URL` 需要成对匹配
- 若 `EMBEDDING_PROVIDER=ollama`，需确保嵌入模型已可调用

## 常用接口分组

- 认证：`/api/token`、`/api/register`
- 会话与消息：`/api/chat/sessions/*`、`/api/stream-chat`
- 文档与知识库：`/api/user/documents/*`、`/api/user/qa/*`
- 任务与分类：`/api/tasks*`、`/api/task-categories*`

## 常见问题

- **服务启动成功但请求超时**：检查模型服务状态与网络连通性
- **接口 401**：确认 token 是否过期、请求头是否正确
- **文档问答返回空结果**：确认文档处理状态与向量检索配置

## 生产部署建议

- 使用 `uv run uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4`
- 为 `SECRET_KEY` 配置高强度随机值
- 将 `DEBUG` 关闭并收敛 `CORS_ORIGINS`
- 对数据库与文档目录配置备份策略

## 相关文档

- 仓库总览：`README.md`
- 前端说明：`void-system-frontend/README.md`
- 项目理念：`docs/project-concept.md`
