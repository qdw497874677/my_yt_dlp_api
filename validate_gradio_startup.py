#!/usr/bin/env python3
"""
Gradio启动配置验证脚本
验证Docker环境中的Gradio是否能正确启动
"""

import os
import sys
from pathlib import Path

def test_gradio_file_structure():
    """测试Gradio文件结构"""
    print("🔍 测试Gradio文件结构...")

    # 检查必要文件
    required_files = [
        'gradio_app.py',
        'main.py',
        'Dockerfile',
        'supervisord.conf',
        'docker-compose.yml'
    ]

    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)

    if missing_files:
        print(f"❌ 缺少文件: {missing_files}")
        return False
    else:
        print("✅ 所有必要文件存在")

    return True

def test_gradio_syntax():
    """测试Gradio文件语法"""
    print("\n🔍 测试Gradio语法...")

    try:
        with open('gradio_app.py', 'r') as f:
            gradio_code = f.read()

        # 检查必要的函数和组件
        required_elements = [
            'def create_gradio_interface()',
            'with gr.Blocks(',
            'demo.launch(',
            'if __name__ == "__main__":',
            'server_name="0.0.0.0"',
            'server_port=7860'
        ]

        missing_elements = []
        for element in required_elements:
            if element not in gradio_code:
                missing_elements.append(element)

        if missing_elements:
            print(f"❌ Gradio文件缺少: {missing_elements}")
            return False
        else:
            print("✅ Gradio文件结构正确")

        # 检查语法
        compile(gradio_code, 'gradio_app.py', 'exec')
        print("✅ Gradio语法检查通过")

        return True

    except Exception as e:
        print(f"❌ Gradio语法检查失败: {e}")
        return False

def test_supervisor_configuration():
    """测试supervisor配置"""
    print("\n🔍 测试supervisor配置...")

    try:
        with open('supervisord.conf', 'r') as f:
            supervisor_config = f.read()

        required_programs = [
            '[program:fastapi]',
            '[program:gradio]',
            'python main.py',
            'python gradio_app.py'
        ]

        missing_programs = []
        for program in required_programs:
            if program not in supervisor_config:
                missing_programs.append(program)

        if missing_programs:
            print(f"❌ supervisor配置缺少: {missing_programs}")
            return False
        else:
            print("✅ supervisor配置正确")

        return True

    except Exception as e:
        print(f"❌ supervisor配置检查失败: {e}")
        return False

def test_docker_integration():
    """测试Docker集成配置"""
    print("\n🔍 测试Docker集成...")

    try:
        # 检查Dockerfile
        with open('Dockerfile', 'r') as f:
            dockerfile_content = f.read()

        docker_requirements = [
            'supervisor',
            'supervisord.conf',
            '/usr/bin/supervisord',
            'EXPOSE 8000 7860'
        ]

        missing_docker = []
        for req in docker_requirements:
            if req not in dockerfile_content:
                missing_docker.append(req)

        if missing_docker:
            print(f"❌ Dockerfile缺少: {missing_docker}")
            return False
        else:
            print("✅ Dockerfile配置正确")

        # 检查docker-compose.yml
        with open('docker-compose.yml', 'r') as f:
            compose_content = f.read()

        compose_requirements = [
            '"18000:8000"',
            '"17860:7860"',
            'API_BASE_URL=http://localhost:8000',
            'GRADIO_SERVER_NAME=0.0.0.0'
        ]

        missing_compose = []
        for req in compose_requirements:
            if req not in compose_content:
                missing_compose.append(req)

        if missing_compose:
            print(f"❌ docker-compose.yml缺少: {missing_compose}")
            return False
        else:
            print("✅ docker-compose.yml配置正确")

        return True

    except Exception as e:
        print(f"❌ Docker集成检查失败: {e}")
        return False

def test_gradio_startup_logic():
    """测试Gradio启动逻辑"""
    print("\n🔍 测试Gradio启动逻辑...")

    try:
        with open('gradio_app.py', 'r') as f:
            gradio_content = f.read()

        # 检查启动逻辑
        startup_checks = [
            'demo = create_gradio_interface()',
            'demo.launch(',
            'server_name="0.0.0.0"',
            'server_port=7860',
            'prevent_thread_lock=False'
        ]

        missing_startup = []
        for check in startup_checks:
            if check not in gradio_content:
                missing_startup.append(check)

        if missing_startup:
            print(f"❌ 启动逻辑缺少: {missing_startup}")
            return False
        else:
            print("✅ Gradio启动逻辑正确")

        return True

    except Exception as e:
        print(f"❌ 启动逻辑检查失败: {e}")
        return False

def generate_gradio_startup_report(tests):
    """生成Gradio启动报告"""
    print("\n" + "="*60)
    print("🎯 GRADIO启动配置验证报告")
    print("="*60)

    total_tests = len(tests)
    passed_tests = sum(tests.values())
    failed_tests = total_tests - passed_tests

    print(f"\n📊 测试摘要: {passed_tests}/{total_tests} 测试通过")

    if failed_tests == 0:
        print("🎉 所有测试通过！Gradio应该能正确启动。")
    else:
        print(f"⚠️ {failed_tests} 个测试失败。")

    print("\n📋 测试结果:")
    for test_name, passed in tests.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {status} - {test_name}")

    print("\n🚀 启动确认:")
    if failed_tests == 0:
        print("  ✅ Gradio应用结构正确")
        print("  ✅ Supervisor进程管理配置完善")
        print("  ✅ Docker环境变量正确")
        print("  ✅ 启动逻辑完整")
        print("  ✅ 端口映射配置正确")
        print("\n📚 预期启动行为:")
        print("  1. Docker容器启动时，supervisor会同时启动:")
        print("     - FastAPI服务 (端口8000)")
        print("     - Gradio应用 (端口7860)")
        print("  2. 用户可通过以下地址访问:")
        print("     - API文档: http://localhost:18000/docs")
        print("     - Gradio界面: http://localhost:17860")
        print("     - YouTube登录: Gradio中的'🔐 YouTube登录'标签")
    else:
        print("  ❌ 需要修复失败的测试")
        print("  ❌ 建议重新运行验证直到所有测试通过")

    return failed_tests == 0

def main():
    """主验证函数"""
    print("🎨 开始Gradio启动配置验证...")
    print("=" * 60)

    # 运行所有测试
    test_results = {
        "Gradio文件结构": test_gradio_file_structure(),
        "Gradio语法检查": test_gradio_syntax(),
        "Supervisor配置": test_supervisor_configuration(),
        "Docker集成": test_docker_integration(),
        "Gradio启动逻辑": test_gradio_startup_logic(),
    }

    # 生成报告
    success = generate_gradio_startup_report(test_results)

    # 返回适当的退出代码
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()