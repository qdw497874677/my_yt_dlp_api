"""
Cookie管理器模块
提供自动获取、验证、管理浏览器cookies的完整功能
"""

from .config import config, CookieConfig
from .scanner import BrowserCookieScanner
from .validator import CookieValidator, CookieManager
from utils.browser_utils import (
    BrowserDetector, PathUtils, ProcessUtils, BrowserLockChecker,
    get_system_info, detect_browsers, get_browser_status
)
import logging
import asyncio
import os
from typing import Dict, Optional, List
from pathlib import Path

__version__ = "1.0.0"
__all__ = [
    "config",
    "CookieConfig",
    "BrowserCookieScanner",
    "CookieValidator",
    "CookieManager",
    "BrowserDetector",
    "PathUtils",
    "ProcessUtils",
    "BrowserLockChecker",
    "get_system_info",
    "detect_browsers",
    "get_browser_status",
    "AutoCookieManager"
]

logger = logging.getLogger(__name__)

class AutoCookieManager:
    """
    自动Cookie管理器
    提供完整的cookie自动管理功能
    """

    def __init__(self, config_obj=None):
        """
        初始化自动cookie管理器

        Args:
            config_obj: 自定义配置对象，如果为None则使用默认配置
        """
        self.config = config_obj or config
        self.cookie_manager = CookieManager()
        self.scanner = BrowserCookieScanner()
        self.validator = CookieValidator()

        # 确保目录存在
        self.config.ensure_directories()

        logger.info("AutoCookieManager初始化完成")

    async def auto_setup(self) -> Dict:
        """
        自动设置cookies

        Returns:
            Dict: 设置结果和状态信息
        """
        logger.info("开始自动cookie设置...")

        try:
            # 第一步：检测系统环境
            system_info = get_system_info()
            logger.info(f"系统信息: {system_info['platform']} {system_info['architecture']}")

            # 第二步：检测浏览器
            detected_browsers = detect_browsers()
            logger.info(f"检测到的浏览器: {detected_browsers}")

            # 第三步：检查浏览器状态
            browser_status = {}
            for browser in detected_browsers:
                if detected_browsers[browser]:
                    status = get_browser_status(browser)
                    browser_status[browser] = status
                    logger.info(f"{browser}状态: {status['recommendation']}")

            # 第四步：自动扫描和验证
            scan_result = await self.cookie_manager.auto_scan_and_validate()

            # 第五步：生成设置报告
            # 转换系统信息中的Path对象为字符串，确保可JSON序列化
            system_info_serializable = {}
            for key, value in system_info.items():
                if isinstance(value, Path):
                    system_info_serializable[key] = str(value)
                else:
                    system_info_serializable[key] = value

            setup_report = {
                "success": scan_result["best_cookie"] is not None,
                "system_info": system_info_serializable,
                "detected_browsers": detected_browsers,
                "browser_status": browser_status,
                "scan_result": scan_result,
                "active_cookie": str(scan_result.get("best_cookie")) if scan_result.get("best_cookie") else None,
                "recommendations": self._generate_recommendations(scan_result, browser_status),
                "timestamp": scan_result.get("timestamp")
            }

            logger.info(f"自动cookie设置完成: {setup_report['success']}")
            return setup_report

        except Exception as e:
            logger.error(f"自动cookie设置失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "recommendations": ["检查系统权限", "确保浏览器已安装", "查看详细错误日志"]
            }

    def _generate_recommendations(self, scan_result: Dict, browser_status: Dict) -> List[str]:
        """生成建议列表"""
        recommendations = []

        if scan_result["best_cookie"]:
            recommendations.append("✅ Cookie自动设置成功，可以正常使用")
        else:
            recommendations.append("❌ 未找到有效的YouTube cookies")

            # 分析原因并给出建议
            if not any(browser_status.values()):
                recommendations.append("🔍 未检测到支持的浏览器，请安装Chrome/Firefox/Edge等浏览器")
            else:
                recommendations.append("🔍 检测到浏览器但未找到有效cookies，可能原因：")

                running_browsers = [b for b, status in browser_status.items() if status.get("running")]
                if running_browsers:
                    recommendations.append(f"  - 以下浏览器正在运行: {', '.join(running_browsers)}")
                    recommendations.append("  - 建议关闭浏览器后重试")

                locked_browsers = [b for b, status in browser_status.items() if status.get("has_locked_files")]
                if locked_browsers:
                    recommendations.append(f"  - 以下浏览器文件被锁定: {', '.join(locked_browsers)}")
                    recommendations.append("  - 建议重启电脑后重试")

            recommendations.append("💡 也可以手动上传cookies文件")

        return recommendations

    async def get_current_cookie_status(self) -> Dict:
        """
        获取当前cookie状态

        Returns:
            Dict: 当前cookie状态信息
        """
        active_cookie = self.cookie_manager.get_active_cookie()

        if not active_cookie:
            return {
                "has_active_cookie": False,
                "message": "没有活跃的cookie",
                "recommendation": "运行自动设置或手动上传cookies"
            }

        # 验证当前cookie
        validation_result = await self.cookie_manager.validate_active_cookie()

        return {
            "has_active_cookie": True,
            "cookie_file": active_cookie,
            "validation_result": validation_result,
            "health_status": self.validator.get_cookie_health_status(validation_result),
            "recommendation": self.validator.get_health_recommendation(
                self.validator.get_cookie_health_status(validation_result)
            )
        }

    async def refresh_cookies(self) -> Dict:
        """
        刷新cookies

        Returns:
            Dict: 刷新结果
        """
        logger.info("开始刷新cookies...")

        try:
            # 清理当前缓存
            self.validator.cache.clear()

            # 执行新的扫描
            scan_result = await self.cookie_manager.auto_scan_and_validate()

            # 清理过期cookies
            cleanup_result = await self.cookie_manager.cleanup_expired_cookies()

            return {
                "success": scan_result["best_cookie"] is not None,
                "new_cookie": scan_result["best_cookie"],
                "scan_summary": scan_result["scan_summary"],
                "cleaned_count": cleanup_result.get("cleaned_count", 0),
                "timestamp": scan_result.get("timestamp")
            }

        except Exception as e:
            logger.error(f"刷新cookies失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def validate_cookie_file(self, cookie_file: str, detailed: bool = True) -> Dict:
        """
        验证指定的cookie文件

        Args:
            cookie_file: cookie文件路径
            detailed: 是否进行详细验证

        Returns:
            Dict: 验证结果
        """
        return await self.validator.validate_cookie_file(cookie_file, detailed)

    def get_active_cookie_path(self) -> Optional[str]:
        """
        获取当前活跃的cookie文件路径

        Returns:
            Optional[str]: cookie文件路径，如果没有则返回None
        """
        return self.cookie_manager.get_active_cookie()

    def get_supported_browsers(self) -> List[str]:
        """
        获取支持的浏览器列表

        Returns:
            List[str]: 支持的浏览器名称列表
        """
        return self.config.supported_browsers

    async def diagnose_environment(self) -> Dict:
        """
        诊断环境问题

        Returns:
            Dict: 诊断结果
        """
        logger.info("开始环境诊断...")

        diagnosis = {
            "system": {},
            "browsers": {},
            "permissions": {},
            "directories": {},
            "recommendations": []
        }

        try:
            # 系统诊断
            system_info = get_system_info()
            diagnosis["system"] = {
                "platform": system_info["platform"],
                "architecture": system_info["architecture"],
                "python_version": system_info["python_version"],
                "home_directory": str(system_info["home"]),
                "status": "ok"
            }

            # 浏览器诊断
            detected_browsers = detect_browsers()
            for browser in self.config.supported_browsers:
                is_installed = detected_browsers.get(browser, False)
                browser_info = {
                    "installed": is_installed,
                    "status": "ok" if is_installed else "not_installed"
                }

                if is_installed:
                    status = get_browser_status(browser)
                    browser_info.update({
                        "running": status["running"],
                        "has_locked_files": status["has_locked_files"],
                        "recommendation": status["recommendation"]
                    })

                diagnosis["browsers"][browser] = browser_info

            # 权限诊断
            diagnosis["permissions"] = self._check_permissions()

            # 目录诊断
            diagnosis["directories"] = self._check_directories()

            # 生成总体建议
            diagnosis["recommendations"] = self._generate_diagnosis_recommendations(diagnosis)

        except Exception as e:
            logger.error(f"环境诊断失败: {e}")
            diagnosis["error"] = str(e)

        return diagnosis

    def _check_permissions(self) -> Dict:
        """检查文件系统权限"""
        permissions = {}

        # 检查cookie目录权限
        cookie_dir = Path(self.config.cookie_directory)
        if cookie_dir.exists():
            permissions["cookie_directory"] = {
                "exists": True,
                "writable": os.access(cookie_dir, os.W_OK),
                "readable": os.access(cookie_dir, os.R_OK),
                "permissions": PathUtils.get_file_permissions(cookie_dir)
            }
        else:
            permissions["cookie_directory"] = {
                "exists": False,
                "writable": False,
                "readable": False,
                "error": "目录不存在"
            }

        # 检查用户主目录权限
        home_dir = Path.home()
        permissions["home_directory"] = {
            "exists": True,
            "writable": os.access(home_dir, os.W_OK),
            "readable": os.access(home_dir, os.R_OK),
            "permissions": PathUtils.get_file_permissions(home_dir)
        }

        return permissions

    def _check_directories(self) -> Dict:
        """检查必要目录"""
        directories = {}

        required_dirs = [
            self.config.cookie_directory,
            self.config.backup_directory
        ]

        for dir_path in required_dirs:
            path_obj = Path(dir_path)
            directories[dir_path] = {
                "exists": path_obj.exists(),
                "is_directory": path_obj.is_dir() if path_obj.exists() else False,
                "writable": os.access(dir_path, os.W_OK) if path_obj.exists() else False
            }

        return directories

    def _generate_diagnosis_recommendations(self, diagnosis: Dict) -> List[str]:
        """生成诊断建议"""
        recommendations = []

        # 检查浏览器
        installed_browsers = [name for name, info in diagnosis["browsers"].items() if info["installed"]]
        if not installed_browsers:
            recommendations.append("❌ 未检测到支持的浏览器，请安装Chrome、Firefox或Edge")

        # 检查权限
        perm_issues = []
        for dir_name, perm_info in diagnosis["permissions"].items():
            if not perm_info.get("writable", False):
                perm_issues.append(dir_name)

        if perm_issues:
            recommendations.append(f"⚠️  以下目录权限不足: {', '.join(perm_issues)}")

        # 检查目录
        dir_issues = []
        for dir_name, dir_info in diagnosis["directories"].items():
            if not dir_info["exists"]:
                dir_issues.append(dir_name)

        if dir_issues:
            recommendations.append(f"📁 需要创建目录: {', '.join(dir_issues)}")

        if not recommendations:
            recommendations.append("✅ 环境检查通过，可以正常运行")

        return recommendations

# 创建全局实例
auto_cookie_manager = AutoCookieManager()

# 便捷函数
async def auto_setup_cookies() -> Dict:
    """自动设置cookies（便捷函数）"""
    return await auto_cookie_manager.auto_setup()

async def get_cookie_status() -> Dict:
    """获取cookie状态（便捷函数）"""
    return await auto_cookie_manager.get_current_cookie_status()

async def refresh_cookies() -> Dict:
    """刷新cookies（便捷函数）"""
    return await auto_cookie_manager.refresh_cookies()