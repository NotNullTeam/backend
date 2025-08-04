# IP智慧解答专家系统——后端仓库

## 🏗️ 项目架构

### 后端技术栈
- **框架**: Flask + SQLAlchemy + Flask-Migrate
- **数据库**: SQLite (轻量级本地数据库) + Weaviate (向量数据)
- **任务队列**: Redis + RQ
- **AI服务**: 阿里云百炼平台 (Qwen模型) + 文档智能
- **Agent框架**: LangGraph

### 核心特性
- **混合检索**: 向量检索 + 关键词检索 + 重排序
- **语义切分**: 基于文档智能的语义感知切分
- **多轮交互**: 状态机驱动的对话流程
- **知识溯源**: 可追溯的答案来源引用

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Redis 7+ (可选，用于异步任务)

### 1. 克隆项目
```bash
git clone <https://github.com/NotNullTeam/backend>
cd backend
```

### 2. 环境配置
```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量
复制 `.env.example` 为 `.env` 并配置：
```bash
cp .env.example .env
```

主要配置项：
```env
# 基础配置
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret

# 数据库配置（SQLite，零配置）
# 数据库文件将自动创建在 instance/ip_expert.db

# AI服务配置
DASHSCOPE_API_KEY=your-dashscope-api-key
ALIBABA_ACCESS_KEY_ID=your-access-key-id
ALIBABA_ACCESS_KEY_SECRET=your-access-key-secret
```

### 4. 初始化数据库
```bash
# 使用初始化脚本（推荐）
python scripts/init_db.py
```

### 5. 启动应用
```bash
python run.py
```

应用将在 `http://localhost:5000` 启动

默认管理员账户：
- **用户名**: `admin`
- **密码**: `admin123`

### 6. 可选服务（高级功能）
如果需要使用异步任务或向量搜索功能：

**选项1：使用模拟服务器（推荐开发测试）**
```bash
# 启动模拟Weaviate服务器
python bin/mock_weaviate.py
```

**选项2：本地安装Weaviate**
```bash
# 下载并运行本地Weaviate（推荐使用模拟服务器）
# 或参考官方文档进行本地二进制部署
# https://weaviate.io/developers/weaviate/installation/local-deployment
```

注意：系统仅支持本地Weaviate实例，不支持云端服务。推荐使用模拟服务器进行开发测试。

## 🧪 测试

### 运行测试套件
```bash
# 环境检查
python scripts/development/run_tests.py check

# 运行所有测试
python scripts/development/run_tests.py all

# 运行特定模块测试
python scripts/development/run_tests.py auth      # 认证API测试
python scripts/development/run_tests.py models    # 数据模型测试
python scripts/development/run_tests.py api       # API测试

# 生成覆盖率报告
python scripts/development/run_tests.py coverage

# 或者直接使用pytest（推荐）
pytest                        # 运行所有测试
pytest -m auth               # 运行认证测试
pytest --cov=app             # 生成覆盖率报告
```

### API测试示例
```bash
# 登录获取令牌
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# 获取用户信息
curl -X GET http://localhost:5000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# 创建诊断案例
curl -X POST http://localhost:5000/api/v1/cases \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{"query": "OSPF邻居建立失败", "attachments": []}'

# 上传知识文档
curl -X POST http://localhost:5000/api/v1/knowledge/documents \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "file=@document.pdf" \
  -F "vendor=华为" \
  -F "tags=OSPF,路由"
```

## 📁 项目结构

