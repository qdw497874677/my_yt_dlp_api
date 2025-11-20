#!/usr/bin/env python3
"""
Docker中Gradio启动问题诊断脚本
用于诊断和修复Docker环境中Gradio无法启动的问题
"""

import os
import sys
import subprocess
from pathlib import Path

def test_gradio_import():
    """测试Gradio导入"""
    print("🔍 测试Gradio导入...")

    try:
        import gradio as gr
        version = gr.__version__
        print(f"✅ Gradio导入成功，版本: {version}")
        return True
    except ImportError as e:
        print(f"❌ Gradio导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ Gradio导入异常: {e}")
        return False

def test_gradio_app_syntax():
    """测试Gradio应用语法"""
    print("\n🔍 测试Gradio应用语法...")

    try:
        with open('gradio_app.py', 'r') as f:
            gradio_code = f.read()

        # 检查语法
        compile(gradio_code, 'gradio_app.py', 'exec')
        print("✅ gradio_app.py语法检查通过")
        return True
    except SyntaxError as e:
        print(f"❌ 语法错误: {e}")
        print(f"行号: {e.lineno}, 位置: {e.offset}")
        return False
    except Exception as e:
        print(f"❌ 语法检查失败: {e}")
        return False

def test_supervisor_config():
    """测试supervisor配置"""
    print("\n🔍 测试supervisor配置...")

    try:
        with open('supervisord.conf', 'r') as f:
            supervisor_config = f.read()

        # 检查关键配置
        required_configs = [
            '[program:gradio]',
            'command=python gradio_app.py',
            'autostart=true',
            'autorestart=true',
            'startsecs=30',
        ]

        missing_configs = []
        for config in required_configs:
            if config not in supervisor_config:
                missing_configs.append(config)

        if missing_configs:
            print(f"❌ supervisor配置缺少: {missing_configs}")
            return False
        else:
            print("✅ supervisor配置正确")
            return True
    except Exception as e:
        print(f"❌ supervisor配置检查失败: {e}")
        return False

def test_dockerfile():
    """测试Dockerfile"""
    print("\n🔍 测试Dockerfile...")

    try:
        with open('Dockerfile', 'r') as f:
            dockerfile_content = f.read()

        # 检查关键配置
        required_docker = [
            'supervisor',
            'supervisord.conf',
            '/usr/bin/supervisord',
            'EXPOSE 7860',
        ]

        missing_docker = []
        for docker in required_docker:
            if docker not in dockerfile_content:
                missing_docker.append(docker)

        if missing_docker:
            print(f"❌ Dockerfile缺少: {missing_docker}")
            return False
        else:
            print("✅ Dockerfile配置正确")
            return True
    except Exception as e:
        print(f"❌ Dockerfile检查失败: {e}")
        return False

def test_gradio_startup_logic():
    """测试Gradio启动逻辑"""
    print("\n🔍 测试Gradio启动逻辑...")

    try:
        with open('gradio_app.py', 'r') as f:
            gradio_content = f.read()

        # 检查启动逻辑
        required_logic = [
            'if __name__ == "__main__":',
            'demo = create_gradio_interface()',
            'demo.launch(',
            'server_name="0.0.0.0"',
            'server_port=7860',
            'prevent_thread_lock=True',
            'while True:',
            'time.sleep(1)',
        ]

        missing_logic = []
        for logic in required_logic:
            if logic not in gradio_content:
                missing_logic.append(logic)

        if missing_logic:
            print(f"❌ Gradio启动逻辑缺少: {missing_logic}")
            return False
        else:
            print("✅ Gradio启动逻辑正确")
            return True
    except Exception as e:
        print(f"❌ 启动逻辑检查失败: {e}")
        return False

def test_dependency_availability():
    """测试依赖可用性"""
    print("\n🔍 测试关键依赖...")

    dependencies = {
        'gradio': 'gradio as gr',
        'requests': 'requests',
        'yt-dlp': 'yt_dlp',
    }

    failed_deps = []
    for dep_name, import_name in dependencies.items():
        try:
            if dep_name == 'yt-dlp':
                import yt_dlp
                print(f"✅ {dep_name}: {yt_dlp.__version__}")
            else:
                exec(f"import {import_name}")
                print(f"✅ {dep_name}: 可用")
        except ImportError as e:
            print(f"❌ {dep_name}: 导入失败 - {e}")
            failed_deps.append(dep_name)
        except Exception as e:
            print(f"⚠️ {dep_name}: 异常 - {e}")
            failed_deps.append(dep_name)

    return len(failed_deps) == 0

def generate_docker_diagnostic_report(tests):
    """生成Docker诊断报告"""
    print("\n" + "="*60)
    print("🎯 Docker Gradio启动诊断报告")
    print("="*60)

    total_tests = len(tests)
    passed_tests = sum(tests.values())
    failed_tests = total_tests - passed_tests

    print(f"\n📊 诊断摘要: {passed_tests}/{total_tests} 测试通过")

    if failed_tests == 0:
        print("🎉 所有诊断通过！Gradio应该能正常启动。")
    else:
        print(f"⚠️ {failed_tests} 个测试失败，需要修复。")

    print("\n📋 诊断结果:")
    for test_name, passed in tests.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {status} - {test_name}")

    print("\n🚀 Docker部署建议:")
    if failed_tests == 0:
        print("  ✅ 配置正确，可以部署到Docker")
        print("  📋 部署命令:")
        print("    docker-compose build")
        print("    docker-compose up -d")
        print("    docker-compose logs -f gradio")
        print("\n  🔍 验证服务:")
        print("    docker-compose exec yt-dlp-api-service supervisorctl status")
        print("    curl http://localhost:17860")
    else:
        print("  ❌ 需要修复失败的项目")
        print("  🔧 建议按照错误信息逐一修复")
        print("  🔄 修复后重新运行诊断")

    return failed_tests == 0

def main():
    """主诊断函数"""
    print("🐳 开始Docker Gradio启动诊断...")
    print("=" * 60)

    # 运行所有诊断
    diagnostic_results = {
        "Gradio导入测试": test_gradio_import(),
        "Gradio应用语法": test_gradio_app_syntax(),
        "Supervisor配置": test_supervisor_config(),
        "Dockerfile配置": test_dockerfile(),
        "Gradio启动逻辑": test_gradio_startup_logic(),
        "关键依赖可用性": test_dependency_availability(),
    }

    # 生成报告
    success = generate_docker_diagnostic_report(diagnostic_results)

    # 返回适当的退出代码
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()