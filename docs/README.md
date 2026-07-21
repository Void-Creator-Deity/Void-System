# Docs

此目录保存当前架构、接口合同、工程规则、执行提示词、产品方向和历史资料。目标设计以根目录 `DESIGN.md` 为准，字段级运行接口以 OpenAPI 为准；二者不一致时必须登记并修复，不能把历史计划当作当前合同。

## 当前文档

- `../DESIGN.md`：产品目标、规范架构、核心流程、已知缺口和完成定义
- `../PROJECT_RULES.md`：实现、迁移、注释、测试和交付的强制规则
- `MASTER_ENGINEERING_PROMPT.md`：可直接交给编码代理执行的完整项目目标提示词
- `../CONTEXT.md`：领域语言、架构不变量和迁移方向
- `api-contract.md`：前端可依赖的现行 HTTP 合同
- `adr/`：已确认的架构决策
- `next-iteration-product-loop.md`：商城、系统伙伴、上下文工程、长期记忆和用户画像的产品输入
- `project-concept.md`：项目创意来源与产品定位
- `plans/`：阶段计划和历史审计；必须先阅读文件状态，Superseded 内容不是运行合同
- `archive/README.md`：历史报告入口，内容可能过时

## 建议阅读顺序

1. 根目录 `README.md`
2. `DESIGN.md`
3. `PROJECT_RULES.md`
4. `CONTEXT.md`
5. 与当前改动相关的 `adr/`
6. `api-contract.md`
7. 需要向编码代理下达全项目任务时使用 `MASTER_ENGINEERING_PROMPT.md`

## 状态约定

- `ACTIVE`：当前维护，可作为实现依据
- `MANDATORY`：所有实现和评审必须遵守
- `INTERNAL`：团队内部材料
- `SUPERSEDED`：已被后续设计或迁移替代，只能作为历史背景
- `ARCHIVED`：历史资料，可能过时
- `DEPRECATED`：正在退役，不得新增调用方

临时日志、截图、数据库、路由快照和测试缓存不应进入此目录或仓库提交。
