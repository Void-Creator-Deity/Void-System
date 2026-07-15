# Void System Frontend

Void System 的 Vue 3 前端。它面向普通用户呈现目标、行动、资料、成长和对话，不把 RAG、向量、provider、prompt、任务链或数据库结构暴露为主要交互概念。

## 主要页面

- `Home.vue`：当前进展、优先行动、常用入口和成长动态
- `TaskWorkspace.vue`：Goal、Run、Step 与自动安排的统一行动工作台
- `Advisor.vue`：把目标整理成可审阅方案并发布
- `AIConsole.vue`：分组对话、会话管理与临时附件
- `DocumentManager.vue`：个人资料上传、归档、恢复、搜索和资料问答
- `QA.vue`：知识问答与来源支持信息
- `Growth.vue`：能力方向、积分余额和活动记录
- `Settings.vue` / `Profile.vue`：用户偏好、账号和个人资料
- `RAGManagement.vue` / `AdminAIConfiguration.vue`：仅管理员可见的共享资料与模型连接维护

## API 组织

页面不得直接拼接 HTTP 请求。稳定入口位于 `src/api/`：

- `goals.js`：Goal 生命周期
- `runs.js`：Run、Step、Approval、Event 和 Run Command
- `triggers.js`：自动安排与触发
- `plans.js`：规范规划接口
- `growthProfile.js`：能力与积分记录
- `document.js` / `rag.js` / `knowledge.js`：个人与共享资料
- `chat.js` / `session.js`：对话与临时附件
- `administration.js` / `knowledgeAdministration.js`：管理员接口

旧 task catalog、task chain 和 reward marketplace 客户端已经移除。兼容端点仍由后端保留，但不应在新页面中继续扩展。

## 本地开发

```powershell
cd void-system-frontend
npm install
npm run dev
```

默认开发地址是 `http://127.0.0.1:5173`。Vite 将 `/api/*` 代理到 `http://127.0.0.1:8000`。需要使用其他后端时：

```powershell
$env:VITE_API_PROXY_TARGET = "http://127.0.0.1:8011"
npm run dev
```

## 构建

```powershell
npm run build
npm run preview
```

## 交互约束

- 普通用户使用“目标、行动、步骤、资料、成长、自动安排”等语言。
- 模型连接、索引修复和共享资料维护属于管理员操作。
- 写接口返回的 Run、Goal 或资料状态是权威结果，不在页面中猜测后端状态。
- 异步流程必须展示准备中、进行中、失败、可重试和完成状态。
- 桌面与移动端都必须保持无页面级横向滚动、按钮文字不溢出和可键盘操作。

接口细节见 `../docs/api-contract.md`。
