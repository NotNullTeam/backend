# IP智慧解答专家系统——后端仓库

## 🏗️ 项目架构

### 后端技术栈
- **框架**: Flask + SQLAlchemy + Flask-Migrate
- **数据库**: MySQL (关系数据) + Weaviate (向量数据)
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
- Docker & Docker Compose
- MySQL 8.0+
- Redis 7+

### 1. 克隆项目
```bash
git clone <repository-url>
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

# 数据库配置
DATABASE_URL=mysql+pymysql://root:password@localhost/ip_expert
REDIS_URL=redis://localhost:6379

# AI服务配置
DASHSCOPE_API_KEY=your-dashscope-api-key
ALIBABA_ACCESS_KEY_ID=your-access-key-id
ALIBABA_ACCESS_KEY_SECRET=your-access-key-secret
```

### 4. 启动基础服务
```bash
# 启动MySQL、Redis、Weaviate等服务
docker-compose -f docker-compose.local.yml up -d
```

### 5. 初始化数据库
```bash
# 方式1：使用Flask CLI命令（推荐）
flask init-db

# 方式2：使用管理脚本
python scripts/manage.py init

# 方式3：使用独立脚本
python scripts/init_db.py
```

### 6. 启动应用
```bash
python run.py
```

应用将在 `http://localhost:5000` 启动

默认管理员账户：
- **用户名**: `admin`
- **密码**: `admin123`

## 🧪 测试

### 运行测试套件
```bash
# 环境检查
python scripts/run_tests.py check

# 运行所有测试
python scripts/run_tests.py all

# 运行特定模块测试
python scripts/run_tests.py auth      # 认证API测试
python scripts/run_tests.py models    # 数据模型测试
python scripts/run_tests.py api       # API测试

# 生成覆盖率报告
python scripts/run_tests.py coverage

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
│   │   ├── knowledge.py    # 知识库API
│   │   ├── statistics.py   # 统计API
│   │   └── __init__.py
│   ├── models/             # 数据模型
│   │   ├── user.py         # 用户模型
│   │   ├── case.py         # 案例模型
│   │   ├── knowledge.py    # 知识文档模型
│   │   ├── feedback.py     # 反馈模型
│   │   └── __init__.py
│   ├── services/           # 业务服务
│   │   ├── agent_service.py    # Agent服务
│   │   ├── retrieval_service.py # 检索服务
│   │   ├── vector_service.py    # 向量服务
│   │   └── idp_service.py      # 文档解析服务
│   ├── utils/              # 工具模块
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
├── docker-compose.local.yml # 本地开发环境
├── .vscode/               # VSCode配置
│   └── pyrightconfig.json # 类型检查配置
└── .env.example          # 环境变量示例
```

## 💡 核心功能

### 智能诊断流程
1. **用户提问** → 系统分析问题类型和复杂度
2. **知识检索** → 从向量数据库中检索相关文档
3. **Agent追问** → 如需更多信息，主动询问用户
4. **方案生成** → 基于检索结果生成解决方案
5. **反馈收集** → 收集用户反馈优化系统

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
python worker.py

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

### Docker 部署
```bash
# 构建镜像
docker build -t ip-expert-backend .

# 运行容器
docker run -p 5000:5000 ip-expert-backend
```

## 🔍 故障排除

### 常见问题

1. **导入错误**
   - 确保虚拟环境已激活
   - 检查 Python 路径配置

2. **数据库连接失败**
   - 确认 Docker 服务运行状态
   - 检查数据库配置和网络连接

3. **端口占用**
   - 修改 `run.py` 中的端口配置
   - 或使用 `lsof -i :5000` 查找占用进程

### 日志查看
```bash
# 应用日志
tail -f logs/ip_expert.log

# Docker 服务日志
docker-compose -f docker-compose.local.yml logs mysql
docker-compose -f docker-compose.local.yml logs redis
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
