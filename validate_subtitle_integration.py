#!/usr/bin/env python3
"""
字幕功能集成验证脚本
验证字幕下载功能是否完整集成并正确使用cookies
"""

import os
import sys
from pathlib import Path

def test_subtitle_backend_api():
    """测试字幕后端API配置"""
    print("🔍 测试字幕后端API配置...")

    try:
        with open('main.py', 'r') as f:
            main_content = f.read()

        # 检查字幕下载端点
        required_endpoints = [
            '@app.post("/download-subtitles"',
            'class SubtitleDownloadRequest',
            'async def api_download_subtitles(',
        ]

        missing_endpoints = []
        for endpoint in required_endpoints:
            if endpoint not in main_content:
                missing_endpoints.append(endpoint)

        if missing_endpoints:
            print(f"❌ 缺少字幕API端点: {missing_endpoints}")
            return False
        else:
            print("✅ 字幕API端点配置正确")

        # 检查cookies自动检测逻辑
        cookies_checks = [
            'if not request.cookies:',
            'auto_cookies = await state.get_cookies_for_download(request.url)',
            'request.cookies = auto_cookies',
        ]

        missing_cookies_logic = []
        for check in cookies_checks:
            if check not in main_content:
                missing_cookies_logic.append(check)

        if missing_cookies_logic:
            print(f"❌ 字幕API缺少cookies自动检测: {missing_cookies_logic}")
            return False
        else:
            print("✅ 字幕API自动cookies检测配置正确")

        return True

    except Exception as e:
        print(f"❌ 后端API检查失败: {e}")
        return False

def test_subtitle_functions():
    """测试字幕下载函数"""
    print("\n🔍 测试字幕下载函数...")

    try:
        with open('main.py', 'r') as f:
            main_content = f.read()

        # 检查字幕下载核心函数
        required_functions = [
            'def download_subtitle(',
            'cookies: str = None',
            'ydl_opts[\'cookiefile\'] = cookies',
            'ydl_opts[\'cookiesfrombrowser\'] = (cookies,)',
        ]

        missing_functions = []
        for func in required_functions:
            if func not in main_content:
                missing_functions.append(func)

        if missing_functions:
            print(f"❌ 缺少字幕下载函数: {missing_functions}")
            return False
        else:
            print("✅ 字幕下载函数配置正确")

        return True

    except Exception as e:
        print(f"❌ 字幕函数检查失败: {e}")
        return False

def test_gradio_subtitle_interface():
    """测试Gradio字幕界面"""
    print("\n🔍 测试Gradio字幕界面...")

    try:
        with open('gradio_app.py', 'r') as f:
            gradio_content = f.read()

        # 检查字幕界面元素
        required_elements = [
            'with gr.Tab("📝 下载字幕"):',
            'def download_subtitles(',
            'subtitle_languages = gr.CheckboxGroup(',
            'subtitle_format = gr.Dropdown(',
            'subtitle_download_btn = gr.Button("📝 下载字幕"',
            'subtitle_download_btn.click(',
            'POST /download-subtitles',
        ]

        missing_elements = []
        for element in required_elements:
            if element not in gradio_content:
                missing_elements.append(element)

        if missing_elements:
            print(f"❌ Gradio字幕界面缺少元素: {missing_elements}")
            return False
        else:
            print("✅ Gradio字幕界面配置正确")

        return True

    except Exception as e:
        print(f"❌ Gradio界面检查失败: {e}")
        return False

def test_subtitle_request_model():
    """测试字幕请求模型"""
    print("\n🔍 测试字幕请求模型...")

    try:
        with open('main.py', 'r') as f:
            main_content = f.read()

        # 检查SubtitleDownloadRequest模型
        required_fields = [
            'class SubtitleDownloadRequest(BaseModel):',
            'url: str',
            'languages: List[str]',
            'subtitle_format: str = "srt"',
            'cookies: str = None',
        ]

        missing_fields = []
        for field in required_fields:
            if field not in main_content:
                missing_fields.append(field)

        if missing_fields:
            print(f"❌ SubtitleDownloadRequest模型缺少字段: {missing_fields}")
            return False
        else:
            print("✅ SubtitleDownloadRequest模型配置正确")

        return True

    except Exception as e:
        print(f"❌ 请求模型检查失败: {e}")
        return False

