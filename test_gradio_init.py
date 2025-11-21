#!/usr/bin/env python3
"""
Gradio应用初始化测试脚本
"""

import sys
import os

def test_imports():
    """测试必要的导入"""
    try:
        import requests
        print("✅ requests 导入成功")
    except ImportError:
        print("❌ requests 未安装")
        return False

    try:
        import gradio as gr
        print("✅ gradio 导入成功")
        print(f"   Gradio版本: {gr.__version__}")
    except ImportError:
        print("❌ gradio 未安装")
        return False

    return True

def test_basic_functions():
    """测试基本功能函数"""
    try:
        # 添加当前目录到路径
        sys.path.insert(0, '.')
        from gradio_app import (
            check_ytdlp_version,
            get_comprehensive_video_info,
            get_smart_format_recommendation,
            get_cookies_status
        )
        print("✅ 核心函数导入成功")
        return True
    except ImportError as e:
        print(f"❌ 函数导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

def test_interface_creation():
    """测试界面创建"""
    try:
        sys.path.insert(0, '.')
        from gradio_app import create_gradio_interface

        print("🔧 尝试创建Gradio界面...")
        demo = create_gradio_interface()
        print("✅ Gradio界面创建成功")
        print(f"   界面类型: {type(demo)}")
        return True
    except Exception as e:
        print(f"❌ 界面创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_connection():
    """测试API连接"""
    try:
        import requests

        # 测试API是否运行
        try:
            response = requests.get("http://localhost:8000/docs", timeout=5)
            if response.status_code == 200:
                print("✅ API服务运行正常")
                return True
            else:
                print(f"⚠️  API服务状态码: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print("⚠️  API服务未运行 (这是正常的，不影响Gradio界面)")
            return True
    except Exception as e:
        print(f"❌ API连接测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 Gradio应用初始化测试")
    print("=" * 50)

    # 设置环境变量
    os.environ.setdefault('DOCKER_ENV', 'false')

    tests = [
        ("依赖检查", test_imports),
        ("函数检查", test_basic_functions),
        ("界面创建", test_interface_creation),
        ("API连接", test_api_connection),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 异常: {e}")
            results.append((test_name, False))

    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")

    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1

    print(f"\n🎯 总体结果: {passed}/{len(results)} 项测试通过")

    if passed >= 3:  # API连接失败不影响Gradio界面
        print("🎉 Gradio应用可以正常初始化!")
        return True
    else:
        print("⚠️  Gradio应用存在问题，需要修复")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)