#!/usr/bin/env python3
"""
系统健康检查脚本

检查数据库连接、外部服务状态、磁盘空间等系统健康状况。
"""

import sys
import os
import psutil
import requests
from datetime import datetime
import argparse

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db

def check_database():
    """检查数据库连接"""
    print("🔍 检查数据库连接...")
    try:
        app = create_app()
        with app.app_context():
            # 尝试执行一个简单查询
            db.engine.execute('SELECT 1')
            print("✅ 数据库连接正常")
            return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

def check_redis():
    """检查Redis连接"""
    print("🔍 检查Redis连接...")
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis连接正常")
        return True
    except Exception as e:
        print(f"❌ Redis连接失败: {e}")
        return False

def check_weaviate():
    """检查Weaviate服务"""
    print("🔍 检查Weaviate服务...")
    try:
        response = requests.get('http://localhost:8080/v1/meta', timeout=5)
        if response.status_code == 200:
            print("✅ Weaviate服务正常")
            return True
        else:
            print(f"❌ Weaviate服务异常: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Weaviate服务连接失败: {e}")
        return False

def check_disk_space():
    """检查磁盘空间"""
    print("🔍 检查磁盘空间...")
    try:
        usage = psutil.disk_usage('/')
        free_percent = (usage.free / usage.total) * 100

        print(f"📊 磁盘使用情况:")
        print(f"   总空间: {usage.total // (1024**3):.1f} GB")
        print(f"   已使用: {usage.used // (1024**3):.1f} GB")
        print(f"   可用空间: {usage.free // (1024**3):.1f} GB ({free_percent:.1f}%)")

        if free_percent < 10:
            print("❌ 磁盘空间不足 (<10%)")
            return False
        elif free_percent < 20:
            print("⚠️ 磁盘空间警告 (<20%)")
            return True
        else:
            print("✅ 磁盘空间充足")
            return True
    except Exception as e:
        print(f"❌ 磁盘空间检查失败: {e}")
        return False

def check_memory():
    """检查内存使用情况"""
    print("🔍 检查内存使用...")
    try:
        memory = psutil.virtual_memory()

        print(f"📊 内存使用情况:")
        print(f"   总内存: {memory.total // (1024**3):.1f} GB")
        print(f"   已使用: {memory.used // (1024**3):.1f} GB ({memory.percent:.1f}%)")
        print(f"   可用内存: {memory.available // (1024**3):.1f} GB")

        if memory.percent > 90:
            print("❌ 内存使用过高 (>90%)")
            return False
        elif memory.percent > 80:
            print("⚠️ 内存使用警告 (>80%)")
            return True
        else:
            print("✅ 内存使用正常")
            return True
    except Exception as e:
        print(f"❌ 内存检查失败: {e}")
        return False

def check_log_errors():
    """检查日志文件中的错误"""
    print("🔍 检查日志错误...")
    try:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'logs')

        if not os.path.exists(log_dir):
            print("⚠️ 日志目录不存在")
            return True

        error_count = 0
        for log_file in os.listdir(log_dir):
            if log_file.endswith('.log'):
                log_path = os.path.join(log_dir, log_file)
                try:
                    with open(log_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        error_count += content.lower().count('error')
                        error_count += content.lower().count('exception')
                except Exception:
                    continue

        if error_count > 100:
            print(f"❌ 发现大量错误日志 ({error_count})")
            return False
        elif error_count > 10:
            print(f"⚠️ 发现一些错误日志 ({error_count})")
            return True
        else:
            print(f"✅ 错误日志正常 ({error_count})")
            return True
    except Exception as e:
        print(f"❌ 日志检查失败: {e}")
        return False

def generate_report(results):
    """生成健康检查报告"""
    print("\n" + "="*60)
    print("📋 系统健康检查报告")
    print("="*60)
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    total_checks = len(results)
    passed_checks = sum(1 for result in results.values() if result)

    for check_name, result in results.items():
        status = "✅ 正常" if result else "❌ 异常"
        print(f"{check_name}: {status}")

    print()
    print(f"总检查项: {total_checks}")
    print(f"通过检查: {passed_checks}")
    print(f"健康度: {(passed_checks/total_checks)*100:.1f}%")

    if passed_checks == total_checks:
        print("\n🎉 系统运行良好！")
        return 0
    elif passed_checks >= total_checks * 0.8:
        print("\n⚠️ 系统基本正常，但有些问题需要注意")
        return 1
    else:
        print("\n❌ 系统存在严重问题，需要立即处理")
        return 2

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='系统健康检查工具')
    parser.add_argument('--skip-external', action='store_true', help='跳过外部服务检查')

    args = parser.parse_args()

    print("🔍 开始系统健康检查...")
    print()

    results = {}

    # 基础检查
    results['数据库连接'] = check_database()
    results['磁盘空间'] = check_disk_space()
    results['内存使用'] = check_memory()
    results['日志错误'] = check_log_errors()

    # 外部服务检查
    if not args.skip_external:
        results['Redis服务'] = check_redis()
        results['Weaviate服务'] = check_weaviate()

    # 生成报告
    exit_code = generate_report(results)
    sys.exit(exit_code)

if __name__ == '__main__':
    main()