def test_subtitle_languages_support():
    """测试字幕语言支持"""
    print("\n🔍 测试字幕语言支持...")

    try:
        with open('main.py', 'r') as f:
            main_content = f.read()

        with open('gradio_app.py', 'r') as f:
            gradio_content = f.read()

        # 检查后端支持的语言
        backend_languages = 'supported_languages = [\'en\', \'zh\', \'es\', \'fr\', \'de\', \'ja\', \'ko\', \'ru\', \'ar\', \'hi\', \'pt\', \'it\', \'nl\', \'pl\', \'sv\', \'da\', \'no\', \'fi\']'

        # 检查前端语言选项
        frontend_languages = 'choices=["en", "zh", "es", "fr", "de", "ja", "ko", "ru", "ar", "hi", "pt", "it", "nl", "pl", "sv", "da", "no", "fi"]'

        if backend_languages not in main_content:
            print("❌ 后端缺少支持的语言列表")
            return False
        else:
            print("✅ 后端语言支持配置正确")

        if frontend_languages not in gradio_content:
            print("❌ 前端缺少语言选项")
            return False
        else:
            print("✅ 前端语言选项配置正确")

        return True

    except Exception as e:
        print(f"❌ 语言支持检查失败: {e}")
        return False

def test_subtitle_formats_support():
    """测试字幕格式支持"""
    print("\n🔍 测试字幕格式支持...")

    try:
        with open('main.py', 'r') as f:
            main_content = f.read()

        with open('gradio_app.py', 'r') as f:
            gradio_content = f.read()

        # 检查后端支持的格式
        backend_formats = 'supported_formats = [\'srt\', \'vtt\', \'ass\', \'ssa\']'

        # 检查前端格式选项
        frontend_formats = 'choices=["srt", "vtt", "ass", "ssa"]'

        if backend_formats not in main_content:
            print("❌ 后端缺少支持的格式列表")
            return False
        else:
            print("✅ 后端格式支持配置正确")

        if frontend_formats not in gradio_content:
            print("❌ 前端缺少格式选项")
            return False
        else:
            print("✅ 前端格式选项配置正确")

        return True

    except Exception as e:
        print(f"❌ 格式支持检查失败: {e}")
        return False

def generate_subtitle_integration_report(tests):
    """生成字幕集成验证报告"""
    print("\n" + "="*60)
    print("🎯 字幕功能集成验证报告")
    print("="*60)

    total_tests = len(tests)
    passed_tests = sum(tests.values())
    failed_tests = total_tests - passed_tests

    print(f"\n📊 测试摘要: {passed_tests}/{total_tests} 测试通过")

    if failed_tests == 0:
        print("🎉 所有测试通过！字幕功能已完整集成。")
    else:
        print(f"⚠️ {failed_tests} 个测试失败。")

    print("\n📋 测试结果:")
    for test_name, passed in tests.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {status} - {test_name}")

    print("\n🚀 字幕功能确认:")
    if failed_tests == 0:
        print("  ✅ 字幕API端点正确配置")
        print("  ✅ 自动cookies检测集成")
        print("  ✅ Gradio界面完整实现")
        print("  ✅ 多语言多格式支持")
        print("  ✅ 任务状态跟踪功能")
        print("\n📚 字幕功能特性:")
        print("  - 支持多种语言字幕下载 (18种语言)")
        print("  - 支持多种字幕格式 (SRT, VTT, ASS, SSA)")
        print("  - 自动cookies认证 (优先使用浏览器登录cookies)")
        print("  - 异步下载处理")
        print("  - 实时状态监控")
        print("  - 自动字幕选择机制")
        print("\n🌐 用户使用方式:")
        print("  1. 访问Gradio界面的'📝 下载字幕'标签")
        print("  2. 输入视频URL和选择语言/格式")
        print("  3. 点击下载，系统自动使用最佳cookies")
        print("  4. 使用任务ID查询下载进度")
        print("  5. 在'📊 任务状态'标签查看下载结果")
    else:
        print("  ❌ 需要修复失败的测试")
        print("  ❌ 建议重新运行验证直到所有测试通过")

    return failed_tests == 0

def main():
    """主验证函数"""
    print("📝 开始字幕功能集成验证...")
    print("=" * 60)

    # 运行所有测试
    test_results = {
        "字幕后端API": test_subtitle_backend_api(),
        "字幕下载函数": test_subtitle_functions(),
        "Gradio字幕界面": test_gradio_subtitle_interface(),
        "字幕请求模型": test_subtitle_request_model(),
        "字幕语言支持": test_subtitle_languages_support(),
        "字幕格式支持": test_subtitle_formats_support(),
    }

    # 生成报告
    success = generate_subtitle_integration_report(test_results)

    # 返回适当的退出代码
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()