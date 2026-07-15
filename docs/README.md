# Docs

此目录保存当前架构、接口合同、产品方向和历史资料。运行行为以代码、OpenAPI 和 ACTIVE 文档为准。

## 当前文档

- `../CONTEXT.md`：领域语言、架构不变量和迁移方向
- `api-contract.md`：前端可依赖的 HTTP 合同与兼容接口规则
- `adr/`：已确认的架构决策
- `next-iteration-product-loop.md`：商城、系统伙伴、上下文工程、长期记忆和用户画像的下一迭代范围
- `project-concept.md`：项目创意来源与产品定位
- `archive/README.md`：历史报告入口，内容可能过时

## 建议阅读顺序

1. 根目录 `README.md`
2. `CONTEXT.md`
3. `api-contract.md`
4. 与当前改动相关的 `adr/`
5. 需要规划下一轮产品闭环时再看 `next-iteration-product-loop.md`

## 状态约定

- `ACTIVE`：当前维护，可作为实现依据
- `INTERNAL`：团队内部材料
- `ARCHIVED`：历史资料，可能过时
- `DEPRECATED`：不再建议使用

临时日志、截图、数据库、路由快照和测试缓存不应进入此目录或仓库提交。
