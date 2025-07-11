# IP智慧解答专家系统 - 测试指南

本文档提供了项目测试的完整指南，包括测试运行、覆盖率报告和测试最佳实践。

## 📋 测试概览

### 测试结构
```
tests/
├── __init__.py              # 测试包初始化
├── conftest.py             # pytest配置和fixture
├── test_auth_api.py        # 认证API测试
├── test_models.py          # 数据模型测试
├── test_database.py        # 数据库操作测试
├── test_config.py          # 配置和错误处理测试
└── README.md              # 本文档
```

### 测试类型
- **单元测试** (`@pytest.mark.unit`): 测试独立的函数和方法
- **集成测试** (`@pytest.mark.integration`): 测试组件间的交互
- **API测试** (`@pytest.mark.api`): 测试HTTP API接口
- **模型测试** (`@pytest.mark.models`): 测试数据库模型
- **认证测试** (`@pytest.mark.auth`): 测试认证相关功能

## 🚀 快速开始

### 1. 安装测试依赖
```bash
# 激活虚拟环境
source .venv/bin/activate

# 安装测试依赖
pip install -r requirements.txt
```

### 2. 运行所有测试
```bash
# 运行所有测试
pytest

# 运行测试并显示覆盖率
pytest --cov=app --cov-report=term-missing
```

### 3. 运行特定测试
```bash
# 运行认证相关测试
pytest -m auth

# 运行单元测试
pytest -m unit

# 运行集成测试
pytest -m integration

# 运行特定测试文件
pytest tests/test_auth_api.py

# 运行特定测试类
pytest tests/test_auth_api.py::TestAuthLogin

# 运行特定测试方法
pytest tests/test_auth_api.py::TestAuthLogin::test_login_success
```

## 📊 测试覆盖率

### 生成覆盖率报告
```bash
# 生成终端覆盖率报告
pytest --cov=app --cov-report=term-missing

# 生成HTML覆盖率报告
pytest --cov=app --cov-report=html

# 生成XML覆盖率报告（用于CI/CD）
pytest --cov=app --cov-report=xml
```

### 查看覆盖率报告
```bash
# 查看HTML报告
open htmlcov/index.html

# 或在浏览器中打开
python -m http.server 8000 -d htmlcov
```

### 覆盖率目标
- **总体覆盖率**: ≥ 80%
- **认证模块**: ≥ 90%
- **数据模型**: ≥ 85%
- **API接口**: ≥ 85%

## 🔧 测试配置

### pytest配置 (pytest.ini)
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --cov=app
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-fail-under=80
```

### 测试标记
- `@pytest.mark.unit`: 单元测试
- `@pytest.mark.integration`: 集成测试
- `@pytest.mark.auth`: 认证相关测试
- `@pytest.mark.models`: 模型测试
- `@pytest.mark.api`: API测试
- `@pytest.mark.slow`: 运行较慢的测试

### 环境变量
测试使用独立的配置，主要特点：
- 使用内存SQLite数据库
- 禁用CSRF保护
- 禁用JWT过期检查
- 启用测试模式

## 📝 测试最佳实践

### 1. 测试命名
```python
def test_should_return_success_when_valid_credentials():
    """测试：当提供有效凭据时应该返回成功"""
    pass

def test_should_raise_error_when_invalid_input():
    """测试：当输入无效时应该抛出错误"""
    pass
```

### 2. 使用Fixture
```python
def test_user_creation(database, sample_user):
    """使用fixture提供测试数据"""
    assert sample_user.username == 'testuser'
    assert sample_user.is_active is True
```

### 3. 测试隔离
- 每个测试函数都使用独立的数据库
- 测试之间不共享状态
- 使用事务回滚确保数据清理

### 4. 断言最佳实践
```python
# 好的断言
assert response.status_code == 200
assert 'access_token' in data
assert user.username == 'expected_username'

# 避免的断言
assert response.status_code != 500  # 太宽泛
assert data  # 不够具体
```

## 🐛 调试测试

### 1. 运行失败的测试
```bash
# 只运行上次失败的测试
pytest --lf

# 运行失败的测试并停在第一个失败
pytest -x

# 显示详细的错误信息
pytest -vvv
```

### 2. 使用pdb调试
```python
def test_debug_example():
    import pdb; pdb.set_trace()
    # 测试代码
```

### 3. 查看测试输出
```bash
# 显示print输出
pytest -s

# 显示详细日志
pytest --log-cli-level=DEBUG
```

## 📈 持续集成

### GitHub Actions示例
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    - name: Run tests
      run: |
        pytest --cov=app --cov-report=xml
    - name: Upload coverage
      uses: codecov/codecov-action@v1
```

## 🔍 测试检查清单

### 新功能测试检查
- [ ] 单元测试覆盖所有公共方法
- [ ] 集成测试覆盖主要用例
- [ ] 错误情况测试
- [ ] 边界条件测试
- [ ] 性能测试（如需要）

### 代码审查检查
- [ ] 测试名称清晰描述测试目的
- [ ] 测试独立且可重复
- [ ] 使用适当的断言
- [ ] 测试覆盖率满足要求
- [ ] 没有跳过的测试（除非有充分理由）

## 🆘 常见问题

### Q: 测试数据库连接失败
A: 确保测试使用内存数据库，检查conftest.py中的配置。

### Q: 测试运行很慢
A: 使用`-m "not slow"`跳过慢速测试，或优化测试数据。

### Q: 覆盖率不达标
A: 运行`pytest --cov=app --cov-report=html`查看详细报告，补充缺失的测试。

### Q: JWT令牌测试失败
A: 确保测试配置中禁用了JWT过期检查。

## 📚 相关资源

- [pytest官方文档](https://docs.pytest.org/)
- [pytest-flask文档](https://pytest-flask.readthedocs.io/)
- [pytest-cov文档](https://pytest-cov.readthedocs.io/)
- [Flask测试指南](https://flask.palletsprojects.com/en/2.3.x/testing/)

---

**注意**: 在提交代码前，请确保所有测试通过且覆盖率达到要求。
