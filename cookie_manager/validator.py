"""
Cookie验证和管理器
验证cookie有效性，管理过期和续期
"""

import os
import json
import asyncio
import aiohttp
import yt_dlp
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from .config import config

logger = logging.getLogger(__name__)

class CookieValidator:
    """Cookie验证器"""

    def __init__(self):
        self.config = config
        self.cache = {}  # 验证结果缓存
        self.cache_timeout = 300  # 缓存5分钟

    async def validate_cookie_file(self, cookie_file: str, detailed: bool = True) -> Dict:
        """验证cookie文件有效性"""
        # 检查缓存
        cache_key = f"{cookie_file}_{detailed}"
        if cache_key in self.cache:
            cached_result, timestamp = self.cache[cache_key]
            if datetime.now().timestamp() - timestamp < self.cache_timeout:
                return cached_result

        if not os.path.exists(cookie_file):
            result = {
                "valid": False,
                "error": "Cookie文件不存在",
                "file_path": cookie_file,
                "timestamp": datetime.now().isoformat()
            }
            self.cache[cache_key] = (result, datetime.now().timestamp())
            return result

        try:
            # 解析cookie文件信息
            metadata = self._parse_cookie_metadata(cookie_file)

            # 检查文件大小
            file_size = os.path.getsize(cookie_file)
            if file_size == 0:
                result = {
                    "valid": False,
                    "error": "Cookie文件为空",
                    "file_size": file_size,
                    "metadata": metadata,
                    "timestamp": datetime.now().isoformat()
                }
                self.cache[cache_key] = (result, datetime.now().timestamp())
                return result

            # 在线验证
            validation_result = await self._online_validation(cookie_file, detailed)

            result = {
                **validation_result,
                "file_path": cookie_file,
                "file_size": file_size,
                "metadata": metadata,
                "timestamp": datetime.now().isoformat()
            }

            # 缓存结果
            self.cache[cache_key] = (result, datetime.now().timestamp())
            return result

        except Exception as e:
            error_result = {
                "valid": False,
                "error": f"验证过程出错: {str(e)}",
                "file_path": cookie_file,
                "timestamp": datetime.now().isoformat()
            }
            self.cache[cache_key] = (error_result, datetime.now().timestamp())
            return error_result

    async def _online_validation(self, cookie_file: str, detailed: bool) -> Dict:
        """在线验证cookie有效性"""
        try:
            # 使用yt-dlp进行验证
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'cookiefile': cookie_file,
                'socket_timeout': self.config.validation_timeout,
            }

            test_url = f"{self.config.validation_urls['youtube']}{self.config.test_video_id}"

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(test_url, download=False)

                if not info or not info.get('title'):
                    return {
                        "valid": False,
                        "error": "无法获取视频信息，Cookie可能已失效",
                        "test_url": test_url
                    }

                # 分析视频信息
                validation_data = {
                    "valid": True,
                    "test_url": test_url,
                    "video_title": info.get('title'),
                    "video_id": info.get('id'),
                    "duration": info.get('duration'),
                    "uploader": info.get('uploader'),
                    "view_count": info.get('view_count'),
                    "upload_date": info.get('upload_date'),
                }

                if detailed:
                    # 详细验证
                    validation_data.update({
                        "age_restricted": info.get('age_limit', 0) >= 18,
                        "premium_content": self._check_premium_content(info),
                        "live_content": info.get('is_live', False),
                        "formats_available": len(info.get('formats', [])),
                        "can_download": True
                    })

                    # 测试不同类型的访问
                    validation_data["access_tests"] = await self._test_access_variability(cookie_file)

                return validation_data

        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            if "HTTP Error 401" in error_msg or "Unauthorized" in error_msg:
                return {
                    "valid": False,
                    "error": "Cookie认证失败 (401 Unauthorized)",
                    "test_url": test_url
                }
            elif "HTTP Error 403" in error_msg or "Forbidden" in error_msg:
                return {
                    "valid": False,
                    "error": "访问被禁止，Cookie可能已失效 (403 Forbidden)",
                    "test_url": test_url
                }
            else:
                return {
                    "valid": False,
                    "error": f"下载错误: {error_msg}",
                    "test_url": test_url
                }
        except Exception as e:
            return {
                "valid": False,
                "error": f"验证过程中发生错误: {str(e)}",
                "test_url": test_url if 'test_url' in locals() else "unknown"
            }

    async def _test_access_variability(self, cookie_file: str) -> Dict:
        """测试对不同内容的访问权限"""
        access_tests = {}

        test_urls = {
            "premium": self.config.validation_urls["youtube_premium"],
            "music": self.config.validation_urls["youtube_music"],
            "shorts": f"{self.config.validation_urls['youtube_shorts']}ABC123",
            "regular": f"{self.config.validation_urls['youtube']}{self.config.test_video_id}"
        }

        for test_type, url in test_urls.items():
            try:
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'skip_download': True,
                    'cookiefile': cookie_file,
                    'socket_timeout': 10,
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    access_tests[test_type] = {
                        "accessible": True,
                        "title": info.get('title', 'Unknown'),
                        "requires_auth": "login" in str(info).lower() or "sign" in str(info).lower()
                    }

            except Exception as e:
                access_tests[test_type] = {
                    "accessible": False,
                    "error": str(e)
                }

        return access_tests

    def _check_premium_content(self, info: Dict) -> bool:
        """检查是否为Premium内容"""
        # 检查各种Premium指标
        premium_indicators = [
            "premium" in str(info).lower(),
            "paid" in str(info).lower(),
            info.get('availability') == 'premium_only',
            any(fmt.get('has_drm') for fmt in info.get('formats', []))
        ]
        return any(premium_indicators)

    def _parse_cookie_metadata(self, cookie_file: str) -> Dict:
        """解析cookie文件元数据"""
        metadata = {
            "file_exists": os.path.exists(cookie_file),
            "file_size": os.path.getsize(cookie_file) if os.path.exists(cookie_file) else 0,
            "created_time": None,
            "modified_time": None,
            "browser_source": "unknown",
            "cookie_count": 0,
            "domains": [],
            "estimated_expiry": None
        }

        try:
            stat = os.stat(cookie_file)
            metadata["created_time"] = datetime.fromtimestamp(stat.st_ctime).isoformat()
            metadata["modified_time"] = datetime.fromtimestamp(stat.st_mtime).isoformat()

            # 解析文件内容
            with open(cookie_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            # 分析文件头信息
            for line in lines[:10]:  # 只检查前10行
                line = line.strip()
                if line.startswith("# Browser:"):
                    metadata["browser_source"] = line.replace("# Browser:", "").strip()
                elif line.startswith("# Cookie count:"):
                    try:
                        metadata["cookie_count"] = int(line.replace("# Cookie count:", "").strip())
                    except:
                        pass

            # 分析域名信息
            domains = set()
            for line in lines:
                if not line.startswith('#') and '\t' in line:
                    parts = line.split('\t')
                    if len(parts) >= 1:
                        domain = parts[0].strip()
                        if domain and not domain.startswith('#'):
                            domains.add(domain)

            metadata["domains"] = list(domains)

            # 估算过期时间
            if "youtube" in str(metadata["domains"]).lower():
                # YouTube cookies通常有效期2-6个月
                created_time = datetime.fromisoformat(metadata["created_time"]) if metadata["created_time"] else datetime.now()
                metadata["estimated_expiry"] = (created_time + timedelta(days=120)).isoformat()

        except Exception as e:
            logger.warning(f"解析cookie元数据失败: {e}")

        return metadata

    def get_cookie_health_status(self, validation_result: Dict) -> str:
        """获取cookie健康状态"""
        if not validation_result.get("valid", False):
            return "invalid"

        # 检查过期时间
        metadata = validation_result.get("metadata", {})
        estimated_expiry = metadata.get("estimated_expiry")

        if estimated_expiry:
            try:
                expiry_date = datetime.fromisoformat(estimated_expiry)
                days_remaining = (expiry_date - datetime.now()).days

                if days_remaining <= self.config.critical_threshold_days:
                    return "critical"
                elif days_remaining <= self.config.warning_threshold_days:
                    return "warning"
                else:
                    return "healthy"
            except:
                pass

        # 基于文件修改时间估算
        modified_time = metadata.get("modified_time")
        if modified_time:
            try:
                modified_date = datetime.fromisoformat(modified_time)
                days_ago = (datetime.now() - modified_date).days

                if days_ago > 100:  # 超过100天可能接近过期
                    return "warning"
                elif days_ago > 150:  # 超过150天可能已过期
                    return "critical"
            except:
                pass

        return "unknown"

    def get_health_recommendation(self, health_status: str) -> str:
        """获取健康状态建议"""
        recommendations = {
            "healthy": "Cookie状态良好，可以正常使用",
            "warning": "Cookie可能即将过期，建议准备更新",
            "critical": "Cookie即将过期或已失效，请立即更新",
            "invalid": "Cookie已失效，需要重新获取",
            "unknown": "无法确定Cookie状态，建议验证后使用"
        }
        return recommendations.get(health_status, "状态未知")

class CookieManager:
    """Cookie管理器 - 统一管理cookie生命周期"""

    def __init__(self):
        self.validator = CookieValidator()
        self.config = config
        self.active_cookies = {}  # 当前活跃的cookies
        self.cookie_stats = {}    # Cookie使用统计

    async def auto_scan_and_validate(self) -> Dict:
        """自动扫描和验证cookies"""
        from .scanner import BrowserCookieScanner

        scanner = BrowserCookieScanner()
        logger.info("开始自动扫描浏览器cookies...")

        # 扫描所有浏览器
        scan_results = scanner.scan_all_browsers()
        summary = scanner.get_scan_summary(scan_results)

        # 验证找到的cookies
        validation_results = {}
        best_cookie = None
        best_score = 0

        for browser, result in scan_results.items():
            if result["success"] and result.get("cookie_file"):
                cookie_file = result["cookie_file"]
                validation = await self.validator.validate_cookie_file(cookie_file)

                validation_results[browser] = validation

                # 评分并选择最佳cookie
                if validation.get("valid"):
                    score = self._calculate_cookie_score(validation)
                    if score > best_score:
                        best_score = score
                        best_cookie = cookie_file

        # 更新活跃cookies
        if best_cookie:
            await self._set_active_cookie(best_cookie)

        return {
            "scan_summary": summary,
            "validation_results": validation_results,
            "best_cookie": best_cookie,
            "best_score": best_score,
            "timestamp": datetime.now().isoformat()
        }

    def _calculate_cookie_score(self, validation_result: Dict) -> float:
        """计算cookie质量分数"""
        score = 0.0

        # 基础分数
        if validation_result.get("valid"):
            score += 50

        # 访问能力测试
        access_tests = validation_result.get("access_tests", {})
        for test_type, result in access_tests.items():
            if result.get("accessible"):
                score += 10

        # Premium功能
        if validation_result.get("premium_content"):
            score += 20

        # 健康状态
        health_status = self.validator.get_cookie_health_status(validation_result)
        if health_status == "healthy":
            score += 20
        elif health_status == "warning":
            score += 10
        elif health_status == "critical":
            score += 5

        # 格式数量
        formats_available = validation_result.get("formats_available", 0)
        score += min(formats_available / 10, 10)  # 最多加10分

        return min(score, 100)  # 最高100分

    async def _set_active_cookie(self, cookie_file: str):
        """设置活跃cookie"""
        if os.path.exists(cookie_file):
            self.active_cookies["default"] = cookie_file
            self.cookie_stats[cookie_file] = {
                "set_time": datetime.now().isoformat(),
                "usage_count": 0,
                "last_used": None,
                "valid": True
            }
            logger.info(f"设置活跃cookie: {cookie_file}")

    def get_active_cookie(self) -> Optional[str]:
        """获取当前活跃的cookie文件"""
        return self.active_cookies.get("default")

    async def validate_active_cookie(self) -> Dict:
        """验证当前活跃的cookie"""
        active_cookie = self.get_active_cookie()
        if not active_cookie:
            return {
                "valid": False,
                "error": "没有活跃的cookie",
                "recommendation": "请运行自动扫描获取cookies"
            }

        return await self.validator.validate_cookie_file(active_cookie)

    async def cleanup_expired_cookies(self):
        """清理过期的cookies"""
        cookie_dir = Path(self.config.cookie_directory)
        if not cookie_dir.exists():
            return

        cleaned_count = 0
        for cookie_file in cookie_dir.glob("*.txt"):
            try:
                validation = await self.validator.validate_cookie_file(str(cookie_file), detailed=False)
                health_status = self.validator.get_cookie_health_status(validation)

                if health_status in ["invalid", "critical"]:
                    # 移动到备份目录而不是直接删除
                    backup_dir = Path(self.config.backup_directory)
                    backup_dir.mkdir(exist_ok=True)

                    backup_file = backup_dir / f"{cookie_file.name}.bak"
                    shutil.move(str(cookie_file), str(backup_file))
                    cleaned_count += 1

                    logger.info(f"已移动过期cookie到备份: {cookie_file} -> {backup_file}")

            except Exception as e:
                logger.warning(f"清理cookie文件失败 {cookie_file}: {e}")

        logger.info(f"清理完成，共处理 {cleaned_count} 个过期cookie文件")
        return {"cleaned_count": cleaned_count}