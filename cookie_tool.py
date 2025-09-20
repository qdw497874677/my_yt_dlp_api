#!/usr/bin/env python3
"""
Cookie管理工具脚本
提供命令行接口来管理cookies
"""

import asyncio
import sys
import os
import json
import argparse
import datetime
from typing import Dict, Any
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cookie_manager import (
    auto_cookie_manager,
    auto_setup_cookies,
    get_cookie_status,
    refresh_cookies
)
from utils.browser_utils import (
    detect_browsers,
    get_system_info,
    get_browser_status
)


async def cmd_auto_setup(args):
    """自动设置cookies"""
    print("🔍 正在自动设置cookies...")
    result = await auto_setup_cookies()

    if result.get("success"):
        print("✅ Cookie设置成功!")
        print(f"活跃cookie文件: {result.get('active_cookie', 'N/A')}")

        if result.get("recommendations"):
            print("\n💡 建议:")
            for rec in result["recommendations"]:
                print(f"  • {rec}")
    else:
        print("❌ Cookie设置失败")
        print(f"错误: {result.get('error', '未知错误')}")

        if result.get("recommendations"):
            print("\n💡 故障排除建议:")
            for rec in result["recommendations"]:
                print(f"  • {rec}")


async def cmd_status(args):
    """查看cookie状态"""
    print("📊 检查Cookie状态...")
    status = await get_cookie_status()

    if status.get("has_active_cookie"):
        print("✅ 发现活跃的Cookie")
        print(f"文件: {status.get('cookie_file')}")
        print(f"健康状态: {status.get('health_status', 'unknown')}")
        print(f"建议: {status.get('recommendation', '无')}")

        validation = status.get("validation_result", {})
        if validation.get("valid"):
            print(f"视频标题: {validation.get('video_title', 'N/A')}")
            print(f"时长: {validation.get('duration', 'N/A')}秒")
            print(f"上传者: {validation.get('uploader', 'N/A')}")

            if validation.get("premium_content"):
                print("🌟 Premium内容访问: ✅")

            if validation.get("age_restricted"):
                print("🔞 年龄限制内容: ✅")
    else:
        print("❌ 没有发现活跃的Cookie")
        print(f"建议: {status.get('recommendation', '请运行自动设置')}")


async def cmd_refresh(args):
    """刷新cookies"""
    print("🔄 正在刷新Cookies...")
    result = await refresh_cookies()

    if result.get("success"):
        print("✅ Cookie刷新成功!")
        print(f"新cookie文件: {result.get('new_cookie', 'N/A')}")
        print(f"清理了 {result.get('cleaned_count', 0)} 个过期文件")

        if result.get("scan_summary"):
            summary = result["scan_summary"]
            print(f"\n📈 扫描摘要:")
            print(f"  扫描浏览器: {summary.get('total_browsers', 0)}")
            print(f"  成功浏览器: {summary.get('successful_browsers', 0)}")
            print(f"  总cookies: {summary.get('total_cookies', 0)}")
    else:
        print("❌ Cookie刷新失败")
        print(f"错误: {result.get('error', '未知错误')}")


async def cmd_diagnose(args):
    """诊断环境问题"""
    print("🔍 正在诊断环境...")
    diagnosis = await auto_cookie_manager.diagnose_environment()

    print("\n📋 系统信息:")
    sys_info = diagnosis.get("system", {})
    print(f"  操作系统: {sys_info.get('platform', 'Unknown')}")
    print(f"  架构: {sys_info.get('architecture', 'Unknown')}")
    print(f"  Python版本: {sys_info.get('python_version', 'Unknown')}")

    print("\n🌐 浏览器检测:")
    browsers = diagnosis.get("browsers", {})
    for browser, info in browsers.items():
        status_icon = "✅" if info.get("installed") else "❌"
        print(f"  {status_icon} {browser}: {info.get('status', 'Unknown')}")

        if info.get("installed"):
            if info.get("running"):
                print(f"    ⚠️  浏览器正在运行")
            if info.get("has_locked_files"):
                print(f"    🔒 检测到文件锁定")
            if info.get("recommendation"):
                print(f"    💡 {info.get('recommendation')}")

    print("\n📁 权限检查:")
    permissions = diagnosis.get("permissions", {})
    for dir_name, perm_info in permissions.items():
        status_icon = "✅" if perm_info.get("writable") else "❌"
        print(f"  {status_icon} {dir_name}: 可写={perm_info.get('writable', False)}")

    print("\n🎯 建议:")
    recommendations = diagnosis.get("recommendations", [])
    if recommendations:
        for rec in recommendations:
            print(f"  • {rec}")
    else:
        print("  • 环境检查通过，可以正常运行")

    if diagnosis.get("error"):
        print(f"\n❌ 诊断错误: {diagnosis.get('error')}")


