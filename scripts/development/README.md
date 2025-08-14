# 开发工具脚本
本目录包含开发过程中使用的各种工具和测试脚本。
## 脚本说明
### `run_tests.py` - 测试运行器
统一的测试运行入口，支持不同类型的测试执行。
```bash
# 运行所有测试
python scripts/development/run_tests.py all
# 只运行单元测试
python scripts/development/run_tests.py unit
# 运行集成测试
python scripts/development/run_tests.py integration
# 生成覆盖率报告
python scripts/development/run_tests.py coverage
```
### `test_model_connection.py` - LLM模型连接测试
测试大语言模型的连接性和基本功能。
```bash
python scripts/development/test_model_connection.py
```
### `test_prompts.py` - 提示词工程测试
测试LLM服务的各种功能和提示词效果。
```bash
python scripts/development/test_prompts.py
```
### `check_code_quality.py` - 代码质量检查
运行代码质量检查工具，包括语法检查、安全扫描等。

```bash
python scripts/development/check_code_quality.py
```

## 开发建议

- 提交代码前务必运行代码质量检查
- 新功能开发完成后补充相应的测试用例
- 定期运行完整的测试套件确保系统稳定性
