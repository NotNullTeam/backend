# 项目管理脚本

本目录包含项目的各种管理和工具脚本。

## 脚本说明

### `manage.py` - 项目管理工具
统一的项目管理入口，提供数据库初始化、环境检查等功能。

```bash
# 初始化数据库
python scripts/manage.py init

# 重置数据库（谨慎使用）
python scripts/manage.py reset

# 检查开发环境
python scripts/manage.py check
```

### `init_db.py` - 数据库初始化脚本
独立的数据库初始化脚本，与原根目录脚本功能相同。

```bash
python scripts/init_db.py
```

### `run_tests.py` - 测试运行脚本
提供便捷的测试运行命令，支持多种测试类型和覆盖率报告。

```bash
# 运行所有测试
python scripts/run_tests.py all

# 运行特定类型测试
python scripts/run_tests.py auth
python scripts/run_tests.py models

# 生成覆盖率报告
python scripts/run_tests.py coverage
```

### `worker.py` - RQ异步任务Worker
启动RQ任务队列的worker进程，用于处理异步AI分析任务。

```bash
# 启动Worker进程
python scripts/worker.py

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
python scripts/init_db.py
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
   python scripts/worker.py
   ```

3. **重置环境**
   ```bash
   # 重置数据库
   python scripts/manage.py reset
   ```
