"""
浏览器工具模块
提供浏览器检测、路径解析等通用功能
"""

import os
import sys
import platform
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class BrowserDetector:
    """浏览器检测器"""

    @staticmethod
    def detect_system() -> Dict:
        """检测系统信息"""
        system_info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "home": Path.home(),
        }

        # 添加系统特定的信息
        if system_info["platform"] == "Windows":
            system_info.update({
                "appdata": os.getenv("APPDATA"),
                "localappdata": os.getenv("LOCALAPPDATA"),
                "program_files": os.getenv("ProgramFiles"),
                "program_files_x86": os.getenv("ProgramFiles(x86)"),
            })
        elif system_info["platform"] == "Darwin":  # macOS
            system_info.update({
                "library": Path.home() / "Library",
                "application_support": Path.home() / "Library" / "Application Support",
                "caches": Path.home() / "Library" / "Caches",
            })
        else:  # Linux
            system_info.update({
                "config": Path.home() / ".config",
                "cache": Path.home() / ".cache",
                "local_share": Path.home() / ".local" / "share",
            })

        return system_info

    @staticmethod
    def detect_installed_browsers() -> Dict[str, bool]:
        """检测已安装的浏览器"""
        system_info = BrowserDetector.detect_system()
        platform_name = system_info["platform"].lower()
        detected = {}

        # 定义浏览器检测规则
        browser_rules = {
            "chrome": {
                "windows": [
                    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
                    f"{system_info.get('localappdata', '')}\\Google\\Chrome\\Application\\chrome.exe",
                ],
                "darwin": [
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                    "/Applications/Google Chrome Beta.app/Contents/MacOS/Google Chrome",
                    "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome",
                ],
                "linux": [
                    "/usr/bin/google-chrome",
                    "/usr/bin/google-chrome-stable",
                    "/usr/bin/google-chrome-beta",
                    "/opt/google/chrome/chrome",
                    "~/.config/google-chrome/chrome",
                ]
            },
            "firefox": {
                "windows": [
                    "C:\\Program Files\\Mozilla Firefox\\firefox.exe",
                    "C:\\Program Files (x86)\\Mozilla Firefox\\firefox.exe",
                    f"{system_info.get('localappdata', '')}\\Mozilla Firefox\\firefox.exe",
                ],
                "darwin": [
                    "/Applications/Firefox.app/Contents/MacOS/firefox",
                    "/Applications/Firefox Developer Edition.app/Contents/MacOS/firefox",
                ],
                "linux": [
                    "/usr/bin/firefox",
                    "/usr/bin/firefox-developer-edition",
                    "/usr/lib/firefox/firefox",
                    "/opt/firefox/firefox",
                ]
            },
            "edge": {
                "windows": [
                    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
                    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
                    f"{system_info.get('localappdata', '')}\\Microsoft\\Edge\\Application\\msedge.exe",
                ],
                "darwin": [
                    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                    "/Applications/Microsoft Edge Beta.app/Contents/MacOS/Microsoft Edge",
                ],
                "linux": [
                    "/usr/bin/microsoft-edge",
                    "/usr/bin/microsoft-edge-stable",
                    "/usr/bin/microsoft-edge-beta",
                    "/opt/microsoft/msedge/msedge",
                ]
            },
            "safari": {
                "darwin": [
                    "/Applications/Safari.app/Contents/MacOS/Safari",
                    "/System/Library/CoreServices/SafariSupport.bundle/Contents/MacOS/Safari",
                ],
                "default": []  # Safari主要在macOS上
            },
            "opera": {
                "windows": [
                    "C:\\Program Files\\Opera\\opera.exe",
                    "C:\\Program Files (x86)\\Opera\\opera.exe",
                    f"{system_info.get('localappdata', '')}\\Programs\\Opera\\opera.exe",
                ],
                "darwin": [
                    "/Applications/Opera.app/Contents/MacOS/opera",
                    "/Applications/Opera Beta.app/Contents/MacOS/opera",
                ],
                "linux": [
                    "/usr/bin/opera",
                    "/usr/bin/opera-beta",
                    "/usr/bin/opera-developer",
                    "/opt/opera/opera",
                ]
            }
        }

        # 检测每个浏览器
        for browser_name, paths_dict in browser_rules.items():
            # 获取当前平台的路径列表
            platform_paths = paths_dict.get(platform_name, paths_dict.get("default", []))

            # 展开路径并检查是否存在
            detected[browser_name] = False
            for path_template in platform_paths:
                expanded_path = os.path.expanduser(path_template)
                path = Path(expanded_path)
                if path.exists() and path.is_file():
                    detected[browser_name] = True
                    logger.debug(f"检测到浏览器 {browser_name}: {path}")
                    break

        return detected

    @staticmethod
    def get_browser_data_paths(browser_name: str) -> List[Path]:
        """获取浏览器数据存储路径"""
        system_info = BrowserDetector.detect_system()
        platform_name = system_info["platform"].lower()

        # 定义浏览器数据路径
        data_paths = {
            "chrome": {
                "windows": [
                    Path(system_info.get("localappdata", "")) / "Google" / "Chrome" / "User Data",
                    Path(system_info.get("localappdata", "")) / "Google" / "Chrome Beta" / "User Data",
                    Path(system_info.get("localappdata", "")) / "Google" / "Chrome Canary" / "User Data",
                ],
                "darwin": [
                    Path(system_info.get("application_support", "")) / "Google" / "Chrome",
                    Path(system_info.get("application_support", "")) / "Google" / "Chrome Beta",
                    Path(system_info.get("application_support", "")) / "Google" / "Chrome Canary",
                ],
                "linux": [
                    Path(system_info.get("config", "")) / "google-chrome",
                    Path(system_info.get("config", "")) / "google-chrome-beta",
                    Path(system_info.get("config", "")) / "google-chrome-unstable",
                ]
            },
            "firefox": {
                "windows": [
                    Path(system_info.get("appdata", "")) / "Mozilla" / "Firefox" / "Profiles",
                    Path(system_info.get("appdata", "")) / "Waterfox" / "Profiles",
                ],
                "darwin": [
                    Path(system_info.get("application_support", "")) / "Firefox" / "Profiles",
                    Path(system_info.get("application_support", "")) / "Waterfox" / "Profiles",
                ],
                "linux": [
                    Path(system_info.get("localappdata", "")) / ".mozilla" / "firefox",
                    Path(system_info.get("localappdata", "")) / ".waterfox",
                ]
            },
            "edge": {
                "windows": [
                    Path(system_info.get("localappdata", "")) / "Microsoft" / "Edge" / "User Data",
                    Path(system_info.get("localappdata", "")) / "Microsoft" / "Edge Beta" / "User Data",
                    Path(system_info.get("localappdata", "")) / "Microsoft" / "Edge Canary" / "User Data",
                ],
                "darwin": [
                    Path(system_info.get("application_support", "")) / "Microsoft Edge",
                    Path(system_info.get("application_support", "")) / "Microsoft Edge Beta",
                    Path(system_info.get("application_support", "")) / "Microsoft Edge Canary",
                ],
                "linux": [
                    Path(system_info.get("config", "")) / "microsoft-edge",
                    Path(system_info.get("config", "")) / "microsoft-edge-beta",
                    Path(system_info.get("config", "")) / "microsoft-edge-dev",
                ]
            }
        }

        # 获取当前平台的路径列表
        platform_paths = data_paths.get(browser_name, {}).get(platform_name, [])

        # 过滤存在的路径
        existing_paths = []
        for path in platform_paths:
            if path.exists() and path.is_dir():
                existing_paths.append(path)

        return existing_paths

