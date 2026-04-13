# Void System Frontend

Void System 的前端应用，负责页面渲染、路由管理、状态交互与后端 API 调用。

## 技术栈

- Vue 3
- Vite
- Vue Router
- Element Plus
- Axios

## 功能范围

- 登录注册与基础用户流程
- 首页、任务、AI 控制台等业务页面
- 文档管理与知识问答页面
- 与后端接口的统一请求封装

界面表达采用“系统终端”风格，强调信息密度、状态反馈与可操作性，面向真实使用场景而非展示页。

## 项目结构（核心）

```text
void-system-frontend/
├── src/
│   ├── api/
│   ├── components/
│   ├── pages/
│   ├── router/
│   ├── App.vue
│   └── main.js
├── vite.config.js
└── package.json
```

文档管理 API 统一入口为 `src/api/document.js`。

## 本地启动

```powershell
cd void-system-frontend
npm install
npm run dev
```

默认地址：`http://localhost:5173`

## 使用教程（前端）

1. 打开 `http://localhost:5173`
2. 注册并登录账号
3. 在首页查看任务与状态面板
4. 在 AI 页面发起多轮对话
5. 在文档页面上传资料并进入问答页面验证结果

## 与后端联调说明

`vite.config.js` 已配置开发代理：

- `/api/*` -> `http://127.0.0.1:8000`

因此前端请求使用相对路径即可，不需要写死后端域名。

联调前请确认：

- 后端服务运行在 `127.0.0.1:8000`
- 后端鉴权接口可正常返回 token
- 代理未被本地安全软件拦截

## 构建与预览

```powershell
npm run build
npm run preview
```

## 页面映射（核心）

- `Home.vue`：系统主页与任务总览
- `AIConsole.vue`：系统精灵对话
- `Advisor.vue`：AI 任务建议
- `QA.vue`：知识问答
- `DocumentManager.vue`：文档管理
- `RAGManagement.vue`：RAG 管理

## 注意事项

- 登录态令牌存于本地存储，调试时可清理 `localStorage` 重新登录。
- 若出现请求失败，优先检查后端服务是否在 `127.0.0.1:8000` 运行。
- 若页面空白或路由异常，先检查依赖是否完整安装并重启 `npm run dev`。
- 视觉与文案修改需保持统一术语：系统终端、任务模块、系统精灵、知识问答。
