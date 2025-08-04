# Application Core - 应用核心

本目录包含IP智慧解答专家系统的核心应用代码。

## 目录结构

```
app/
├── __init__.py          # Flask应用工厂和配置
├── errors.py           # 全局错误处理
├── logging_config.py   # 日志配置
├── api/                # API路由模块
│   └── v1/            # API版本1
├── models/            # 数据模型
├── services/          # 业务逻辑服务
├── utils/             # 工具函数
└── prompts/          # AI提示词模板
```

## 模块说明

### API (api/)
RESTful API接口层，按版本和功能模块组织：
- `v1/auth/` - 用户认证
- `v1/cases/` - 案例管理
- `v1/knowledge/` - 知识库
- `v1/files/` - 文件处理
- `v1/analysis/` - 智能分析
- `v1/system/` - 系统管理

### Models (models/)
数据模型层，定义数据库实体和关系：
- 用户管理（User, UserSettings）
- 案例系统（Case, CaseStep, Feedback）
- 知识库（Knowledge, KnowledgeChunk）
- 文件系统（FileRecord）
- 通知系统（Notification）

### Services (services/)
业务逻辑层，处理复杂业务规则：
- AI服务集成
- 文档处理
- 知识检索
- 数据分析

### Utils (utils/)
工具函数，提供通用功能支持：
- 文件处理
- 数据验证
- 格式转换
- 安全工具

### Prompts (prompts/)
AI提示词模板，用于各种智能功能：
- 日志分析
- 问题诊断
- 解决方案生成

## 开发指南

### 添加新功能
1. 在对应的API模块中添加路由
2. 在models中定义数据结构
3. 在services中实现业务逻辑
4. 添加相应的测试用例

### 代码规范
- 遵循PEP 8代码风格
- 使用类型注解
- 编写完整的文档字符串
- 保持模块职责单一

## 依赖关系

```
API Layer (routes) 
    ↓ 调用
Services Layer (business logic)
    ↓ 使用  
Models Layer (data access)
    ↓ 操作
Database Layer
```

工具和错误处理模块为各层提供横向支持。
