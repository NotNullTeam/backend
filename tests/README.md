# IP智慧解答专家系统 - 测试套件

本目录包含项目的所有测试用例，按照模块和测试类型进行组织。

## 📁 目录结构

```
tests/
├── api/              # API层测试
│   ├── test_auth.py          # 认证API测试
│   ├── test_auth_api.py      # 认证API详细测试
│   ├── test_basic_api.py     # 基础API测试
│   ├── test_cases.py         # 案例API测试
│   ├── test_cases_api.py     # 案例API详细测试
│   ├── test_feedback_api.py  # 反馈API测试
│   ├── test_interactions_api.py  # 交互API测试
│   └── test_statistics_api.py    # 统计API测试
├── services/         # 服务层测试
│   ├── test_services.py         # 通用服务测试
│   ├── test_vector_service.py   # 向量服务测试
│   ├── test_hybrid_retrieval.py # 混合检索测试
│   ├── test_hybrid_retrieval_core.py # 混合检索核心测试
│   └── test_knowledge.py       # 知识库服务测试
├── models/           # 模型层测试
│   └── test_models.py          # 数据模型测试
├── integration/      # 集成测试
│   ├── test_config.py          # 配置集成测试
│   ├── test_database.py        # 数据库集成测试
│   ├── test_vector_setup.py    # 向量数据库设置测试
│   └── test_weaviate.py        # Weaviate集成测试
├── unit/             # 单元测试
│   ├── test_config.py          # 配置单元测试
│   └── __init__.py
├── fixtures/         # 测试夹具和数据
│   └── __init__.py
├── conftest.py       # pytest配置和共享夹具
└── README.md         # 本文件
```

## 🚀 运行测试

### 使用便捷脚本

```bash
# 运行所有测试
python run_tests.py

# 运行特定类型的测试
python run_tests.py --type api          # API层测试
python run_tests.py --type services     # 服务层测试
python run_tests.py --type models       # 模型层测试
python run_tests.py --type integration  # 集成测试
python run_tests.py --type unit         # 单元测试

# 生成覆盖率报告
python run_tests.py --coverage

# 并行运行测试（需要安装pytest-xdist）
python run_tests.py --parallel

# 详细输出
python run_tests.py --verbose
```

### 直接使用pytest

```bash
# 运行所有测试
pytest

# 运行特定目录的测试
pytest tests/api/                    # API测试
pytest tests/services/               # 服务层测试
pytest tests/models/                 # 模型层测试
pytest tests/integration/            # 集成测试

# 运行特定测试文件
pytest tests/services/test_hybrid_retrieval_core.py

# 运行带标记的测试
pytest -m "unit"                     # 单元测试
pytest -m "integration"              # 集成测试
pytest -m "api"                      # API测试
pytest -m "hybrid_retrieval"         # 混合检索测试

# 生成覆盖率报告
pytest --cov=app --cov-report=html --cov-report=term-missing

# 并行测试
pytest -n auto
```

## 🏷️ 测试标记

测试用例使用以下标记进行分类：

- `@pytest.mark.unit` - 单元测试
- `@pytest.mark.integration` - 集成测试
- `@pytest.mark.api` - API测试
- `@pytest.mark.services` - 服务层测试
- `@pytest.mark.models` - 模型层测试
- `@pytest.mark.slow` - 慢速测试
- `@pytest.mark.auth` - 认证相关测试
- `@pytest.mark.vector` - 向量服务测试
- `@pytest.mark.knowledge` - 知识库测试
- `@pytest.mark.hybrid_retrieval` - 混合检索测试

## 📋 测试类型说明

### API层测试 (`tests/api/`)
测试REST API端点的功能，包括：
- 请求/响应格式验证
- HTTP状态码检查
- 认证和授权
- 输入验证和错误处理

### 服务层测试 (`tests/services/`)
测试业务逻辑和服务层功能，包括：
- 核心业务逻辑
- 外部服务集成
- 数据处理算法
- 混合检索算法

### 模型层测试 (`tests/models/`)
测试数据模型和数据库操作，包括：
- 模型字段验证
- 数据库约束
- 关系映射
- CRUD操作

### 集成测试 (`tests/integration/`)
测试组件间的集成，包括：
- 数据库连接
- 外部服务集成
- 端到端流程
- 配置加载

### 单元测试 (`tests/unit/`)
测试单个函数和类的功能，包括：
- 函数输入输出
- 边界条件
- 异常处理
- 配置逻辑

## 🔧 配置文件

- `pytest.ini` - pytest配置文件
- `conftest.py` - 共享测试夹具和配置
- `run_tests.py` - 便捷的测试运行脚本

## 📊 覆盖率报告

运行带覆盖率的测试后，可以在以下位置查看报告：
- 终端输出：覆盖率摘要
- `htmlcov/index.html`：详细的HTML覆盖率报告

## 💡 最佳实践

1. **测试命名**：使用描述性的测试函数名
2. **测试分组**：相关测试放在同一个类中
3. **使用标记**：为测试添加适当的标记
4. **夹具使用**：利用pytest夹具复用测试代码
5. **断言清晰**：使用清晰的断言消息
6. **独立性**：确保测试之间的独立性

## 🐛 调试测试

```bash
# 运行失败时立即停止
pytest -x

# 显示详细错误信息
pytest -v --tb=long

# 运行特定测试
pytest tests/services/test_hybrid_retrieval_core.py::TestHybridRetrievalCore::test_extract_keywords

# 进入调试模式
pytest --pdb
```

## 📈 持续集成

测试套件支持在CI/CD流水线中运行：

```yaml
# GitHub Actions示例
- name: Run tests
  run: |
    python run_tests.py --coverage
    
- name: Upload coverage
  uses: codecov/codecov-action@v1
```
