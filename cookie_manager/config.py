"""
Cookie管理配置文件
定义cookie管理的各种配置参数
"""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class CookieConfig:
    """Cookie管理配置"""

    # 存储配置
    cookie_directory: str = "cookies"
    backup_directory: str = "cookies/backup"

    # 浏览器配置
    supported_browsers: List[str] = None
    browser_profiles: Dict[str, Dict] = None

    # 验证配置
    validation_urls: Dict[str, str] = None
    test_video_id: str = "dQw4w9WgXcQ"  # 测试用的YouTube视频ID

    # 过期管理配置
    warning_threshold_days: int = 7  # 提前7天警告
    critical_threshold_days: int = 3  # 提前3天严重警告
    auto_renew_threshold_days: int = 5  # 自动续期阈值

    # 性能配置
    max_concurrent_browsers: int = 3
    browser_timeout: int = 30
    validation_timeout: int = 15

    def __post_init__(self):
        """初始化默认值"""
        if self.supported_browsers is None:
            self.supported_browsers = [
                "edge"
            ]

        if self.browser_profiles is None:
            self.browser_profiles = {
                "edge": {
                    "windows_paths": [
                        "~/AppData/Local/Microsoft/Edge/User Data",
                        "~/AppData/Local/Microsoft/Edge Beta/User Data",
                        "~/AppData/Local/Microsoft/Edge Canary/User Data"
                    ],
                    "mac_paths": [
                        "~/Library/Application Support/Microsoft Edge",
                        "~/Library/Application Support/Microsoft Edge Beta",
                        "~/Library/Application Support/Microsoft Edge Canary"
                    ],
                    "linux_paths": [
                        "~/.config/microsoft-edge",
                        "~/.config/microsoft-edge-beta",
                        "~/.config/microsoft-edge-dev"
                    ],
                    "cookie_db": "Cookies"
                }
            }

        if self.validation_urls is None:
            self.validation_urls = {
                "youtube": "https://www.youtube.com/watch?v=",
                "youtube_shorts": "https://www.youtube.com/shorts/",
                "youtube_music": "https://music.youtube.com/",
                "youtube_premium": "https://www.youtube.com/premium"
            }

    def get_browser_paths(self, browser: str, os_type: str = None) -> List[str]:
        """获取指定浏览器的cookie存储路径"""
        if os_type is None:
            # 自动检测操作系统
            import platform
            system = platform.system().lower()
            if system == "windows":
                os_type = "windows"
            elif system == "darwin":
                os_type = "mac"
            else:
                os_type = "linux"

        browser_config = self.browser_profiles.get(browser, {})
        paths = browser_config.get(f"{os_type}_paths", [])

        # 展开路径中的 ~
        expanded_paths = []
        for path in paths:
            expanded_path = os.path.expanduser(path)
            if os.path.exists(expanded_path):
                expanded_paths.append(expanded_path)

        return expanded_paths

    def ensure_directories(self):
        """确保必要的目录存在"""
        for directory in [self.cookie_directory, self.backup_directory]:
            os.makedirs(directory, exist_ok=True)

    @classmethod
    def from_env(cls):
        """从环境变量创建配置"""
        return cls(
            cookie_directory=os.getenv("COOKIE_DIR", "cookies"),
            backup_directory=os.getenv("COOKIE_BACKUP_DIR", "cookies/backup"),
            warning_threshold_days=int(os.getenv("COOKIE_WARNING_DAYS", "7")),
            critical_threshold_days=int(os.getenv("COOKIE_CRITICAL_DAYS", "3")),
            auto_renew_threshold_days=int(os.getenv("COOKIE_AUTO_RENEW_DAYS", "5")),
            max_concurrent_browsers=int(os.getenv("MAX_CONCURRENT_BROWSERS", "3")),
            browser_timeout=int(os.getenv("BROWSER_TIMEOUT", "30")),
            validation_timeout=int(os.getenv("VALIDATION_TIMEOUT", "15"))
        )

# 全局配置实例
config = CookieConfig.from_env()