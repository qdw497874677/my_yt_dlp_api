"""
浏览器Cookie自动扫描器
自动从各种浏览器提取YouTube cookies
"""

import os
import sqlite3
import json
import shutil
import tempfile
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import browser_cookie3
from .config import config

logger = logging.getLogger(__name__)

class BrowserCookieScanner:
    """浏览器Cookie扫描器"""

    def __init__(self):
        self.config = config
        self.config.ensure_directories()

    def scan_all_browsers(self) -> Dict[str, Dict]:
        """扫描所有支持的浏览器"""
        results = {}

        # 先检测哪些浏览器已安装
        from utils.browser_utils import detect_browsers
        installed_browsers = detect_browsers()

        for browser in self.config.supported_browsers:
            try:
                # 只扫描已安装的浏览器
                if not installed_browsers.get(browser, False):
                    logger.info(f"浏览器 {browser} 未安装，跳过扫描")
                    results[browser] = {
                        "success": False,
                        "error": "浏览器未安装",
                        "cookies": []
                    }
                    continue

                logger.info(f"正在扫描 {browser} 浏览器...")
                browser_result = self.scan_browser(browser)
                if browser_result["success"]:
                    results[browser] = browser_result
                    logger.info(f"{browser} 扫描成功，找到 {len(browser_result['cookies'])} 个cookies")
                else:
                    logger.warning(f"{browser} 扫描失败: {browser_result['error']}")
            except Exception as e:
                logger.error(f"扫描 {browser} 时发生错误: {e}")
                results[browser] = {
                    "success": False,
                    "error": str(e),
                    "cookies": []
                }

        return results

    def scan_browser(self, browser_name: str) -> Dict:
        """扫描指定浏览器的cookies"""
        try:
            # 使用browser_cookie3库提取cookies
            cookies = self._extract_cookies_with_browser_cookie3(browser_name)

            if not cookies:
                # 如果browser_cookie3失败，尝试直接读取数据库
                cookies = self._extract_cookies_from_database(browser_name)

            # 过滤YouTube相关cookies
            youtube_cookies = self._filter_youtube_cookies(cookies)

            if youtube_cookies:
                # 保存cookies到文件
                cookie_file = self._save_cookies_to_file(
                    youtube_cookies,
                    browser_name
                )

                return {
                    "success": True,
                    "cookies": youtube_cookies,
                    "cookie_file": cookie_file,
                    "count": len(youtube_cookies),
                    "browser": browser_name,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": "未找到YouTube相关cookies",
                    "cookies": []
                }

        except Exception as e:
            logger.error(f"扫描 {browser_name} 时发生错误: {e}")
            return {
                "success": False,
                "error": str(e),
                "cookies": []
            }

    def _extract_cookies_with_browser_cookie3(self, browser_name: str) -> List[Dict]:
        """使用browser_cookie3库提取cookies"""
        cookies = []

        try:
            # 只支持Edge浏览器
            if browser_name == "edge":
                import signal
                import threading

                def extract_with_timeout():
                    """带超时的cookie提取"""
                    try:
                        cookie_objects = browser_cookie3.edge(domain_name='youtube.com')
                        return cookie_objects
                    except Exception as e:
                        logger.error(f"browser_cookie3内部错误 {browser_name}: {e}")
                        return []

                # 使用线程来实现超时控制
                result = []
                exception = None

                def worker():
                    nonlocal result, exception
                    try:
                        result = extract_with_timeout()
                    except Exception as e:
                        exception = e

                thread = threading.Thread(target=worker)
                thread.start()
                thread.join(timeout=30)  # 30秒超时

                if thread.is_alive():
                    logger.warning(f"browser_cookie3提取 {browser_name} cookies超时")
                    return []

                if exception:
                    raise exception

                for cookie in result:
                    cookies.append({
                        "name": cookie.name,
                        "value": cookie.value,
                        "domain": cookie.domain,
                        "path": cookie.path,
                        "expires": cookie.expires,
                        "secure": cookie.secure,
                        "httponly": cookie._has_httponly
                    })

        except Exception as e:
            logger.warning(f"browser_cookie3提取 {browser_name} cookies失败: {e}")

        return cookies

    def _extract_cookies_from_database(self, browser_name: str) -> List[Dict]:
        """直接从浏览器数据库提取cookies"""
        cookies = []

        try:
            browser_config = self.config.browser_profiles.get(browser_name, {})
            if not browser_config:
                return cookies

            # 获取浏览器数据目录
            paths = self.config.get_browser_paths(browser_name)
            if not paths:
                return cookies

            # 查找cookie数据库文件
            cookie_db_name = browser_config.get("cookie_db", "Cookies")
            cookie_files = self._find_cookie_files(paths, cookie_db_name)

            for cookie_file in cookie_files:
                try:
                    # 复制数据库文件到临时位置（避免锁定）
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_file:
                        shutil.copy2(cookie_file, temp_file.name)

                        # 读取cookies
                        db_cookies = self._read_cookies_from_sqlite(
                            temp_file.name,
                            browser_name
                        )
                        cookies.extend(db_cookies)

                        # 清理临时文件
                        os.unlink(temp_file.name)

                except Exception as e:
                    logger.warning(f"读取cookie文件 {cookie_file} 失败: {e}")

        except Exception as e:
            logger.error(f"从数据库提取 {browser_name} cookies失败: {e}")

        return cookies

    def _find_cookie_files(self, search_paths: List[str], db_name: str) -> List[str]:
        """查找cookie数据库文件"""
        cookie_files = []

        for search_path in search_paths:
            try:
                path = Path(search_path)
                if path.exists():
                    # 递归查找cookie文件
                    for file_path in path.rglob(db_name):
                        if file_path.is_file():
                            cookie_files.append(str(file_path))
            except Exception as e:
                logger.warning(f"搜索路径 {search_path} 失败: {e}")

        return cookie_files

    def _read_cookies_from_sqlite(self, db_path: str, browser_name: str) -> List[Dict]:
        """从SQLite数据库读取cookies"""
        cookies = []

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # 不同浏览器的cookie表结构可能不同
            if browser_name == "firefox":
                # Firefox cookie表结构
                query = """
                SELECT name, value, host, path, expiry, isSecure, isHttpOnly
                FROM moz_cookies
                WHERE host LIKE '%.youtube.com' OR host = 'youtube.com'
                """
            else:
                # Chrome/Edge cookie表结构
                query = """
                SELECT name, value, host_key, path, expires_utc, is_secure, is_httponly
                FROM cookies
                WHERE host_key LIKE '%.youtube.com' OR host_key = 'youtube.com'
                """

            cursor.execute(query)
            rows = cursor.fetchall()

            for row in rows:
                if browser_name == "firefox":
                    name, value, host, path, expiry, is_secure, is_httponly = row
                else:
                    name, value, host, path, expires_utc, is_secure, is_httponly = row
                    # Chrome的过期时间使用Webkit时间戳
                    expiry = expires_utc / 1000000 - 11644473600 if expires_utc > 0 else 0

                cookies.append({
                    "name": name,
                    "value": value,
                    "domain": host,
                    "path": path,
                    "expires": expiry,
                    "secure": bool(is_secure),
                    "httponly": bool(is_httponly),
                    "browser": browser_name
                })

            conn.close()

        except Exception as e:
            logger.error(f"读取SQLite数据库 {db_path} 失败: {e}")

        return cookies

    def _filter_youtube_cookies(self, cookies: List[Dict]) -> List[Dict]:
        """过滤YouTube相关的cookies"""
        youtube_domains = [
            'youtube.com', '.youtube.com', 'www.youtube.com',
            'music.youtube.com', 'studio.youtube.com'
        ]

        youtube_cookie_names = {
            'VISITOR_INFO1_LIVE', 'YSC', 'PREF', 'CONSENT', 'GPS',
            'HSID', 'SSID', 'APISID', 'SAPISID', 'SID', 'SIDCC',
            'LOGIN_INFO', 'VISITOR_PRIVACY_METADATA', 'ACTIVITY_DATA'
        }

        filtered_cookies = []
        for cookie in cookies:
            domain = cookie.get('domain', '')
            name = cookie.get('name', '')

            # 检查域名
            domain_match = any(yt_domain in domain for yt_domain in youtube_domains)

            # 检查cookie名称
            name_match = name in youtube_cookie_names or any(
                keyword in name.lower() for keyword in ['login', 'auth', 'session', 'sid']
            )

            if domain_match and name_match:
                filtered_cookies.append(cookie)

        return filtered_cookies

    def _save_cookies_to_file(self, cookies: List[Dict], browser_name: str) -> str:
        """保存cookies到Netscape格式文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"youtube_{browser_name}_auto_{timestamp}.txt"
        filepath = os.path.join(self.config.cookie_directory, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                # 写入文件头
                f.write("# Netscape HTTP Cookie File\n")
                f.write(f"# Generated by yt-dlp API Auto Scanner\n")
                f.write(f"# Browser: {browser_name}\n")
                f.write(f"# Generated at: {datetime.now().isoformat()}\n")
                f.write(f"# Cookie count: {len(cookies)}\n\n")

                # 写入cookies
                for cookie in cookies:
                    domain = cookie.get('domain', '')
                    flag = "TRUE" if domain.startswith('.') else "FALSE"
                    path = cookie.get('path', '/')
                    secure = "TRUE" if cookie.get('secure', False) else "FALSE"
                    expires = int(cookie.get('expires', 0))
                    name = cookie.get('name', '')
                    value = cookie.get('value', '')

                    f.write(f"{domain}\t{flag}\t{path}\t{secure}\t{expires}\t{name}\t{value}\n")

            # 设置文件权限
            os.chmod(filepath, 0o600)

            logger.info(f"Cookies已保存到: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"保存cookies文件失败: {e}")
            raise

    def get_scan_summary(self, scan_results: Dict[str, Dict]) -> Dict:
        """生成扫描结果摘要"""
        summary = {
            "total_browsers": len(scan_results),
            "successful_browsers": 0,
            "total_cookies": 0,
            "browser_details": [],
            "latest_cookie_file": None,
            "scan_time": datetime.now().isoformat()
        }

        for browser, result in scan_results.items():
            if result["success"]:
                summary["successful_browsers"] += 1
                summary["total_cookies"] += result["count"]

                summary["browser_details"].append({
                    "browser": browser,
                    "cookie_count": result["count"],
                    "cookie_file": result.get("cookie_file"),
                    "timestamp": result.get("timestamp")
                })

                # 记录最新的cookie文件
                if result.get("cookie_file"):
                    if (summary["latest_cookie_file"] is None or
                        result.get("timestamp") > summary["latest_cookie_file"].get("timestamp", "")):
                        summary["latest_cookie_file"] = {
                            "file": result["cookie_file"],
                            "browser": browser,
                            "timestamp": result.get("timestamp")
                        }

        return summary