class PathUtils:
    """路径工具类"""

    @staticmethod
    def expand_path(path: str) -> Path:
        """展开路径中的用户目录和环境变量"""
        expanded = os.path.expanduser(path)
        expanded = os.path.expandvars(expanded)
        return Path(expanded)

    @staticmethod
    def ensure_directory(path: Path) -> Path:
        """确保目录存在"""
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def safe_filename(filename: str) -> str:
        """生成安全的文件名"""
        # 替换不安全的字符
        unsafe_chars = '<>:"/\\|?*'
        safe_name = filename
        for char in unsafe_chars:
            safe_name = safe_name.replace(char, '_')

        # 限制长度
        if len(safe_name) > 200:
            safe_name = safe_name[:197] + '...'

        return safe_name

    @staticmethod
    def get_file_permissions(file_path: Path) -> str:
        """获取文件权限"""
        if not file_path.exists():
            return "000"

        stat = file_path.stat()
        return oct(stat.st_mode)[-3:]

class ProcessUtils:
    """进程工具类"""

    @staticmethod
    def is_process_running(process_name: str) -> bool:
        """检查进程是否正在运行"""
        try:
            import psutil
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] == process_name:
                    return True
            return False
        except ImportError:
            logger.warning("psutil未安装，无法检测进程状态")
            return False

    @staticmethod
    def kill_browser_processes(browser_name: str) -> bool:
        """终止浏览器进程"""
        success = False
        try:
            import psutil

            browser_processes = {
                "chrome": ["chrome.exe", "chrome", "google-chrome"],
                "firefox": ["firefox.exe", "firefox"],
                "edge": ["msedge.exe", "msedge", "microsoft-edge"],
                "safari": ["Safari"],
                "opera": ["opera.exe", "opera"]
            }

            process_names = browser_processes.get(browser_name.lower(), [])
            if not process_names:
                logger.warning(f"未知的浏览器: {browser_name}")
                return False

            for proc in psutil.process_iter(['name']):
                if proc.info['name'] in process_names:
                    try:
                        proc.terminate()
                        success = True
                        logger.info(f"已终止进程: {proc.info['name']} (PID: {proc.pid})")
                    except Exception as e:
                        logger.warning(f"终止进程失败 {proc.info['name']}: {e}")

            return success

        except ImportError:
            logger.warning("psutil未安装，无法终止进程")
            return False

