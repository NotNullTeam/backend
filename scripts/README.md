# IP智慧解答专家系统 - 脚本管理

本目录包含项目的各种管理和工具脚本，按功能分类组织。所有不必要和重复的脚本已被清理。

## 📁 目录结构

```
scripts/
├── manage.py                    # 主管理脚本入口
├── database/                    # 数据库管理脚本
│   ├── init_db.py              # 数据库初始化
│   └── setup_vector_db.py      # 向量数据库设置
├── development/                 # 开发工具脚本
│   ├── run_tests.py            # 测试运行器
│   ├── run_api_tests.py        # API响应测试运行器
│   ├── test_model_connection.py # LLM模型连接测试
│   ├── test_prompts.py         # 提示词工程测试
│   └── check_code_quality.py   # 代码质量检查
├── deployment/                  # 部署相关脚本
│   ├── start_weaviate.py       # 启动Weaviate服务
│   └── worker.py               # RQ Worker进程
├── demos/                       # 演示脚本
│   └── demo_hybrid_retrieval.py # 混合检索演示
├── maintenance/                 # 维护脚本
│   ├── backup_data.py          # 数据备份
│   └── health_check.py         # 系统健康检查
└── README.md                    # 本文件
```

## 🚀 快速开始

### 主管理脚本
```bash
# 初始化数据库
python scripts/manage.py init

# 重置数据库（谨慎使用）
python scripts/manage.py reset

# 检查开发环境
python scripts/manage.py check
```

## 📋 脚本分类说明

### 1. 数据库管理 (`database/`)
数据库相关的初始化、配置和维护脚本。

```bash
# 初始化主数据库
python scripts/database/init_db.py

# 设置向量数据库
python scripts/database/setup_vector_db.py
```

### 2. 开发工具 (`development/`)
开发过程中使用的测试、调试和质量检查工具。

```bash
# 运行测试套件
python scripts/development/run_tests.py all

# 运行API响应测试（推荐）
python scripts/development/run_api_tests.py                    # 所有API测试
python scripts/development/run_api_tests.py auth              # 认证模块测试
python scripts/development/run_api_tests.py --coverage        # 带覆盖率报告

# 测试LLM模型连接
python scripts/development/test_model_connection.py

# 测试提示词工程
python scripts/development/test_prompts.py

# 代码质量检查
python scripts/development/check_code_quality.py
```

### 3. 部署脚本 (`deployment/`)
生产环境部署和服务管理脚本。

```bash
# 启动Weaviate向量数据库
python scripts/deployment/start_weaviate.py

# 启动RQ Worker进程
python scripts/deployment/worker.py
```

### 4. 演示脚本 (`demos/`)
功能演示和使用示例脚本。

```bash
# 混合检索算法演示
python scripts/demos/demo_hybrid_retrieval.py
```

### 5. 维护脚本 (`maintenance/`)
系统维护、监控和数据管理脚本。

```bash
# 数据备份
python scripts/maintenance/backup_data.py

# 系统健康检查
python scripts/maintenance/health_check.py

# 清理旧备份文件
python scripts/maintenance/backup_data.py --cleanup-days 30
```

### `init_db.py` - 数据库初始化脚本
独立的数据库初始化脚本，与原根目录脚本功能相同。

```bash
python scripts/database/init_db.py
```

### `run_tests.py` - 测试运行脚本
提供便捷的测试运行命令，支持多种测试类型和覆盖率报告。

```bash
# 运行所有测试
python scripts/development/run_tests.py all

# 运行特定类型测试
python scripts/development/run_tests.py auth
python scripts/development/run_tests.py models

# 生成覆盖率报告
python scripts/development/run_tests.py coverage
```

### `worker.py` - RQ异步任务Worker
启动RQ任务队列的worker进程，用于处理异步AI分析任务。

```bash
# 启动Worker进程
python scripts/deployment/worker.py

# 监控任务队列状态
rq info

# 清空失败任务
rq empty failed
```

## 使用方式

### 方式1：使用Flask CLI命令（推荐）
```bash
flask init-db
```

### 方式2：使用管理脚本
```bash
python scripts/manage.py init
```

### 方式3：使用独立脚本
```bash
python scripts/database/init_db.py
```

## 开发流程

1. **首次设置**
   ```bash
   # 安装依赖
   pip install -r requirements.txt
   
   # 初始化数据库
   flask init-db
   
   # 启动应用
   python run.py
   ```

2. **日常开发**
   ```bash
   # 启动Flask应用
   python run.py

   # 启动异步任务Worker（新终端）
   python scripts/deployment/worker.py
   ```

3. **重置环境**
   ```bash
   # 重置数据库
   python scripts/manage.py reset
   ```