async def cmd_list(args):
    """列出cookie文件"""
    print("📂 Cookie文件列表:")

    try:
        import glob
        cookie_files = glob.glob("cookies/*.txt")

        if not cookie_files:
            print("  没有找到Cookie文件")
            return

        # 按修改时间排序
        cookie_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

        for i, cookie_file in enumerate(cookie_files, 1):
            stat = os.stat(cookie_file)
            size_kb = stat.st_size / 1024
            mod_time = datetime.datetime.fromtimestamp(stat.st_mtime)

            print(f"  {i}. {os.path.basename(cookie_file)}")
            print(f"     大小: {size_kb:.1f} KB")
            print(f"     修改时间: {mod_time}")

            # 检查是否为活跃cookie
            active_cookie = auto_cookie_manager.get_active_cookie_path()
            if active_cookie == cookie_file:
                print("     🟢 活跃状态")
            print()
    except Exception as e:
        print(f"❌ 列出Cookie文件失败: {e}")


async def cmd_validate(args):
    """验证cookie文件"""
    if not args.file:
        print("❌ 请指定要验证的cookie文件")
        return

    cookie_file = args.file
    if not os.path.exists(cookie_file):
        print(f"❌ 文件不存在: {cookie_file}")
        return

    print(f"🔍 验证Cookie文件: {cookie_file}")
    result = await auto_cookie_manager.validate_cookie_file(cookie_file, args.detailed)

    if result.get("valid"):
        print("✅ Cookie有效")
        print(f"测试URL: {result.get('test_url', 'N/A')}")
        print(f"视频标题: {result.get('video_title', 'N/A')}")
        print(f"健康状态: {auto_cookie_manager.validator.get_cookie_health_status(result)}")

        if args.detailed and result.get("access_tests"):
            print("\n🧪 访问测试:")
            for test_type, test_result in result["access_tests"].items():
                status_icon = "✅" if test_result.get("accessible") else "❌"
                print(f"  {status_icon} {test_type}: {test_result.get('title', 'N/A')}")
    else:
        print("❌ Cookie无效")
        print(f"错误: {result.get('error', 'Unknown error')}")


async def cmd_detect(args):
    """检测浏览器"""
    print("🌐 检测已安装的浏览器...")

    system_info = get_system_info()
    print(f"\n💻 系统信息:")
    print(f"  操作系统: {system_info['platform']}")
    print(f"  架构: {system_info['architecture']}")

    detected = detect_browsers()
    print(f"\n🔍 浏览器检测结果:")

    for browser, is_installed in detected.items():
        status_icon = "✅" if is_installed else "❌"
        print(f"  {status_icon} {browser}")

        if is_installed:
            status = get_browser_status(browser)
            print(f"    状态: {status['recommendation']}")


async def cmd_cleanup(args):
    """清理过期cookies"""
    print("🧹 清理过期Cookies...")

    try:
        result = await auto_cookie_manager.cookie_manager.cleanup_expired_cookies()
        cleaned_count = result.get("cleaned_count", 0)

        if cleaned_count > 0:
            print(f"✅ 清理完成，移动了 {cleaned_count} 个过期Cookie文件到备份目录")
        else:
            print("✅ 没有发现需要清理的过期Cookie文件")

    except Exception as e:
        print(f"❌ 清理失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="yt-dlp Cookie管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  %(prog)s auto-setup          # 自动设置cookies
  %(prog)s status              # 查看cookie状态
  %(prog)s refresh             # 刷新cookies
  %(prog)s diagnose            # 诊断环境问题
  %(prog)s list                # 列出cookie文件
  %(prog)s validate file.txt   # 验证指定cookie文件
  %(prog)s detect              # 检测浏览器
  %(prog)s cleanup             # 清理过期cookies
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # auto-setup命令
    parser_auto = subparsers.add_parser('auto-setup', help='自动设置cookies')
    parser_auto.set_defaults(func=cmd_auto_setup)

    # status命令
    parser_status = subparsers.add_parser('status', help='查看cookie状态')
    parser_status.set_defaults(func=cmd_status)

    # refresh命令
    parser_refresh = subparsers.add_parser('refresh', help='刷新cookies')
    parser_refresh.set_defaults(func=cmd_refresh)

    # diagnose命令
    parser_diagnose = subparsers.add_parser('diagnose', help='诊断环境问题')
    parser_diagnose.set_defaults(func=cmd_diagnose)

    # list命令
    parser_list = subparsers.add_parser('list', help='列出cookie文件')
    parser_list.set_defaults(func=cmd_list)

    # validate命令
    parser_validate = subparsers.add_parser('validate', help='验证cookie文件')
    parser_validate.add_argument('file', help='Cookie文件路径')
    parser_validate.add_argument('--detailed', action='store_true', help='详细验证')
    parser_validate.set_defaults(func=cmd_validate)

    # detect命令
    parser_detect = subparsers.add_parser('detect', help='检测浏览器')
    parser_detect.set_defaults(func=cmd_detect)

    # cleanup命令
    parser_cleanup = subparsers.add_parser('cleanup', help='清理过期cookies')
    parser_cleanup.set_defaults(func=cmd_cleanup)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # 运行对应命令
    try:
        asyncio.run(args.func(args))
    except KeyboardInterrupt:
        print("\n操作被用户中断")
    except Exception as e:
        print(f"执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()