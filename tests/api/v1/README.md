# API v1 测试套件

本目录包含所有v1版本API的响应测试文件。

## 文件结构

- `test_v1_auth_responses.py` - 认证模块API响应测试 (14个测试)
- `test_v1_cases_responses.py` - 案例模块API响应测试 (17个测试)  
- `test_v1_knowledge_responses.py` - 知识库模块API响应测试 (19个测试)
- `test_v1_system_responses.py` - 系统模块API响应测试 (19个测试)
- `test_v1_development_responses.py` - 开发工具模块API响应测试 (20个测试)
- `test_response_consistency.py` - 响应一致性测试 (15个测试)
- `test_v1_attachment_filter.py` - 附件类型过滤功能测试 (12个测试)

**总计：116个API响应测试用例**

## 运行测试

```bash
# 运行所有v1 API测试
pytest tests/api/v1/ -v

# 运行特定模块测试
pytest tests/api/v1/test_v1_auth_responses.py -v
pytest tests/api/v1/test_v1_cases_responses.py -v
pytest tests/api/v1/test_v1_knowledge_responses.py -v
pytest tests/api/v1/test_v1_system_responses.py -v
pytest tests/api/v1/test_v1_development_responses.py -v
pytest tests/api/v1/test_response_consistency.py -v
pytest tests/api/v1/test_v1_attachment_filter.py -v
```

## 测试覆盖

这些测试覆盖了：
- API端点的响应状态码
- 响应数据结构和字段
- 错误处理和异常情况
- 响应格式一致性
- 数据验证和业务逻辑
