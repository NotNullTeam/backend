# 测试套件

本目录包含各种测试套件脚本，用于批量运行和管理测试。

## 文件列表

- `test_suite_runner.py` - **[推荐]** 通用测试套件运行器，支持交互式选择
- `test_suite.py` - 原始的API测试套件运行器

## 使用方法

### 🚀 通用测试套件运行器（推荐）
```bash
# 交互式运行，可选择不同测试套件
python tests/api/suites/test_suite_runner.py

# 选项：
# 1. 运行主要API测试套件（v1目录下的所有测试）
# 2. 运行所有测试
```

###  原始测试套件
```bash
# 运行完整的API测试套件
python tests/api/suites/test_suite.py
```

## 📁 文件功能说明

### test_suite_runner.py
- **通用测试套件运行器**
- 支持交互式选择测试类型
- 模块化设计，易于扩展
- 提供详细的测试报告和汇总
- 包含v1 API测试和附件过滤测试

### test_suite.py
- **原始API测试套件**
- 批量运行API响应测试
- 提供基础的测试执行功能

## 🎯 最佳实践

1. **日常测试**：使用 `test_suite_runner.py` 进行交互式测试
2. **CI/CD**：可以直接调用具体的测试套件文件
3. **全面测试**：使用 `test_suite_runner.py` 的"运行所有测试"选项