```
backend/
├── app/                     # 应用主目录
│   ├── __init__.py         # Flask应用工厂
│   ├── api/                # API蓝图
│   │   ├── auth.py         # 认证API
│   │   ├── cases.py        # 案例管理API
│   │   ├── analysis.py     # 诊断分析API
│   │   ├── knowledge.py    # 知识库API
│   │   ├── statistics.py   # 统计API
│   │   └── __init__.py
│   ├── models/             # 数据模型
│   │   ├── user.py         # 用户模型
│   │   ├── case.py         # 案例模型
│   │   ├── knowledge.py    # 知识文档模型
│   │   ├── feedback.py     # 反馈模型
│   │   └── __init__.py
│   ├── services/           # 业务服务（分模块组织）
│   │   ├── ai/             # AI相关服务
│   │   │   ├── agent_service.py      # Agent服务
│   │   │   ├── llm_service.py        # 大语言模型服务
│   │   │   ├── embedding_service.py  # 文本嵌入服务
│   │   │   └── log_parsing_service.py # 日志解析服务
│   │   ├── retrieval/      # 检索服务
│   │   │   ├── vector_service.py     # 向量服务
│   │   │   ├── hybrid_retrieval.py  # 混合检索
│   │   │   └── knowledge_service.py  # 知识检索服务
│   │   ├── network/        # 网络设备服务
│   │   │   └── vendor_command_service.py # 厂商命令生成
│   │   ├── document/       # 文档处理服务
│   │   │   └── idp_service.py        # 文档解析服务
│   │   └── storage/        # 存储服务
│   ├── utils/              # 工具模块
│   │   └── response_helper.py  # 统一响应格式
│   ├── errors.py           # 错误处理
│   └── logging_config.py   # 日志配置
├── scripts/                # 管理脚本
│   ├── manage.py          # 项目管理工具
│   ├── init_db.py         # 数据库初始化
│   ├── run_tests.py       # 测试运行脚本
│   └── README.md          # 脚本使用说明
├── tests/                  # 测试文件
├── migrations/             # 数据库迁移
├── config/                 # 配置文件目录
│   └── settings.py        # 应用配置
├── run.py                 # 应用启动文件
├── requirements.txt       # 依赖包列表
├── pyproject.toml         # 项目配置和工具配置
├── .vscode/               # VSCode配置
│   └── pyrightconfig.json # 类型检查配置
└── .env.example          # 环境变量示例
```

## � API 响应格式

### 统一响应格式

系统使用统一的JSON响应格式，所有API接口都遵循以下结构：

#### 成功响应
```json
{
  "success": true,
  "data": {
    // 具体的数据内容
  },
  "message": "操作成功"
}
```

#### 错误响应
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误描述",
    "details": {
      // 详细错误信息（可选）
    }
  }
}
```

#### 分页响应
```json
{
  "success": true,
  "data": {
    "items": [
      // 数据项列表
    ],
    "pagination": {
      "page": 1,
      "per_page": 20,
      "total": 100,
      "pages": 5
    }
  }
}
```

#### 验证错误响应
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "输入验证失败",
    "details": {
      "field_name": ["具体的验证错误信息"]
    }
  }
}
```

### 常见错误代码
- `VALIDATION_ERROR`: 输入验证失败
- `AUTHENTICATION_ERROR`: 认证失败
- `AUTHORIZATION_ERROR`: 权限不足
- `NOT_FOUND`: 资源不存在
- `CONFLICT`: 资源冲突
- `INTERNAL_ERROR`: 服务器内部错误

## �💡 核心功能

### 智能诊断流程
1. **用户提问** → 系统分析问题类型和复杂度
2. **知识检索** → 从向量数据库中检索相关文档
3. **Agent追问** → 如需更多信息，主动询问用户
4. **方案生成** → 基于检索结果生成解决方案
5. **日志分析** → AI驱动的网络设备日志智能分析
6. **命令生成** → 根据厂商类型生成特定配置命令
7. **反馈收集** → 收集用户反馈优化系统

### 核心服务模块

#### AI服务 (`app/services/ai/`)
- **日志解析服务**: 智能分析网络设备日志，检测异常模式
- **LLM服务**: 处理问答、分析、生成等任务
- **嵌入服务**: 文本向量化和相似度计算
- **Agent服务**: 多轮对话和工作流管理

#### 网络设备服务 (`app/services/network/`)
- **厂商命令服务**: 支持华为、思科、华三、Juniper等主流厂商
- **配置生成**: 根据问题分析自动生成设备配置命令
- **命令模板**: 预定义的故障排查和配置模板

