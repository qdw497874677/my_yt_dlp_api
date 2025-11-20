"""
浏览器会话管理器
提供YouTube登录的浏览器会话管理功能
"""

import asyncio
import logging
import os
import psutil
import tempfile
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import threading
import json

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.common.exceptions import WebDriverException, TimeoutException
    from undetected_chromedriver import Chrome as UndetectedChrome
except ImportError:
    webdriver = None
    Options = None
    Service = None
    WebDriverException = Exception
    TimeoutException = Exception
    UndetectedChrome = None

logger = logging.getLogger(__name__)

@dataclass
class BrowserSession:
    """浏览器会话数据类"""
    session_id: str
    driver: Optional[Any] = None
    debug_port: Optional[int] = None
    user_data_dir: Optional[str] = None
    created_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    status: str = "initializing"  # initializing, ready, login_complete, extracting, completed, error
    youtube_logged_in: bool = False
    cookies_extracted: bool = False
    error_message: Optional[str] = None
    process_id: Optional[int] = None

class BrowserSessionManager:
    """浏览器会话管理器"""

    def __init__(self, max_sessions: int = 3, session_timeout: int = 1800):
        """
        初始化浏览器会话管理器

        Args:
            max_sessions: 最大并发会话数
            session_timeout: 会话超时时间（秒）
        """
        self.max_sessions = max_sessions
        self.session_timeout = session_timeout
        self.sessions: Dict[str, BrowserSession] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_sessions)
        self._cleanup_thread = None
        self._running = False

        # 启动清理线程
        self.start_cleanup_thread()

        logger.info(f"BrowserSessionManager初始化完成，最大会话数: {max_sessions}, 超时: {session_timeout}秒")

    def start_cleanup_thread(self):
        """启动会话清理线程"""
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._running = True
            self._cleanup_thread = threading.Thread(target=self._cleanup_sessions, daemon=True)
            self._cleanup_thread.start()
            logger.info("会话清理线程已启动")

    def _cleanup_sessions(self):
        """定期清理过期会话"""
        while self._running:
            try:
                current_time = datetime.now()
                expired_sessions = []

                for session_id, session in self.sessions.items():
                    # 检查会话超时
                    if (current_time - session.last_activity).total_seconds() > self.session_timeout:
                        expired_sessions.append(session_id)
                        logger.info(f"会话 {session_id} 已超时，准备清理")

                # 清理过期会话
                for session_id in expired_sessions:
                    self.cleanup_session(session_id)

                # 每60秒检查一次
                time.sleep(60)

            except Exception as e:
                logger.error(f"会话清理过程中出错: {e}")
                time.sleep(60)

    def create_session(self) -> Dict[str, Any]:
        """
        创建新的浏览器会话

        Returns:
            Dict: 会话信息
        """
        if len(self.sessions) >= self.max_sessions:
            return {
                "success": False,
                "error": f"已达到最大并发会话数 ({self.max_sessions})，请稍后再试"
            }

        if webdriver is None:
            return {
                "success": False,
                "error": "Selenium未安装，请运行: pip install selenium undetected-chromedriver"
            }

        session_id = str(uuid.uuid4())
        session = BrowserSession(
            session_id=session_id,
            created_at=datetime.now(),
            last_activity=datetime.now()
        )

        try:
            # 在线程池中启动浏览器
            future = self.executor.submit(self._start_browser, session)
            result = future.result(timeout=30)  # 30秒超时

            if result["success"]:
                self.sessions[session_id] = session
                logger.info(f"浏览器会话 {session_id} 创建成功，调试端口: {session.debug_port}")
                return {
                    "success": True,
                    "session_id": session_id,
                    "debug_url": f"http://localhost:{session.debug_port}",
                    "instructions": f"请在浏览器中访问 http://localhost:{session.debug_port} 完成 YouTube 登录"
                }
            else:
                return result

        except Exception as e:
            logger.error(f"创建浏览器会话失败: {e}")
            return {
                "success": False,
                "error": f"创建浏览器会话失败: {str(e)}"
            }

    def _start_browser(self, session: BrowserSession) -> Dict[str, Any]:
        """在独立线程中启动浏览器"""
        try:
            # 创建临时用户数据目录
            temp_dir = tempfile.mkdtemp(prefix="browser_session_")
            session.user_data_dir = temp_dir

            # 配置Chrome选项
            chrome_options = Options()

            # 调试端口配置
            session.debug_port = self._get_available_port()
            chrome_options.add_argument(f"--remote-debugging-port={session.debug_port}")

            # 基本配置
            chrome_options.add_argument(f"--user-data-dir={temp_dir}")
            chrome_options.add_argument("--no-first-run")
            chrome_options.add_argument("--no-default-browser-check")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            chrome_options.add_argument("--disable-renderer-backgrounding")

            # 安全和性能配置
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-images")  # 提高性能
            chrome_options.add_argument("--disable-javascript")  # 提高性能，可根据需要启用

            # Headless模式（可选，用于Docker环境）
            if os.getenv("HEADLESS_BROWSER", "false").lower() == "true":
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--disable-gpu")

            # 尝试使用undetected-chromedriver
            try:
                driver = UndetectedChrome(options=chrome_options, version_main=None)
            except Exception:
                # 回退到标准Chrome
                try:
                    driver = webdriver.Chrome(options=chrome_options)
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"启动Chrome失败: {str(e)}"
                    }

            session.driver = driver
            session.process_id = driver.service.process.pid
            session.status = "ready"

            # 导航到YouTube登录页面
            driver.get("https://accounts.google.com/signin")

            return {"success": True}

        except Exception as e:
            logger.error(f"启动浏览器失败: {e}")
            if session.user_data_dir and os.path.exists(session.user_data_dir):
                import shutil
                shutil.rmtree(session.user_data_dir, ignore_errors=True)
            return {
                "success": False,
                "error": f"启动浏览器失败: {str(e)}"
            }

    def _get_available_port(self) -> int:
        """获取可用端口"""
        import socket
        for port in range(9222, 9322):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(('localhost', port))
                sock.close()
                return port
            except OSError:
                continue
        raise Exception("无法找到可用端口")

    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """
        获取会话状态

        Args:
            session_id: 会话ID

        Returns:
            Dict: 会话状态信息
        """
        if session_id not in self.sessions:
            return {
                "success": False,
                "error": "会话不存在或已过期"
            }

        session = self.sessions[session_id]
        session.last_activity = datetime.now()  # 更新活动时间

        # 检测登录状态
        if session.driver and session.status == "ready":
            try:
                current_url = session.driver.current_url
                if "youtube.com" in current_url and "accounts.google.com" not in current_url:
                    session.status = "login_complete"
                    session.youtube_logged_in = True
                    logger.info(f"会话 {session_id} 检测到YouTube登录成功")

                # 检查是否有YouTube cookies
                cookies = session.driver.get_cookies()
                youtube_cookies = [c for c in cookies if 'youtube.com' in c.get('domain', '')]
                if youtube_cookies:
                    session.youtube_logged_in = True

            except Exception as e:
                logger.warning(f"检测会话 {session_id} 状态失败: {e}")
                session.status = "error"
                session.error_message = str(e)

        # 获取进程资源使用情况
        resource_info = {}
        if session.process_id:
            try:
                process = psutil.Process(session.process_id)
                resource_info = {
                    "cpu_percent": process.cpu_percent(),
                    "memory_mb": process.memory_info().rss / 1024 / 1024,
                    "status": process.status()
                }
            except psutil.NoSuchProcess:
                resource_info = {"status": "process_not_found"}
            except Exception as e:
                resource_info = {"error": str(e)}

        return {
            "success": True,
            "session_id": session_id,
            "status": session.status,
            "youtube_logged_in": session.youtube_logged_in,
            "cookies_extracted": session.cookies_extracted,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "last_activity": session.last_activity.isoformat() if session.last_activity else None,
            "debug_url": f"http://localhost:{session.debug_port}" if session.debug_port else None,
            "resource_info": resource_info,
            "error_message": session.error_message
        }

    def extract_cookies(self, session_id: str) -> Dict[str, Any]:
        """
        提取会话中的YouTube cookies

        Args:
            session_id: 会话ID

        Returns:
            Dict: 提取结果
        """
        if session_id not in self.sessions:
            return {
                "success": False,
                "error": "会话不存在或已过期"
            }

        session = self.sessions[session_id]
        session.last_activity = datetime.now()

        if not session.driver:
            return {
                "success": False,
                "error": "浏览器会话不可用"
            }

        try:
            session.status = "extracting"

            # 获取所有cookies
            cookies = session.driver.get_cookies()
            youtube_cookies = {}

            for cookie in cookies:
                if 'youtube.com' in cookie.get('domain', ''):
                    youtube_cookies[cookie['name']] = cookie['value']

            if not youtube_cookies:
                return {
                    "success": False,
                    "error": "未找到YouTube cookies，请确保已完成YouTube登录"
                }

            # 转换为Netscape格式
            netscape_cookies = self._convert_to_netscape_format(youtube_cookies)

            session.cookies_extracted = True
            session.status = "completed"

            logger.info(f"会话 {session_id} 成功提取 {len(youtube_cookies)} 个YouTube cookies")

            return {
                "success": True,
                "session_id": session_id,
                "cookie_count": len(youtube_cookies),
                "cookies": youtube_cookies,
                "netscape_cookies": netscape_cookies
            }

        except Exception as e:
            logger.error(f"提取cookies失败: {e}")
            session.status = "error"
            session.error_message = str(e)
            return {
                "success": False,
                "error": f"提取cookies失败: {str(e)}"
            }

    def _convert_to_netscape_format(self, cookies: Dict[str, str]) -> str:
        """将cookies转换为Netscape格式"""
        lines = [
            "# Netscape HTTP Cookie File",
            "# This is a generated file! Do not edit.",
            ""
        ]

        for name, value in cookies.items():
            lines.append(f"\t.youtube.com\tTRUE\t/\tFALSE\t2147483647\t{name}\t{value}")

        return "\n".join(lines)

    def cleanup_session(self, session_id: str) -> bool:
        """
        清理会话资源

        Args:
            session_id: 会话ID

        Returns:
            bool: 清理是否成功
        """
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]

        try:
            # 关闭浏览器
            if session.driver:
                try:
                    session.driver.quit()
                except Exception as e:
                    logger.warning(f"关闭浏览器时出错: {e}")

            # 清理临时目录
            if session.user_data_dir and os.path.exists(session.user_data_dir):
                import shutil
                try:
                    shutil.rmtree(session.user_data_dir, ignore_errors=True)
                except Exception as e:
                    logger.warning(f"清理临时目录时出错: {e}")

            # 从会话字典中移除
            del self.sessions[session_id]

            logger.info(f"会话 {session_id} 清理完成")
            return True

        except Exception as e:
            logger.error(f"清理会话 {session_id} 时出错: {e}")
            return False

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """获取所有活跃会话信息"""
        sessions_info = []
        for session_id in list(self.sessions.keys()):
            status = self.get_session_status(session_id)
            if status["success"]:
                sessions_info.append(status)
        return sessions_info

    def shutdown(self):
        """关闭管理器并清理所有资源"""
        logger.info("正在关闭BrowserSessionManager...")

        self._running = False

        # 清理所有会话
        for session_id in list(self.sessions.keys()):
            self.cleanup_session(session_id)

        # 关闭线程池
        if self.executor:
            self.executor.shutdown(wait=True)

        logger.info("BrowserSessionManager已关闭")

# 创建全局实例
browser_session_manager = BrowserSessionManager()

# 注册清理函数
import atexit
atexit.register(browser_session_manager.shutdown)