class BrowserLockChecker:
    """浏览器文件锁定检查器"""

    @staticmethod
    def is_file_locked(file_path: Path) -> bool:
        """检查文件是否被锁定"""
        if not file_path.exists():
            return False

        try:
            # 尝试以独占模式打开文件
            with open(file_path, 'r+b') as f:
                pass
            return False
        except (IOError, PermissionError):
            return True

    @staticmethod
    def check_browser_locks(browser_name: str) -> Dict[str, bool]:
        """检查浏览器文件锁定状态"""
        locked_files = {}

        # 获取浏览器数据路径
        data_paths = BrowserDetector.get_browser_data_paths(browser_name)

        # 检查关键文件
        key_files = {
            "chrome": ["Cookies", "History", "Login Data"],
            "firefox": ["cookies.sqlite", "places.sqlite", "formhistory.sqlite"],
            "edge": ["Cookies", "History", "Login Data"]
        }

        browser_files = key_files.get(browser_name.lower(), [])
        if not browser_files:
            return locked_files

        for data_path in data_paths:
            if not data_path.exists():
                continue

            # 检查Profiles目录下的所有配置文件
            for profile_dir in data_path.iterdir():
                if not profile_dir.is_dir():
                    continue

                for file_name in browser_files:
                    file_path = profile_dir / file_name
                    if file_path.exists():
                        locked_files[str(file_path)] = BrowserLockChecker.is_file_locked(file_path)

        return locked_files

    @staticmethod
    def get_browser_status_summary(browser_name: str) -> Dict:
        """获取浏览器状态摘要"""
        detected = BrowserDetector.detect_installed_browsers()
        is_installed = detected.get(browser_name, False)
        is_running = ProcessUtils.is_process_running(browser_name)

        locked_files = BrowserLockChecker.check_browser_locks(browser_name)
        has_locked_files = any(locked_files.values())

        return {
            "browser": browser_name,
            "installed": is_installed,
            "running": is_running,
            "has_locked_files": has_locked_files,
            "locked_files": locked_files,
            "recommendation": BrowserLockChecker._get_recommendation(
                is_installed, is_running, has_locked_files
            )
        }

    @staticmethod
    def _get_recommendation(installed: bool, running: bool, locked_files: bool) -> str:
        """获取操作建议"""
        if not installed:
            return "浏览器未安装，无法获取cookies"
        if running:
            return "建议关闭浏览器后再获取cookies以避免文件锁定"
        if locked_files:
            return "检测到文件锁定，可能需要重启系统或等待浏览器完全关闭"
        return "浏览器状态正常，可以安全获取cookies"

# 便捷函数
def get_system_info() -> Dict:
    """获取系统信息（便捷函数）"""
    return BrowserDetector.detect_system()

def detect_browsers() -> Dict[str, bool]:
    """检测已安装浏览器（便捷函数）"""
    return BrowserDetector.detect_installed_browsers()

def get_browser_status(browser_name: str) -> Dict:
    """获取浏览器状态（便捷函数）"""
    return BrowserLockChecker.get_browser_status_summary(browser_name)