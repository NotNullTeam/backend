"""
IP智慧解答专家系统 - RQ Worker

本模块实现RQ任务队列的worker进程，用于处理异步任务。
"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rq import Worker, Connection
from app import create_app
from app.services import get_redis_connection

def main():
    """启动RQ Worker进程"""
    # 创建Flask应用上下文
    app = create_app()
    
    with app.app_context():
        # 获取Redis连接
        redis_conn = get_redis_connection()
        
        # 创建Worker实例
        worker = Worker(['default'], connection=redis_conn)
        
        print("🚀 启动RQ Worker进程...")
        print(f"📡 Redis连接: {app.config['REDIS_URL']}")
        print("📋 监听队列: default")
        print("⏳ 等待任务...")
        
        try:
            # 启动worker
            worker.work()
        except KeyboardInterrupt:
            print("\n⏹️  Worker进程已停止")
            sys.exit(0)
        except Exception as e:
            print(f"❌ Worker进程错误: {str(e)}")
            sys.exit(1)

if __name__ == '__main__':
    main()
