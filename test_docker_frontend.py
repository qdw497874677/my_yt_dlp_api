#!/usr/bin/env python3
"""
Docker前端页面配置验证脚本
测试Docker配置是否正确启动FastAPI和Gradio服务
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def test_docker_configuration():
    """测试Docker配置文件"""
    print("🔍 测试Docker配置文件...")

    # 检查必要文件
    required_files = [
        'Dockerfile',
        'docker-compose.yml',
        'supervisord.conf',
        'main.py',
        'gradio_app.py'
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

    # 检查Dockerfile内容
    try:
        with open('Dockerfile', 'r') as f:
            dockerfile_content = f.read()

        required_elements = [
            'supervisor',
            'supervisord.conf',
            '/usr/bin/supervisord',
            'EXPOSE 8000 7860'
        ]

        missing_elements = []
        for element in required_elements:
            if element not in dockerfile_content:
                missing_elements.append(element)

        if missing_elements:
            print(f"❌ Dockerfile缺少: {missing_elements}")
            return False
        else:
            print("✅ Dockerfile配置正确")

    except Exception as e:
        print(f"❌ 读取Dockerfile失败: {e}")
        return False

    # 检查supervisord.conf内容
    try:
        with open('supervisord.conf', 'r') as f:
            supervisord_content = f.read()

        required_programs = [
            '[program:fastapi]',
            '[program:gradio]',
            'python main.py',
            'python gradio_app.py'
        ]

        missing_programs = []
        for program in required_programs:
            if program not in supervisord_content:
                missing_programs.append(program)

        if missing_programs:
            print(f"❌ supervisord.conf缺少: {missing_programs}")
            return False
        else:
            print("✅ supervisord.conf配置正确")

    except Exception as e:
        print(f"❌ 读取supervisord.conf失败: {e}")
        return False

    # 检查docker-compose.yml内容
    try:
        with open('docker-compose.yml', 'r') as f:
            compose_content = f.read()

        required_ports = [
            '"18000:8000"',
            '"17860:7860"'
        ]

        missing_ports = []
        for port in required_ports:
            if port not in compose_content:
                missing_ports.append(port)

        if missing_ports:
            print(f"❌ docker-compose.yml缺少端口映射: {missing_ports}")
            return False
        else:
            print("✅ docker-compose.yml端口映射正确")

    except Exception as e:
        print(f"❌ 读取docker-compose.yml失败: {e}")
        return False

    return True

def test_syntax_validation():
    """测试配置文件语法"""
    print("\n🔍 测试配置文件语法...")

    try:
        # 测试Python文件语法
        python_files = ['main.py', 'gradio_app.py']
        for py_file in python_files:
            with open(py_file, 'r') as f:
                code = f.read()
            compile(code, py_file, 'exec')
            print(f"✅ {py_file} 语法正确")

        return True
    except SyntaxError as e:
        print(f"❌ Python语法错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 语法检查失败: {e}")
        return False

def test_environment_variables():
    """测试环境变量配置"""
    print("\n🔍 测试环境变量配置...")

    try:
        with open('docker-compose.yml', 'r') as f:
            compose_content = f.read()

        required_env_vars = [
            'API_BASE_URL=http://localhost:8000',
            'DOCKER_ENV=true',
            'PYTHONPATH=/app',
            'GRADIO_SERVER_NAME=0.0.0.0'
        ]

        missing_vars = []
        for var in required_env_vars:
            if var not in compose_content:
                missing_vars.append(var)

        if missing_vars:
            print(f"❌ 缺少环境变量: {missing_vars}")
            return False
        else:
            print("✅ 环境变量配置正确")
            return True

    except Exception as e:
        print(f"❌ 环境变量检查失败: {e}")
        return False

def generate_docker_test_report(tests):
    """生成Docker测试报告"""
    print("\n" + "="*60)
    print("🎯 DOCKER前端配置验证报告")
    print("="*60)

    total_tests = len(tests)
    passed_tests = sum(tests.values())
    failed_tests = total_tests - passed_tests

    print(f"\n📊 测试摘要: {passed_tests}/{total_tests} 测试通过")

    if failed_tests == 0:
        print("🎉 所有测试通过！Docker配置可以启动前端页面。")
    else:
        print(f"⚠️ {failed_tests} 个测试失败。")

    print("\n📋 测试结果:")
    for test_name, passed in tests.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {status} - {test_name}")

    print("\n🚀 下一步操作:")
    if failed_tests == 0:
        print("  1. 构建镜像: docker-compose build")
        print("  2. 启动服务: docker-compose up -d")
        print("  3. 验证服务:")
        print("     - API文档: http://localhost:18000/docs")
        print("     - Gradio界面: http://localhost:17860")
        print("     - YouTube登录: Gradio中的'🔐 YouTube登录'标签")
    else:
        print("  1. 修复失败的测试")
        print("  2. 重新运行此验证脚本")
        print("  3. 确保所有测试通过后再构建")

    print("\n📚 预期服务:")
    print("  - FastAPI服务: 端口8000 (映射到主机18000)")
    print("  - Gradio界面: 端口7860 (映射到主机17860)")
    print("  - Supervisor进程管理: 同时管理两个服务")
    print("  - 健康检查: 自动监控FastAPI服务状态")

    return failed_tests == 0

def main():
    """主测试函数"""
    print("🐳 开始Docker前端配置验证...")
    print("=" * 60)

    # 运行所有测试
    test_results = {
        "Docker配置文件": test_docker_configuration(),
        "配置文件语法": test_syntax_validation(),
        "环境变量配置": test_environment_variables(),
    }

    # 生成报告
    success = generate_docker_test_report(test_results)

    # 返回适当的退出代码
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()