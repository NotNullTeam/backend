# 数据库管理脚本

本目录包含数据库初始化、配置和维护相关的脚本。

## 脚本说明

### `init_db.py` - 数据库初始化
初始化SQLite数据库，创建所有必要的表结构。

```bash
python scripts/database/init_db.py
```

### `setup_vector_db.py` - 向量数据库设置
配置和初始化Weaviate向量数据库，创建必要的集合和索引。

```bash
python scripts/database/setup_vector_db.py
```

## 使用注意事项

- 首次部署时务必运行数据库初始化脚本
- 向量数据库设置需要确保Weaviate服务已启动
- 生产环境使用前请备份现有数据
