# IP智慧解答专家系统——后端

本仓库为“IP智慧解答专家”项目的后端服务，基于 Flask 构建。

## 核心技术栈
- **后端**: Python 3.8+, Flask
- **API文档**: Flask-RESTX (Swagger UI)
- **数据库**: SQLite
- **AI能力**: 阿里云百炼 (qwen-plus), Weaviate

---

## 🚀 开发环境设置

### 1. 环境要求
- Docker & Docker Compose

### 2. 启动步骤

```bash
# 1. 生成 .env 文件 (仅首次需要)
# 该脚本会创建 .env 并生成必要的随机密钥
python scripts/deployment/setup_env.py
# 或复制示例环境文件（手动方式）
# Linux/Mac
cp .env.example .env
# Windows (PowerShell/CMD)
copy .env.example .env

# 2. 构建并启动所有服务
# -d 参数使服务在后台运行
docker compose up -d --build

# 3. 查看服务运行状态
docker compose ps
```

- **访问地址**: `http://localhost:5001`
- **API文档**: `http://localhost:5001/api/v1/docs/` (Swagger UI)
- **停止服务**: `docker compose down`

### 3. 手动本地部署 (可选)

如果不想使用 Docker，可以手动配置本地环境：

1.  **创建虚拟环境并激活**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # Linux/Mac
    # .venv\Scripts\activate  # Windows
    ```
2.  **安装依赖**
    ```bash
    pip install -r requirements.txt
    ```
3.  **配置环境变量**
    ```bash
    # 推荐使用脚本生成 .env（会生成必要的随机密钥）
    python scripts/deployment/setup_env.py
    # 或复制 .env.example 为 .env 并填入必要配置
    # Linux/Mac
    cp .env.example .env
    # Windows (PowerShell/CMD)
    copy .env.example .env
    ```
4.  **初始化数据库并启动**
    ```bash
    python scripts/database/init_db.py
    python run.py
    ```

---

## 开发常用命令

### 代码质量

```bash
# 格式化 (Black)
black .

# 类型检查 (Mypy)
mypy app/
```

### 数据库迁移

```bash
# 创建新的迁移脚本
flask db migrate -m "简短的迁移描述"

# 应用迁移到数据库
flask db upgrade

# 查看迁移历史
flask db history
```

### 运行测试

```bash
# 运行所有测试 (推荐使用 pytest)
pytest

# 运行指定模块的测试 (例如 auth)
pytest -m auth

# 生成测试覆盖率报告
pytest --cov=app
```

---

## 项目结构概览

```
backend/
├── app/                # 应用主目录
│   ├── api/            # API蓝图 (按模块划分)
│   ├── models/         # SQLAlchemy 数据模型
│   ├── services/       # 核心业务服务
│   ├── utils/          # 工具函数
│   └── __init__.py     # Flask应用工厂
├── scripts/            # 辅助脚本 (部署、管理等)
├── tests/              # 测试代码
├── migrations/         # 数据库迁移文件
├── config/             # 配置文件
├── run.py              # 应用启动入口
├── requirements.txt    # Python 依赖
├── Dockerfile          # 后端服务 Dockerfile
└── docker-compose.yml  # Docker Compose 配置文件
```

### 异步任务开发
```bash
# 启动Worker进程
python scripts/deployment/worker.py

# 监控任务队列
rq info

# 清空失败任务
rq empty failed
```

## 部署

### 生产环境配置（Docker 推荐）
生产环境建议直接使用 **Docker Compose**，免去系统层依赖：

```bash
# 构建并启动（以后台方式运行）
docker compose -f docker-compose.yml --env-file backend/.env up -d --build

# 查看日志
docker compose logs -f backend
```

### 可选：传统裸机部署（仅当无法使用 Docker 时）
```bash
# 安装依赖
pip install -r requirements.txt

# 设置生产环境变量
export FLASK_ENV=production

# 使用 Gunicorn（需自行 pip install gunicorn）
gunicorn -w 4 -b 0.0.0.0:5001 run:app
```

## 故障排除

### 常见问题

1. **导入错误**
   - 确保虚拟环境已激活
   - 检查 Python 路径配置

2. **数据库连接失败**
   - 检查数据库配置和网络连接
   - 确认数据库服务已启动

3. **端口占用**
   - 修改 `run.py` 中的端口配置
   - 或使用 `lsof -i :5001` 查找占用进程

### 日志查看
```bash
# 应用日志
tail -f logs/ip_expert.log

# 如果使用本地服务，查看服务状态
systemctl status redis     # Linux (如果使用Redis)
brew services list        # macOS
```

## 文档

### API 文档
- **在线文档**: 访问 `/api/v1/docs/` 查看完整的 Swagger UI 文档
- **本地开发**: `http://localhost:5001/api/v1/docs/`
- **生产环境**: `http://your-domain.com/api/v1/docs/`
- **技术栈**: 基于 Flask-RESTX 生成的 OpenAPI 3.0 规范

### 其他文档
- [开发指南](docs/project_management/backend-team-guide.md)
- [系统设计](docs/system_design/)
- [贡献指南](docs/CONTRIBUTING.md)
