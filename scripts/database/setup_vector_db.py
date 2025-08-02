#!/usr/bin/env python3
"""
向量数据库设置脚本
帮助用户快速设置和配置向量数据库
"""
import os
import sys
import subprocess
from pathlib import Path


def print_header(text):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f" {text}")
    print(f"{'='*60}")


def print_step(step, text):
    """打印步骤"""
    print(f"\n🔧 步骤 {step}: {text}")


def check_requirements():
    """检查基础依赖"""
    print_step(1, "检查基础依赖")

    # 检查Python版本
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        print("❌ 需要Python 3.8或更高版本")
        return False

    print(f"✅ Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    return True


def install_dependencies():
    """安装依赖包"""
    print_step(2, "安装依赖包")

    try:
        # 安装基础依赖
        print("正在安装基础依赖...")
        root_dir = Path(__file__).parent.parent  # 指向项目根目录
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                      check=True, cwd=root_dir)

        # 安装Weaviate客户端
        print("正在安装Weaviate客户端...")
        subprocess.run([sys.executable, "-m", "pip", "install", "weaviate-client>=4.0.0"],
                      check=True)
        print("✅ Weaviate客户端安装成功")

        print("✅ 依赖安装完成")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        return False


def setup_environment():
    """设置环境变量"""
    print_step(3, "设置环境变量")

    env_file = Path(".env")
    env_example = Path(".env.vector.example")

    if not env_file.exists():
        if env_example.exists():
            print("正在创建.env文件...")
            with open(env_example, 'r') as f:
                content = f.read()
            with open(env_file, 'w') as f:
                f.write(content)
            print(f"✅ 已创建.env文件，请编辑配置")
        else:
            print("❌ 找不到.env.vector.example文件")
            return False

    # 检查关键配置
    if env_file.exists():
        with open(env_file, 'r') as f:
            content = f.read()

        if 'DASHSCOPE_API_KEY=your_dashscope_api_key' in content:
            print("⚠️  请在.env文件中设置你的DASHSCOPE_API_KEY")

        if 'VECTOR_DB_TYPE=' not in content:
            print("⚠️  请在.env文件中设置VECTOR_DB_TYPE")

    return True


def setup_weaviate():
    """设置Weaviate向量数据库"""
    print_step(4, "设置Weaviate向量数据库")

    print("使用Weaviate本地向量数据库")

    # 更新.env文件
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file, 'r') as f:
            content = f.read()

        # 更新VECTOR_DB_TYPE
        if 'VECTOR_DB_TYPE=' in content:
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('VECTOR_DB_TYPE='):
                    lines[i] = f'VECTOR_DB_TYPE=weaviate_local'
                    break
            content = '\n'.join(lines)
        else:
            content += f'\nVECTOR_DB_TYPE=weaviate_local\n'

        # 设置Weaviate URL
        if 'WEAVIATE_URL=' not in content:
            content += f'WEAVIATE_URL=http://localhost:8080\n'

        # 设置Weaviate类名
        if 'WEAVIATE_CLASS_NAME=' not in content:
            content += f'WEAVIATE_CLASS_NAME=KnowledgeChunk\n'

        with open(env_file, 'w') as f:
            f.write(content)

        print(f"✅ 已设置向量数据库类型为: weaviate_local")
        print(f"✅ Weaviate URL: http://localhost:8080")
        return True
    else:
        print("❌ .env文件不存在")
        return False


def create_directories():
    """创建必要的目录"""
    print_step(5, "创建必要的目录")

    directories = [
        "instance",
        "instance/weaviate_data",
        "logs"
    ]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ 创建目录: {directory}")

    return True


def test_setup():
    """测试设置"""
    print_step(6, "测试设置")

    try:
        # 设置PYTHONPATH
        root_dir = Path(__file__).parent.parent
        sys.path.insert(0, str(root_dir))
        os.environ['PYTHONPATH'] = str(root_dir)

        # 导入测试
        print("正在测试向量服务...")
        from app.services.vector_service import get_vector_service
        from app.services.vector_db_config import vector_db_config

        print(f"向量数据库类型: {vector_db_config.db_type.value}")
        print(f"配置是否有效: {vector_db_config.is_valid()}")

        vector_service = get_vector_service()
        if vector_service.test_connection():
            print("✅ 向量服务测试成功！")
            return True
        else:
            print("❌ 向量服务测试失败")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        print("💡 提示: 请确保已启动Weaviate服务器")
        print("   运行命令: python bin/mock_weaviate.py")
        return False


def main():
    """主函数"""
    print_header("IP智慧解答专家系统 - Weaviate向量数据库设置")

    print("本脚本将帮助您设置Weaviate向量数据库。")
    print("系统将使用Weaviate作为向量数据库，支持高性能的向量搜索。")

    steps = [
        check_requirements,
        install_dependencies,
        setup_environment,
        setup_weaviate,
        create_directories,
        test_setup
    ]

    for i, step_func in enumerate(steps, 1):
        if not step_func():
            print(f"\n❌ 设置在步骤 {i} 失败")
            return False

    print_header("设置完成")
    print("🎉 Weaviate向量数据库设置成功！")
    print("\n后续步骤:")
    print("1. 编辑.env文件，设置你的DASHSCOPE_API_KEY")
    print("2. 启动Weaviate服务: python bin/mock_weaviate.py")
    print("3. 运行 'flask test-vector' 测试连接")
    print("4. 运行 'flask run' 启动应用")
    print("5. 访问 http://localhost:5000/api/v1/vector/status 查看状态")

    return True


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户取消操作")
    except Exception as e:
        print(f"\n❌ 设置失败: {e}")
        sys.exit(1)
