# Void System Backend

虚空系统后端服务，提供用户认证、AI智能任务规划、文档智能处理和任务管理等功能。

## 🏗️ 架构概述

### 项目结构

```text
void-system-backend/
├── main.py              # 主应用入口
├── config.py            # 统一配置管理
├── errors.py            # 错误码和异常处理
├── database.py          # 数据库操作
├── pyproject.toml       # 项目配置和依赖管理
├── uv.lock              # 依赖锁定文件
├── middleware/          # 中间件层
│   ├── __init__.py
│   ├── auth.py          # 认证中间件
│   └── error_handler.py # 异常处理中间件
├── tools/               # 工具函数目录
│   ├── __init__.py
│   ├── utils.py         # 通用工具函数
│   └── check_syntax.py  # 语法检查工具
├── tests/               # 测试脚本目录
│   ├── __init__.py
│   ├── test_imports.py      # 导入测试
│   ├── test_refactor.py     # 重构测试
│   ├── test_login.py        # 登录测试
│   ├── test_pandas.py       # pandas测试
│   ├── syntax_test.py       # 语法测试
│   ├── check_users.py       # 用户检查
│   ├── create_test_user.py  # 创建测试用户
│   └── test.py              # 其他测试
├── api/                 # API业务模块
│   ├── __init__.py
│   ├── user_document_manager.py    # 用户文档管理
│   ├── user_vector_manager.py      # 用户向量管理
│   ├── personalized_qa.py          # 个性化问答
│   ├── user_document_parser.py     # 文档解析器
│   └── session_context_manager.py  # 会话上下文管理
├── services/            # 服务层
│   ├── __init__.py
│   ├── user_service.py  # 用户服务
│   └── ai_services/     # AI服务组件
│       ├── __init__.py
│       ├── advisor_chain.py     # 任务生成链
│       ├── persona_chain.py     # 系统精灵对话链
│       ├── qa_chain.py          # RAG问答链
│       └── rag_manager.py       # RAG文档管理器
├── user_documents/      # 用户文档存储目录
├── chroma_db/           # 向量数据库存储
└── void_system.db       # SQLite数据库文件
```

## 🚀 核心特性

### 1. 模块化架构

- **配置管理**: 统一配置管理，实现前后端解耦
- **错误处理**: 统一的错误码和异常处理机制
- **工具函数**: 通用工具函数库，消除代码重复
- **中间件**: 认证、日志、异常处理等横切关注点

### 2. 服务层设计

- **业务逻辑分离**: 服务层封装业务逻辑，提高代码复用性
- **依赖注入**: 清晰的依赖关系管理
- **接口标准化**: 统一的API响应格式

### 3. AI智能任务生成

- **智能规划**: 基于用户目标自动生成结构化任务计划
- **可执行步骤**: 提供详细、可操作的任务执行指南
- **多领域支持**: 支持学习、健身、工作等各类目标规划
- **进度追踪**: 任务发布与状态管理

### 4. DeepSeek风格文件处理

- **多格式支持**: PDF、Word、Excel、CSV、图片、文本等
- **智能解析**: 使用pandas等专业库进行文档解析
- **RAG问答**: 基于用户文档的个性化问答系统
- **向量存储**: 用户隔离的向量数据库存储

## 📋 开发规范

### 命名规范

```python
# 类名: PascalCase
class UserService:
    pass

# 函数名: snake_case
def get_user_service():
    pass

# 变量名: snake_case
user_id = "123"
current_user = {}

# 常量: UPPER_CASE
MAX_FILE_SIZE = 10485760
```

### 代码注释

```python
# 文件头部注释
"""
模块功能描述
"""

# 函数注释
def function_name(param: Type) -> ReturnType:
    """
    函数功能描述

    Args:
        param: 参数描述

    Returns:
        返回值描述

    Raises:
        ExceptionType: 异常描述
    """
    pass

# TODO注释
# TODO: 待实现的功能描述
# FIXME: 需要修复的问题
# NOTE: 重要的实现说明
```

### 错误处理

