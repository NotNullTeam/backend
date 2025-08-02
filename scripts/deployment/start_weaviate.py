#!/usr/bin/env python3
"""
Weaviate服务启动脚本

用于开发环境启动模拟Weaviate服务器
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

if __name__ == "__main__":
    # 导入并启动模拟Weaviate服务器
    from bin.mock_weaviate import app

    print("🚀 启动Weaviate开发服务器...")
    print("📍 访问地址: http://localhost:8080")
    print("⚠️  这只是用于开发测试的模拟服务器")

    app.run(
        host='0.0.0.0',
        port=8080,
        debug=True
    )
