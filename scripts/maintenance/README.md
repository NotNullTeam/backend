# 维护脚本

本目录包含系统维护、监控和数据管理相关的脚本。

## 脚本说明

### `backup_data.py` - 数据备份
创建数据库和重要文件的备份，支持定期清理旧备份。

```bash
# 创建备份
python scripts/maintenance/backup_data.py

# 清理30天前的备份
python scripts/maintenance/backup_data.py --cleanup-days 30

# 指定备份目录
python scripts/maintenance/backup_data.py --backup-dir /path/to/backup
```

### `health_check.py` - 系统健康检查
检查系统各组件的运行状态，包括数据库、Redis、向量数据库等。

```bash
# 运行健康检查
python scripts/maintenance/health_check.py

# 详细检查报告
python scripts/maintenance/health_check.py --verbose

# 导出检查结果
python scripts/maintenance/health_check.py --output health_report.json
```

## 维护建议

- 定期运行健康检查确保系统正常
- 设置自动备份任务
- 监控系统资源使用情况
- 及时清理过期的日志和备份文件

## 监控指标

- 数据库连接状态
- Redis服务状态
- Weaviate向量数据库状态
- 磁盘空间使用率
- 内存使用情况
- 日志错误统计
