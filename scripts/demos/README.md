# 演示脚本

本目录包含各种功能演示和使用示例脚本。

## 脚本说明

### `demo_hybrid_retrieval.py` - 混合检索演示
演示混合检索算法的功能，包括向量检索和关键词检索的结合。

```bash
# 运行基本演示
python scripts/demos/demo_hybrid_retrieval.py

# 使用自定义查询
python scripts/demos/demo_hybrid_retrieval.py --query "您的查询内容"

# 调整检索参数
python scripts/demos/demo_hybrid_retrieval.py --top-k 10 --weight-vector 0.7
```

## 演示功能

- 向量相似度检索
- 关键词匹配检索
- 混合结果重排序
- 结果质量评估
- 性能基准测试

## 使用场景

- 新功能展示
- 算法效果验证
- 参数调优参考
- 用户培训演示
