# 部署脚本

本目录包含生产环境部署和服务管理相关的脚本。

## 脚本说明

### `start_weaviate.py` - Weaviate服务启动
启动和管理Weaviate向量数据库服务。

```bash
python scripts/deployment/start_weaviate.py
```

### `worker.py` - RQ Worker进程
启动Redis Queue (RQ) Worker进程，处理后台任务。

```bash
# 启动单个worker
python scripts/deployment/worker.py

# 启动多个worker
python scripts/deployment/worker.py --workers 4
```

## 部署流程

1. 确保Redis服务运行正常
2. 启动Weaviate向量数据库
3. 运行数据库初始化脚本
4. 启动RQ Worker进程
5. 启动主应用服务

## 生产环境注意事项

- 确保所有服务的配置文件正确
- 监控服务运行状态和资源使用情况
- 定期备份重要数据
- 配置适当的日志级别和轮转策略