```python
# 使用统一错误码
from errors import ErrorCode, VoidSystemException

raise VoidSystemException.from_error_code(ErrorCode.USER_NOT_FOUND)

# 统一响应格式
from tools.utils import create_success_response, create_error_response

return create_success_response("操作成功", data=result)
return create_error_response("操作失败", error_code=ErrorCode.SYSTEM_ERROR)
```

## 🔧 配置管理

### 环境变量

```bash
# 服务器配置
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=development
DEBUG=true

# 数据库配置
DATABASE_URL=sqlite:///void_system.db
DATABASE_POOL_SIZE=10

# 认证配置
SECRET_KEY=your-secure-random-key-here

# 生成安全密钥的工具
# python tools/generate_secret.py
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# AI配置
OLLAMA_BASE_URL=http://localhost:11434

# 文件配置
MAX_FILE_SIZE=52428800        # 50MB
ALLOWED_EXTENSIONS=pdf,docx,xlsx,txt,md,csv,json,png,jpg,jpeg
UPLOAD_DIR=user_documents
```

### 配置文件说明

- `config.py`: 统一配置管理
- 支持环境变量覆盖
- 类型安全的配置访问

### 🔐

- **SECRET_KEY**: JWT令牌签名密钥，必须设置安全的随机密钥
- **生成密钥**: `python tools/generate_secret.py`
- **生产环境**: 必须通过环境变量设置，不得使用默认值

### 🏭 商业部署

#### 商业环境密钥管理最佳实践

1. **密钥轮换**: 每3-6个月更换一次SECRET_KEY (使用 `python tools/key_rotation.py --rotate`)
2. **密钥分层**: 开发/测试/生产使用不同密钥
3. **密钥服务**: 使用AWS KMS、Azure Key Vault、HashiCorp Vault等专业服务
4. **审计日志**: 记录密钥访问和使用情况
5. **平滑过渡**: 支持新旧密钥同时有效，避免服务中断

## ⚡ 快速开始

### 环境要求

- Python 3.11+
- uv 包管理器
- SQLite 数据库

### 安装与运行

```bash
# 克隆项目
git clone <repository-url>
cd void-system-backend

# 安装依赖
uv sync

# 运行开发服务器
uv run main.py
```

### 测试API

```bash
# 服务启动后，访问API文档
open http://localhost:8000/docs

# 或使用curl测试
curl -X POST http://localhost:8000/api/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test123","nickname":"测试用户"}'
```

## 🚀 部署运行

### 开发环境

```bash
# 安装依赖
uv sync

# 运行开发服务器
uv run main.py
```

### 生产环境

```bash
# 使用uv运行生产服务器
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 📚 API文档

启动服务后，访问：

- **API文档**: <http://localhost:8000/docs>
- **替代文档**: <http://localhost:8000/redoc>
- **OpenAPI规范**: <http://localhost:8000/openapi.json>

### 主要API端点

- `POST /api/token` - 用户登录获取令牌
- `POST /api/register` - 用户注册
- `POST /api/upload` - 文档上传处理
- `POST /api/lc/advisor` - AI任务规划生成
- `POST /api/lc/qa` - 基于文档的智能问答

## 🔍 代码质量改进

### 已完成的改进

- ✅ **包管理现代化**: 使用uv替代pip，提高依赖管理效率
- ✅ **消除冗余代码**: 统一API响应创建函数
- ✅ **前后端解耦**: 配置管理、服务层分离
- ✅ **代码架构优化**: 清晰的目录结构（tools/、tests/、services/分类）
- ✅ **命名规范统一**: 遵循Python命名规范
- ✅ **注释完善**: 详细的文档字符串和TODO标记
- ✅ **错误处理统一**: 标准化的异常处理机制

### 待改进项目

- 🔄 **任务评判功能**: 基于AI的任务完成度智能评估
- 🔄 **单元测试**: 完善测试覆盖率
- 🔄 **性能优化**: 添加缓存和异步处理
- 🔄 **监控日志**: 完善日志系统
- 🔄 **API文档**: 自动生成API文档
- 🔄 **微服务迁移**: 考虑微服务架构演进

## 🤝 贡献指南

1. 遵循代码规范和命名约定
2. 添加必要的注释和文档
3. 编写单元测试
4. 更新相关文档
5. 提交PR进行代码审查

## 📄 许可证

本项目采用 MIT 许可证。
