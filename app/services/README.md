# 服务模块

## 目录结构

```
app/services/
├── __init__.py                    # 主入口，导入所有子模块
├── ai/                           # AI相关服务
│   ├── __init__.py
│   ├── llm_service.py           # 大语言模型服务
│   ├── embedding_service.py     # 文本向量化服务
│   ├── agent_service.py         # AI Agent异步任务处理
│   ├── langgraph_agent_service.py # LangGraph智能对话Agent
│   ├── agent_nodes.py           # Agent节点定义
│   ├── agent_state.py           # Agent状态管理
│   ├── agent_workflow.py        # Agent工作流
│   └── log_parsing_service.py   # AI日志解析服务
├── document/                     # 文档处理服务
│   ├── __init__.py
│   ├── document_service.py      # 文档解析服务
│   ├── idp_service.py          # 阿里云文档智能服务
│   ├── idp_service_new.py      # 新版IDP服务
│   ├── semantic_splitter.py    # 语义分割服务
│   └── idp_task_processor.py   # IDP任务处理器
├── storage/                      # 存储服务
│   ├── __init__.py
│   ├── cache_service.py         # Redis缓存服务
│   ├── vector_db_config.py     # 向量数据库配置
│   ├── weaviate_vector_db.py   # Weaviate向量数据库
│   └── local_vector_db.py      # 本地向量数据库
├── retrieval/                    # 检索服务
│   ├── __init__.py
│   ├── vector_service.py        # 向量服务
│   ├── hybrid_retrieval.py     # 混合检索服务
│   └── knowledge_service.py     # 统一知识检索服务
├── network/                      # 网络设备服务
│   ├── __init__.py
│   └── vendor_command_service.py # 厂商命令生成服务
└── infrastructure/               # 基础设施服务
    ├── __init__.py
    └── task_monitor.py          # 任务监控和重试机制
```

## 服务分类说明

### 1. AI服务 (`ai/`)
- **LLM服务**: 处理与大语言模型的交互，包括问题分析、解决方案生成等
- **嵌入服务**: 文本向量化处理，集成阿里云百炼平台
- **Agent服务**: AI Agent相关的异步任务处理和检索服务
- **LangGraph Agent**: 智能对话Agent，提供结构化的多轮对话能力
- **Agent节点**: Agent工作流中的各种节点定义
- **Agent状态**: Agent运行时的状态管理
- **Agent工作流**: 完整的Agent执行工作流
- **日志解析服务**: AI驱动的网络设备日志智能分析

### 2. 文档处理服务 (`document/`)
- **文档服务**: 文档解析和处理的主要服务
- **IDP服务**: 阿里云文档智能处理服务
- **语义分割**: 文档内容的智能分割处理
- **任务处理器**: 文档处理任务的管理和执行

### 3. 存储服务 (`storage/`)
- **缓存服务**: Redis缓存管理，提高LLM响应性能
- **向量数据库**: Weaviate和本地向量数据库的实现
- **数据库配置**: 向量数据库的配置管理

### 4. 检索服务 (`retrieval/`)
- **向量服务**: 向量数据库的操作和管理
- **混合检索**: 结合多种检索策略的智能检索
- **知识服务**: 统一的知识检索接口，支持数据库查询和向量搜索

### 5. 网络设备服务 (`network/`)
- **厂商命令服务**: 根据网络问题分析生成特定厂商设备的配置命令

### 6. 基础设施服务 (`infrastructure/`)
- **任务监控**: 异步任务的监控和重试机制

## 导入方式

### 直接导入特定服务
```python
from app.services.ai.llm_service import LLMService
from app.services.ai.log_parsing_service import LogParsingService
from app.services.document.idp_service import IDPService
from app.services.storage.cache_service import get_cache_service
from app.services.retrieval.vector_service import get_vector_service
from app.services.retrieval.knowledge_service import KnowledgeService
from app.services.network.vendor_command_service import VendorCommandService
from app.services.infrastructure.task_monitor import with_monitoring_and_retry
```

### 通过主模块导入（推荐）
```python
from app.services import (
    LLMService,
    LogParsingService,
    IDPService,
    get_cache_service,
    cache_service,
    cached_llm_call,
    cached_retrieval_call,
    get_vector_service,
    KnowledgeService,
    VendorCommandService,
    with_monitoring_and_retry
)
```