#### 检索服务 (`app/services/retrieval/`)
- **统一知识检索**: 整合数据库查询和向量搜索
- **混合检索策略**: 关键词 + 向量 + 重排序
- **相关性评分**: 智能评估检索结果相关性

### 知识库管理
- **文档上传**：支持PDF、Word、图片等多种格式
- **智能解析**：使用阿里云文档智能进行结构化解析
- **语义切分**：基于文档结构进行语义感知切分
- **向量化存储**：使用text-embedding-v4模型向量化
- **标签管理**：支持厂商、技术分类等标签

### 多轮对话
- **状态管理**：基于LangGraph的状态机管理
- **上下文保持**：维护对话历史和案例状态
- **主动追问**：智能判断是否需要更多信息
- **可视化展示**：节点图形式展示对话流程

## 🔧 开发指南

### 代码规范
- 使用 Black 进行代码格式化
- 使用 Pylance 进行类型检查
- 遵循 PEP 8 编码规范
- 使用类型注解提高代码可读性

### 开发工具
```bash
# 代码格式化
black .

# 类型检查
mypy app/

# 环境检查
python scripts/manage.py check

# 启动开发服务器
python run.py
```

### 服务开发示例

#### 使用日志解析服务
```python
from app.services.ai.log_parsing_service import LogParsingService

log_service = LogParsingService()
result = log_service.parse_log("网络设备日志内容")
# 返回结构化的分析结果，包含问题类型、严重程度、解决方案等
```

#### 使用厂商命令服务
```python
from app.services.network.vendor_command_service import VendorCommandService

command_service = VendorCommandService()
commands = command_service.generate_commands("华为", "OSPF邻居建立失败", "查看OSPF状态")
# 返回特定厂商的命令列表
```

#### 使用知识检索服务
```python
from app.services.retrieval.knowledge_service import KnowledgeService

knowledge_service = KnowledgeService()
result = knowledge_service.retrieve_knowledge("路由协议配置", filters={"vendor": "华为"})
# 返回相关的知识文档和相似度评分
```

### 数据库管理
```bash
# 创建迁移
flask db migrate -m "描述信息"

# 应用迁移
flask db upgrade

# 查看迁移历史
flask db history

# 重置数据库（开发环境）
python scripts/manage.py reset
```

### 异步任务开发
```bash
# 启动Worker进程
python scripts/worker.py

# 监控任务队列
rq info

# 清空失败任务
rq empty failed
```

## 🌍 部署

### 生产环境配置
1. 设置环境变量 `FLASK_ENV=production`
2. 配置生产数据库连接
3. 设置强密码和密钥
4. 配置反向代理（Nginx）
5. 使用 Gunicorn 作为 WSGI 服务器

### 传统部署
```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
export FLASK_ENV=production

# 使用Gunicorn启动
gunicorn -w 4 -b 0.0.0.0:5000 run:app
```

## 🔍 故障排除

### 常见问题

1. **导入错误**
   - 确保虚拟环境已激活
   - 检查 Python 路径配置

2. **数据库连接失败**
   - 检查数据库配置和网络连接
   - 确认数据库服务已启动

3. **端口占用**
   - 修改 `run.py` 中的端口配置
   - 或使用 `lsof -i :5000` 查找占用进程

### 日志查看
```bash
# 应用日志
tail -f logs/ip_expert.log

# 如果使用本地服务，查看服务状态
systemctl status redis     # Linux (如果使用Redis)
brew services list        # macOS
```

## 📚 文档

- [开发指南](docs/project_management/backend-team-guide.md)
- [API 文档](docs/system_design/api/)
- [系统设计](docs/system_design/)
- [贡献指南](docs/CONTRIBUTING.md)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

[MIT License](LICENSE)

## 🆘 获取帮助

如果遇到问题，请：
1. 查看 [故障排除](#-故障排除) 部分
2. 运行环境检查：`python scripts/manage.py check`
3. 查看应用日志：`logs/ip_expert.log`
4. 提交 Issue 描述问题
