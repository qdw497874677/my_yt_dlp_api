import yt_dlp
import os
import uuid
import shutil
import logging

import asyncio

import json
import datetime
import sqlite3
from typing import Dict, Any, Optional, List
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
import uvicorn
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor

# 导入cookie管理模块
from cookie_manager import (
    auto_cookie_manager,
    auto_setup_cookies,
    get_cookie_status,
    refresh_cookies
)

# 导入调度器管理模块
from scheduler_manager import scheduler_manager, SchedulerConfig

# 导入浏览器会话管理模块
from browser_session_manager import browser_session_manager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def NormalizeString(s: str, max_length: int = 200) -> str:
    """
    去掉头尾的空格， 所有特殊字符转换成 _，并限制长度
    """
    s = s.strip()
    # 替换特殊字符
    special_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for char in special_chars:
        s = s.replace(char, '_')
    
    # 限制长度，如果超长则截断并保持可读性
    if len(s) > max_length:
        # 保留前面的内容，并在末尾添加省略标记
        s = s[:max_length-3] + "..."
    
    return s

def create_safe_filename(title: str, format_str: str, ext: str, max_length: int = 200) -> str:
    """
    创建安全的文件名，确保不超过指定长度
    
    Args:
        title (str): 视频标题
        format_str (str): 格式字符串
        ext (str): 文件扩展名
        max_length (int): 最大文件名长度
        
    Returns:
        str: 安全的文件名
    """
    # 标准化格式字符串和扩展名
    safe_format = NormalizeString(format_str, 50)  # 格式前缀限制50字符
    safe_ext = ext.lower()
    
    # 计算标题可用的最大长度
    # 预留空间给格式前缀、分隔符和扩展名
    reserved_length = len(safe_format) + len(safe_ext) + 2  # 2个字符用于连接符
    available_title_length = max_length - reserved_length
    
    # 确保至少有20个字符用于标题
    if available_title_length < 20:
        available_title_length = 20
        safe_format = safe_format[:10]  # 缩短格式前缀
    
    # 标准化并截断标题
    safe_title = NormalizeString(title, available_title_length)
    
    # 构建最终文件名
    if safe_format:
        return f"{safe_format}-{safe_title}.{safe_ext}"
    else:
        return f"{safe_title}.{safe_ext}"

class Task(BaseModel):
    id: str
    url: str
    output_path: str
    format: str
    status: str
    task_type: str = "video"  # 新增：任务类型，默认为video
    subtitle_config: Optional[Dict[str, Any]] = None  # 新增：字幕特定配置
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# 调度器相关的 Pydantic 模型
class SchedulerConfigRequest(BaseModel):
    enabled: Optional[bool] = None
    cron_expression: Optional[str] = None
    timezone: Optional[str] = None
    max_retries: Optional[int] = None
    retry_delay: Optional[int] = None

class SchedulerStatusResponse(BaseModel):
    running: bool
    config: Dict[str, Any]
    next_run: Optional[str] = None

class UpdateHistoryResponse(BaseModel):
    id: int
    timestamp: str
    old_version: Optional[str] = None
    new_version: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    retry_count: int

class State:
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        # 确保data目录存在
        os.makedirs("data", exist_ok=True)
        self.db_file = "data/tasks.db"
        # 初始化数据库
        self._init_db()
        # 从数据库加载任务状态
        self._load_tasks()
        # 初始化cookie管理
        self.cookie_initialized = False
    
    def _init_db(self) -> None:
        """初始化SQLite数据库"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # 创建任务表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            output_path TEXT NOT NULL,
            format TEXT NOT NULL,
            status TEXT NOT NULL,
            task_type TEXT DEFAULT 'video',
            subtitle_config TEXT,
            result TEXT,
            error_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        ''')

        # 创建性能优化索引
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(task_type)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_tasks_type_status ON tasks(task_type, status)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_tasks_status_updated ON tasks(status, updated_at)
        ''')

        # 检查并添加新字段（向后兼容）
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [column[1] for column in cursor.fetchall()]

        # 如果没有task_type字段，则添加
        if 'task_type' not in columns:
            cursor.execute("ALTER TABLE tasks ADD COLUMN task_type TEXT DEFAULT 'video'")

        # 如果没有subtitle_config字段，则添加
        if 'subtitle_config' not in columns:
            cursor.execute("ALTER TABLE tasks ADD COLUMN subtitle_config TEXT")

        conn.commit()
        conn.close()
    
    def _load_tasks(self) -> None:
        """从数据库加载任务状态"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            # 检查是否有新字段
            cursor.execute("PRAGMA table_info(tasks)")
            columns = [column[1] for column in cursor.fetchall()]

            # 根据字段情况选择查询语句
            if 'task_type' in columns and 'subtitle_config' in columns:
                cursor.execute("""
                    SELECT id, url, output_path, format, status, task_type, subtitle_config, result, error_json
                    FROM tasks
                """)
            else:
                # 向后兼容，旧版本数据库
                cursor.execute("""
                    SELECT id, url, output_path, format, status, 'video', NULL, result, error_json
                    FROM tasks
                """)

            rows = cursor.fetchall()

            for row in rows:
                task_id, url, output_path, format, status, task_type, subtitle_config_json, result_json, error = row

                # 解析JSON结果（如果有）
                result = json.loads(result_json) if result_json else None
                error = json.loads(error) if error else None
                subtitle_config = json.loads(subtitle_config_json) if subtitle_config_json else None

                # 创建Task对象并存储在内存中
                task = Task(
                    id=task_id,
                    url=url,
                    output_path=output_path,
                    format=format,
                    status=status,
                    task_type=task_type,
                    subtitle_config=subtitle_config,
                    result=result,
                    error=error
                )
                self.tasks[task_id] = task

            conn.close()
        except Exception as e:
            print(f"Error loading tasks from database: {e}")
    
    def _save_task(self, task: Task) -> None:
        """将任务状态保存到数据库"""
        try:
            # 先更新内存中的任务状态
            self.tasks[task.id] = task

            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            timestamp = datetime.datetime.now().isoformat()
            result_json = json.dumps(task.result) if task.result else None
            error_json = json.dumps(task.error) if task.error else None
            subtitle_config_json = json.dumps(task.subtitle_config) if task.subtitle_config else None

            # 检查表是否有新字段
            cursor.execute("PRAGMA table_info(tasks)")
            columns = [column[1] for column in cursor.fetchall()]

            # 根据表结构选择SQL语句
            if 'task_type' in columns and 'subtitle_config' in columns:
                # 新版本表结构
                cursor.execute('''
                INSERT OR REPLACE INTO tasks (id, url, output_path, format, status, task_type, subtitle_config, result, error_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    task.id,
                    task.url,
                    task.output_path,
                    task.format,
                    task.status,
                    task.task_type,
                    subtitle_config_json,
                    result_json,
                    error_json,
                    timestamp,
                    timestamp
                ))
            else:
                # 旧版本表结构（向后兼容）
                cursor.execute('''
                INSERT OR REPLACE INTO tasks (id, url, output_path, format, status, result, error_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    task.id,
                    task.url,
                    task.output_path,
                    task.format,
                    task.status,
                    result_json,
                    error_json,
                    timestamp,
                    timestamp
                ))

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error saving task to database: {e}")
    
    def add_task(self, url: str, output_path: str, format: str, task_type: str = "video", subtitle_config: Optional[Dict[str, Any]] = None) -> str:
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            url=url,
            output_path=output_path,
            format=format,
            status="pending",
            task_type=task_type,
            subtitle_config=subtitle_config
        )
        self.tasks[task_id] = task

        # 将任务保存到数据库
        self._save_task(task)

        return task_id
    
    def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)
    
    def update_task(self, task_id: str, status: str, result: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> None:
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = status
            if result:
                task.result = result
            if error:
                task.error = error
            
            # 将更新后的任务状态保存到数据库
            self._save_task(task)
    
    def list_tasks(self) -> List[Task]:
        return list(self.tasks.values())
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        if task_id in self.tasks:
            # 从内存中删除任务
            del self.tasks[task_id]

            # 从数据库中删除任务
            try:
                conn = sqlite3.connect(self.db_file)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"Error deleting task from database: {e}")
                return False
        return False

    async def initialize_cookies(self) -> Dict:
        """初始化cookie管理"""
        if not self.cookie_initialized:
            logger.info("正在初始化cookie管理...")
            try:
                result = await auto_setup_cookies()
                self.cookie_initialized = True

                # 确保结果可以被JSON序列化（转换PosixPath为字符串）
                if isinstance(result.get("active_cookie"), Path):
                    result["active_cookie"] = str(result["active_cookie"])

                return result
            except Exception as e:
                logger.error(f"Cookie初始化失败: {e}")
                return {"success": False, "error": str(e)}
        else:
            return {"success": True, "message": "Cookie已初始化"}

    async def get_cookies_for_download(self, url: str) -> Optional[str]:
        """获取下载用的cookies（智能选择策略）"""
        # 优先使用增强的cookie管理器的智能选择策略
        try:
            best_cookie = await auto_cookie_manager.get_best_cookie_for_download(url)
            if best_cookie:
                return best_cookie
        except Exception as e:
            logger.warning(f"智能cookie选择失败，回退到传统方式: {e}")

        # 回退到原有的逻辑
        if not self.cookie_initialized:
            await self.initialize_cookies()

        # 获取活跃的cookie文件
        active_cookie = auto_cookie_manager.get_active_cookie_path()

        if active_cookie:
            # 快速验证cookie有效性
            try:
                validation = await auto_cookie_manager.validate_cookie_file(active_cookie, detailed=False)
                if validation.get("valid"):
                    return active_cookie
                else:
                    logger.warning(f"活跃cookie已失效: {active_cookie}")
            except Exception as e:
                logger.warning(f"验证cookie失败: {e}")

        # 如果没有活跃cookie或已失效，尝试刷新
        logger.info("尝试刷新cookies...")
        try:
            refresh_result = await refresh_cookies()
            if refresh_result.get("success"):
                return refresh_result.get("new_cookie")
        except Exception as e:
            logger.error(f"刷新cookies失败: {e}")

        return None

# 创建全局状态对象
state = State()

def delete_task_file(task: Task) -> bool:
    """
    删除任务对应的文件
    
    Args:
        task (Task): 任务对象
        
    Returns:
        bool: 删除成功返回True，否则返回False
    """
    if not task or task.status != "completed" or not task.result:
        return False
    
    try:
        # 从结果中提取文件名和路径
        filename = None
        
        # 首先尝试从requested_downloads获取文件名
        requested_downloads = task.result.get("requested_downloads", [])
        if requested_downloads and len(requested_downloads) > 0:
            filename = requested_downloads[0].get("filepath") or requested_downloads[0].get("filename")
        
        # 如果没有找到，尝试从requested_filename获取
        if not filename:
            requested_filename = task.result.get("requested_filename")
            if requested_filename:
                filename = requested_filename
        
        # 如果仍然没有找到，尝试构建文件路径
        if not filename:
            title = task.result.get("title", "video")
            ext = task.result.get("ext", "mp4")
            # 使用安全的文件名生成函数
            safe_filename = create_safe_filename(title, task.format, ext)
            filename = os.path.join(task.output_path, safe_filename)
        
        # 检查文件是否存在
        if not filename or not os.path.exists(filename):
            # 如果文件不存在，尝试在output_path目录中查找匹配的文件
            if os.path.exists(task.output_path):
                # 获取output_path目录中的所有文件
                files = os.listdir(task.output_path)
                # 尝试匹配标题的文件
                title = task.result.get("title", "video")
                # 移除特殊字符并转换为小写进行匹配
                normalized_title = NormalizeString(title).lower()
                for file in files:
                    # 检查文件名是否包含标题
                    if normalized_title in file.lower():
                        filename = os.path.join(task.output_path, file)
                        break
        
        # 检查文件是否存在并删除
        if filename and os.path.exists(filename):
            os.remove(filename)
            logger.info(f"已删除任务文件: {filename}")
            return True
        else:
            logger.warning(f"任务文件不存在: {filename}")
            return False
    except Exception as e:
        logger.error(f"删除任务文件失败: {e}")
        return False


def download_video(url: str, output_path: str = "./downloads", format: str = "best", quiet: bool = False, cookies: str = None) -> Dict[str, Any]:
    """
    Download a video from the specified URL using yt-dlp.
    
    Args:
        url (str): The URL of the video to download
        output_path (str): Directory where the video will be saved
        format (str): Video format to download (e.g., "best", "bestvideo+bestaudio", "mp4")
        quiet (bool): If True, suppress output
        cookies (str): Path to cookies file or browser name for cookies
        
    Returns:
        Dict[str, Any]: Information about the downloaded video
    """
    logger.info(f"开始下载视频: {url}")
    
    # 进度钩子函数
    def progress_hook(d):
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', 'N/A')
            speed = d.get('_speed_str', 'N/A')
            eta = d.get('_eta_str', 'N/A')
            logger.info(f"下载进度: {percent} 速度: {speed} 剩余时间: {eta}")
        elif d['status'] == 'finished':
            logger.info("下载完成，正在处理文件...")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_path, exist_ok=True)
    
    # Configure yt-dlp options
    ydl_opts = {
        'outtmpl': os.path.join(output_path, '%(title).180s.%(ext)s'),
        'quiet': quiet,
        'no_warnings': quiet,
        'format': format,
        'no_abort_on_error': True,
        # 添加进度钩子来处理文件名
        'progress_hooks': [progress_hook],
        # 反机器人检测配置
        'extractor_args': {
            'youtube': {
                'player_client': 'default',  # 使用默认客户端避免iOS客户端问题
            }
        },
        # 设置用户代理
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        },
        # 增加超时和重试
        'socket_timeout': 30,
        'retries': 3,
        'fragment_retries': 3,
    }

    # 如果需要更安全的处理，我们可以在下载前先获取信息
    temp_ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        # 反机器人检测配置
        'extractor_args': {
            'youtube': {
                'player_client': 'default',  # 使用默认客户端避免iOS客户端问题
            }
        },
        # 设置用户代理
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        },
        # 增加超时和重试
        'socket_timeout': 30,
        'retries': 3,
        'fragment_retries': 3,
    }
    
    # 添加cookie支持到temp_ydl_opts
    if cookies:
        if cookies.endswith('.txt'):
            # 如果是cookies文件路径
            temp_ydl_opts['cookiefile'] = cookies
        else:
            # 如果是浏览器名称
            temp_ydl_opts['cookiesfrombrowser'] = (cookies,)
    
    # 添加cookie支持
    if cookies:
        if cookies.endswith('.txt'):
            # 如果是cookies文件路径
            ydl_opts['cookiefile'] = cookies
        else:
            # 如果是浏览器名称
            ydl_opts['cookiesfrombrowser'] = (cookies,)
    
    try:
        # 先获取视频信息来生成安全的文件名
        with yt_dlp.YoutubeDL(temp_ydl_opts) as temp_ydl:
            info = temp_ydl.extract_info(url, download=False)
            if info:
                title = info.get('title', 'video')
                ext = info.get('ext', 'mp4')
                safe_filename = create_safe_filename(title, format, ext)
                ydl_opts['outtmpl'] = os.path.join(output_path, safe_filename)
                logger.info(f"使用安全文件名: {safe_filename}")
    except Exception as e:
        logger.warning(f"获取视频信息失败，使用默认模板: {e}")
        # 如果获取信息失败，使用默认的安全模板
        pass
    
    # Download the video
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            result = ydl.sanitize_info(info)
            logger.info("视频下载完成")
            return result
    except Exception as e:
        logger.error(f"下载失败: {e}")
        raise

def get_video_info(url: str, quiet: bool = False, cookies: str = None) -> Dict[str, Any]:
    """
    Get information about a video without downloading it.

    Args:
        url (str): The URL of the video
        quiet (bool): If True, suppress output
        cookies (str): Path to cookies file or browser name for cookies

    Returns:
        Dict[str, Any]: Information about the video
    """
    ydl_opts = {
        'quiet': quiet,
        'no_warnings': quiet,
        'skip_download': True,
        # 反机器人检测配置
        'extractor_args': {
            'youtube': {
                'player_client': 'default',  # 使用默认客户端避免iOS客户端问题
            }
        },
        # 设置用户代理
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
        },
        # 增加超时和重试
        'socket_timeout': 30,
        'retries': 3,
        'fragment_retries': 3,
    }

    # 添加cookie支持
    if cookies:
        if cookies.endswith('.txt'):
            # 如果是cookies文件路径
            ydl_opts['cookiefile'] = cookies
        else:
            # 如果是浏览器名称
            ydl_opts['cookiesfrombrowser'] = (cookies,)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return ydl.sanitize_info(info)

def list_available_formats(url: str, cookies: str = None) -> List[Dict[str, Any]]:
    """
    List all available formats for a video.

    Args:
        url (str): The URL of the video
        cookies (str): Path to cookies file or browser name for cookies

    Returns:
        List[Dict[str, Any]]: List of available formats
    """
    info = get_video_info(url, cookies=cookies)
    if not info:
        return []

    return info.get('formats', [])

def get_video_thumbnails(url: str, cookies: str = None) -> List[Dict[str, Any]]:
    """
    Get video thumbnails in different resolutions.

    Args:
        url (str): The URL of the video
        cookies (str): Path to cookies file or browser name for cookies

    Returns:
        List[Dict[str, Any]]: List of thumbnail information
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'list_thumbnails': True,
    }

    # 添加cookie支持
    if cookies:
        if cookies.endswith('.txt'):
            ydl_opts['cookiefile'] = cookies
        else:
            ydl_opts['cookiesfrombrowser'] = (cookies,)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        thumbnails = info.get('thumbnails', [])

        # 整理缩略图信息
        processed_thumbnails = []
        for thumb in thumbnails:
            processed_thumbnails.append({
                'url': thumb.get('url'),
                'width': thumb.get('width'),
                'height': thumb.get('height'),
                'resolution': f"{thumb.get('width', '?')}x{thumb.get('height', '?')}",
                'preference': thumb.get('preference', 0),
                'id': thumb.get('id')
            })

        # 按偏好排序，高质量在前
        processed_thumbnails.sort(key=lambda x: x.get('preference', 0), reverse=True)

        return processed_thumbnails

def get_video_subtitles(url: str, cookies: str = None) -> Dict[str, Any]:
    """
    Get available subtitles for a video.

    Args:
        url (str): The URL of the video
        cookies (str): Path to cookies file or browser name for cookies

    Returns:
        Dict[str, Any]: Subtitle information including available languages
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'listsubtitles': True,
        'writesubtitles': False,
        'writeautomaticsub': False,
    }

    # 添加cookie支持
    if cookies:
        if cookies.endswith('.txt'):
            ydl_opts['cookiefile'] = cookies
        else:
            ydl_opts['cookiesfrombrowser'] = (cookies,)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        return {
            'subtitles': info.get('subtitles', {}),
            'automatic_captions': info.get('automatic_captions', {}),
            'available_languages': list(info.get('subtitles', {}).keys()),
            'automatic_languages': list(info.get('automatic_captions', {}).keys())
        }

def download_subtitle(url: str, language: str, subtitle_format: str = "srt", cookies: str = None) -> str:
    """
    Download subtitle for a video in specified language and format.

    Args:
        url (str): The URL of the video
        language (str): Language code (e.g., 'en', 'zh', 'ja')
        subtitle_format (str): Subtitle format (e.g., 'srt', 'vtt', 'ass')
        cookies (str): Path to cookies file or browser name for cookies

    Returns:
        str: Path to downloaded subtitle file
    """
    import tempfile
    import os

    # 创建临时目录
    temp_dir = tempfile.mkdtemp()

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': [language],
        'subtitlesformat': subtitle_format,
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
    }

    # 添加cookie支持
    if cookies:
        if cookies.endswith('.txt'):
            ydl_opts['cookiefile'] = cookies
        else:
            ydl_opts['cookiesfrombrowser'] = (cookies,)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)

            # 检查是否有请求的字幕
            subtitles = info.get('subtitles', {})
            automatic_captions = info.get('automatic_captions', {})

            if language not in subtitles and language not in automatic_captions:
                raise ValueError(f"Subtitle not available for language: {language}")

            # 下载字幕
            ydl.download([url])

            # 查找下载的字幕文件
            subtitle_files = [f for f in os.listdir(temp_dir) if f.endswith(f'.{subtitle_format}')]
            if subtitle_files:
                return os.path.join(temp_dir, subtitle_files[0])
            else:
                raise ValueError("Failed to download subtitle")

        except Exception as e:
            # 清理临时目录
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise e

def get_video_details(url: str, cookies: str = None) -> Dict[str, Any]:
    """
    Get comprehensive video information including thumbnails and subtitles.

    Args:
        url (str): The URL of the video
        cookies (str): Path to cookies file or browser name for cookies

    Returns:
        Dict[str, Any]: Complete video information
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'list_thumbnails': True,
        'listsubtitles': True,
    }

    # 添加cookie支持
    if cookies:
        if cookies.endswith('.txt'):
            ydl_opts['cookiefile'] = cookies
        else:
            ydl_opts['cookiesfrombrowser'] = (cookies,)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        sanitized = ydl.sanitize_info(info)

        # 处理缩略图
        thumbnails = sanitized.get('thumbnails', [])
        processed_thumbnails = []
        for thumb in thumbnails:
            processed_thumbnails.append({
                'url': thumb.get('url'),
                'width': thumb.get('width'),
                'height': thumb.get('height'),
                'resolution': f"{thumb.get('width', '?')}x{thumb.get('height', '?')}",
                'preference': thumb.get('preference', 0),
                'id': thumb.get('id')
            })

        # 按偏好排序
        processed_thumbnails.sort(key=lambda x: x.get('preference', 0), reverse=True)

        # 选择最佳缩略图
        best_thumbnail = processed_thumbnails[0] if processed_thumbnails else None

        return {
            'basic_info': {
                'title': sanitized.get('title'),
                'description': sanitized.get('description'),
                'duration': sanitized.get('duration'),
                'upload_date': sanitized.get('upload_date'),
                'uploader': sanitized.get('uploader'),
                'uploader_id': sanitized.get('uploader_id'),
                'view_count': sanitized.get('view_count'),
                'like_count': sanitized.get('like_count'),
                'channel_id': sanitized.get('channel_id'),
                'channel_url': sanitized.get('channel_url'),
            },
            'thumbnails': {
                'all': processed_thumbnails,
                'best': best_thumbnail,
                'count': len(processed_thumbnails)
            },
            'subtitles': {
                'manual': sanitized.get('subtitles', {}),
                'automatic': sanitized.get('automatic_captions', {}),
                'available_languages': list(sanitized.get('subtitles', {}).keys()),
                'automatic_languages': list(sanitized.get('automatic_captions', {}).keys())
            },
            'formats': {
                'count': len(sanitized.get('formats', [])),
                'best_format': sanitized.get('format'),
                'available_formats': list(set(f.get('ext') for f in sanitized.get('formats', []) if f.get('ext')))
            }
        }

app = FastAPI(title="yt-dlp API", description="API for downloading videos using yt-dlp")

class DownloadRequest(BaseModel):
    url: str
    output_path: str = "./downloads"
    format: str = "best[ext=mp4]"
    quiet: bool = False
    cookies: str = None

class SubtitleDownloadRequest(BaseModel):
    url: str
    output_path: str = "./downloads"
    languages: List[str] = ["en"]
    auto_select: bool = True
    subtitle_format: str = "srt"
    cookies: str = None

async def process_download_task(task_id: str, url: str, output_path: str, format: str, quiet: bool, cookies: str = None):
    """Asynchronously process download task"""
    try:
        print(f"Starting download task {task_id} for URL: {url}")
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(
                executor,
                lambda: download_video(
                    url=url,
                    output_path=output_path,
                    format=format,
                    quiet=quiet,
                    cookies=cookies,
                )
            )
        print(f"Download task {task_id} completed successfully")
        state.update_task(task_id, "completed", result=result)
    except Exception as e:
        print(f"Download task {task_id} failed with error: {str(e)}")
        state.update_task(task_id, "failed", error=str(e))

async def process_subtitle_task(task_id: str, url: str, output_path: str, languages: List[str],
                              auto_select: bool, subtitle_format: str, cookies: str = None):
    """异步处理字幕下载任务"""
    try:
        print(f"Starting subtitle download task {task_id} for URL: {url}")

        # 获取视频信息用于文件命名
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        if cookies:
            ydl_opts['cookiefile'] = cookies

        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            # 获取视频标题用于文件命名
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await loop.run_in_executor(executor, lambda: ydl.extract_info(url, download=False))
                video_title = info.get('title', 'video')

            downloaded_files = []

            # 下载每个语言的字幕
            for language in languages:
                try:
                    print(f"Downloading subtitle for language: {language}")
                    subtitle_path = await loop.run_in_executor(
                        executor,
                        lambda: download_subtitle(url, language, subtitle_format, cookies)
                    )

                    # 重命名字幕文件，添加视频标题
                    safe_filename = create_safe_filename(video_title, language, subtitle_format)
                    final_path = os.path.join(output_path, safe_filename)

                    # 确保输出目录存在
                    os.makedirs(output_path, exist_ok=True)

                    # 移动并重命名文件
                    shutil.move(subtitle_path, final_path)

                    file_info = {
                        'language': language,
                        'path': final_path,
                        'format': subtitle_format,
                        'size': os.path.getsize(final_path),
                        'is_auto_generated': False  # 默认为人工字幕
                    }
                    downloaded_files.append(file_info)
                    print(f"Subtitle downloaded successfully: {final_path}")

                except Exception as lang_error:
                    print(f"Failed to download subtitle for language {language}: {str(lang_error)}")
                    # 如果启用了自动选择，可以尝试其他可用语言
                    if auto_select:
                        try:
                            # 获取可用字幕
                            available_subtitles = await loop.run_in_executor(
                                executor,
                                lambda: get_video_subtitles(url, cookies)
                            )

                            # 尝试其他可用语言
                            for lang_code in available_subtitles.get('available_languages', []):
                                if lang_code != language:
                                    try:
                                        subtitle_path = await loop.run_in_executor(
                                            executor,
                                            lambda: download_subtitle(url, lang_code, subtitle_format, cookies)
                                        )

                                        safe_filename = create_safe_filename(video_title, lang_code, subtitle_format)
                                        final_path = os.path.join(output_path, safe_filename)

                                        os.makedirs(output_path, exist_ok=True)
                                        shutil.move(subtitle_path, final_path)

                                        file_info = {
                                            'language': lang_code,
                                            'path': final_path,
                                            'format': subtitle_format,
                                            'size': os.path.getsize(final_path),
                                            'is_auto_generated': lang_code in available_subtitles.get('automatic_captions', {})
                                        }
                                        downloaded_files.append(file_info)
                                        print(f"Auto-selected subtitle downloaded: {final_path}")
                                        break
                                    except:
                                        continue
                        except Exception as auto_error:
                            print(f"Auto-selection failed: {str(auto_error)}")
                            continue

        # 计算总文件数和大小
        total_files = len(downloaded_files)
        total_size = sum(f['size'] for f in downloaded_files) if downloaded_files else 0

        result = {
            'downloaded_files': downloaded_files,
            'total_files': total_files,
            'total_size': total_size,
            'video_title': video_title
        }

        print(f"Subtitle download task {task_id} completed successfully. Files: {total_files}")
        state.update_task(task_id, "completed", result=result)

    except Exception as e:
        print(f"Subtitle download task {task_id} failed with error: {str(e)}")
        state.update_task(task_id, "failed", error=str(e))

@app.post("/download", response_class=JSONResponse)
async def api_download_video(request: DownloadRequest):
    """
    Submit a video download task and return a task ID to track progress.
    """
    print(f"Received download request for URL: {request.url}")

    # 如果没有指定cookies，尝试自动获取
    if not request.cookies:
        print("No cookies specified, attempting to auto-detect...")
        auto_cookies = await state.get_cookies_for_download(request.url)
        if auto_cookies:
            request.cookies = auto_cookies
            print(f"Auto-detected cookies: {auto_cookies}")

    # 如果有相同的url和output_path的任务已经存在，检查任务状态
    existing_task = next((task for task in state.tasks.values() if task.format == request.format and task.url == request.url and task.output_path == request.output_path), None)
    if existing_task:
        print(f"Found existing task with ID: {existing_task.id}")
        # 如果任务失败了，创建新任务而不是返回旧的ID
        if existing_task.status == "failed":
            print(f"Existing task failed, creating new task")
            task_id = state.add_task(request.url, request.output_path, request.format)
            print(f"Created new task with ID: {task_id}")

            # Asynchronously execute download task
            print("Creating async task for download")
            asyncio.create_task(process_download_task(
                task_id=task_id,
                url=request.url,
                output_path=request.output_path,
                format=request.format,
                quiet=request.quiet,
                cookies=request.cookies
            ))
            print("Async task created")

            return {"status": "success", "task_id": task_id}
        else:
            # 对于非失败状态的任务，返回现有任务ID
            return {"status": "success", "task_id": existing_task.id}

    # 创建新任务
    task_id = state.add_task(request.url, request.output_path, request.format)
    print(f"Created new task with ID: {task_id}")

    # Asynchronously execute download task
    print("Creating async task for download")
    asyncio.create_task(process_download_task(
        task_id=task_id,
        url=request.url,
        output_path=request.output_path,
        format=request.format,
        quiet=request.quiet,
        cookies=request.cookies
    ))
    print("Async task created")

    return {"status": "success", "task_id": task_id}

@app.post("/download-subtitles", response_class=JSONResponse)
async def api_download_subtitles(request: SubtitleDownloadRequest):
    """
    Submit a subtitle download task and return a task ID to track progress.
    """
    print(f"Received subtitle download request for URL: {request.url}")

    # 验证语言代码
    supported_languages = ['en', 'zh', 'es', 'fr', 'de', 'ja', 'ko', 'ru', 'ar', 'hi', 'pt', 'it', 'nl', 'pl', 'sv', 'da', 'no', 'fi']
    for lang in request.languages:
        if lang not in supported_languages:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported language code: {lang}. Supported languages: {', '.join(supported_languages)}"
            )

    # 验证字幕格式
    supported_formats = ['srt', 'vtt', 'ass', 'ssa']
    if request.subtitle_format not in supported_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported subtitle format: {request.subtitle_format}. Supported formats: {', '.join(supported_formats)}"
        )

    # 如果没有指定cookies，尝试自动获取
    if not request.cookies:
        print("No cookies specified, attempting to auto-detect...")
        auto_cookies = await state.get_cookies_for_download(request.url)
        if auto_cookies:
            request.cookies = auto_cookies
            print(f"Auto-detected cookies: {auto_cookies}")

    # 检查是否存在相同的字幕任务
    existing_task = None
    for task in state.tasks.values():
        if (task.task_type == "subtitle" and
            task.url == request.url and
            task.output_path == request.output_path and
            task.subtitle_config and
            task.subtitle_config.get('languages') == request.languages and
            task.subtitle_config.get('subtitle_format') == request.subtitle_format):
            existing_task = task
            break

    if existing_task:
        print(f"Found existing subtitle task with ID: {existing_task.id}")
        # 如果任务失败了，创建新任务
        if existing_task.status == "failed":
            print(f"Existing subtitle task failed, creating new task")
            subtitle_config = {
                'languages': request.languages,
                'auto_select': request.auto_select,
                'subtitle_format': request.subtitle_format
            }
            task_id = state.add_task(
                request.url,
                request.output_path,
                ','.join(request.languages),  # 使用format字段存储语言列表
                task_type="subtitle",
                subtitle_config=subtitle_config
            )
            print(f"Created new subtitle task with ID: {task_id}")

            # 异步执行字幕下载任务
            print("Creating async task for subtitle download")
            asyncio.create_task(process_subtitle_task(
                task_id=task_id,
                url=request.url,
                output_path=request.output_path,
                languages=request.languages,
                auto_select=request.auto_select,
                subtitle_format=request.subtitle_format,
                cookies=request.cookies
            ))
            print("Async subtitle task created")

            return {"status": "success", "task_id": task_id}
        else:
            # 对于非失败状态的任务，返回现有任务ID
            return {"status": "success", "task_id": existing_task.id}

    # 创建新字幕任务
    subtitle_config = {
        'languages': request.languages,
        'auto_select': request.auto_select,
        'subtitle_format': request.subtitle_format
    }

    task_id = state.add_task(
        request.url,
        request.output_path,
        ','.join(request.languages),  # 使用format字段存储语言列表
        task_type="subtitle",
        subtitle_config=subtitle_config
    )
    print(f"Created new subtitle task with ID: {task_id}")

    # 异步执行字幕下载任务
    print("Creating async task for subtitle download")
    asyncio.create_task(process_subtitle_task(
        task_id=task_id,
        url=request.url,
        output_path=request.output_path,
        languages=request.languages,
        auto_select=request.auto_select,
        subtitle_format=request.subtitle_format,
        cookies=request.cookies
    ))
    print("Async subtitle task created")

    return {"status": "success", "task_id": task_id}

@app.get("/task/{task_id}", response_class=JSONResponse)
async def get_task_status(task_id: str):
    """
    Get the status of a specific download task.
    """
    task = state.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")
    
    response = {
        "status": "success",
        "data": {
            "id": task.id,
            "url": task.url,
            "status": task.status
        }
    }
    
    if task.status == "completed" and task.result:
        response["data"]["result"] = task.result
    elif task.status == "failed" and task.error:
        response["data"]["error"] = task.error
    
    return response

@app.get("/tasks", response_class=JSONResponse)
async def list_all_tasks():
    """
    List all download tasks and their status.
    """
    tasks = state.list_tasks()
    return {"status": "success", "data": tasks}

@app.get("/info", response_class=JSONResponse)
async def api_get_video_info(url: str = Query(..., description="The URL of the video"), cookies: str = Query(None, description="Path to cookies file or browser name")):
    """
    Get information about a video without downloading it.
    """
    try:
        result = get_video_info(url, cookies=cookies)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/formats", response_class=JSONResponse)
async def api_list_formats(url: str = Query(..., description="The URL of the video"), cookies: str = Query(None, description="Path to cookies file or browser name")):
    """
    List all available formats for a video.
    """
    try:
        # 如果没有指定cookies，尝试自动获取
        if not cookies:
            print("No cookies specified, attempting to auto-detect...")
            auto_cookies = await state.get_cookies_for_download(url)
            if auto_cookies:
                cookies = auto_cookies
                print(f"Auto-detected cookies: {auto_cookies}")

        result = list_available_formats(url, cookies=cookies)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download-formats", response_class=JSONResponse)
async def api_list_download_formats(url: str = Query(..., description="The URL of the video"), cookies: str = Query(None, description="Path to cookies file or browser name")):
    """
    List download-friendly formats with format IDs that can be used with the download API.
    This endpoint provides optimized format selections for downloading.
    """
    try:
        # 如果没有指定cookies，尝试自动获取
        if not cookies:
            print("No cookies specified, attempting to auto-detect...")
            auto_cookies = await state.get_cookies_for_download(url)
            if auto_cookies:
                cookies = auto_cookies
                print(f"Auto-detected cookies: {auto_cookies}")

        # 获取所有可用格式
        formats = list_available_formats(url, cookies=cookies)
        if not formats:
            return {"status": "success", "data": {"formats": [], "recommended": []}}

        # 处理格式信息，提取下载相关的关键信息
        download_formats = []
        recommended_formats = []
        
        for fmt in formats:
            # 提取关键信息
            format_info = {
                "format_id": fmt.get("format_id", ""),
                "ext": fmt.get("ext", ""),
                "resolution": fmt.get("resolution", ""),
                "fps": fmt.get("fps", 0),
                "filesize": fmt.get("filesize"),
                "filesize_approx": fmt.get("filesize_approx"),
                "tbr": fmt.get("tbr", 0),  # 总比特率
                "vbr": fmt.get("vbr", 0),  # 视频比特率
                "abr": fmt.get("abr", 0),  # 音频比特率
                "acodec": fmt.get("acodec", ""),
                "vcodec": fmt.get("vcodec", ""),
                "container": fmt.get("container", ""),
                "quality": fmt.get("quality", 0),
                "format_note": fmt.get("format_note", ""),
                "language": fmt.get("language", ""),
                "proto": fmt.get("proto", ""),
                # 添加是否包含视频和音频的标识
                "has_video": bool(fmt.get("vcodec") and fmt.get("vcodec") != "none"),
                "has_audio": bool(fmt.get("acodec") and fmt.get("acodec") != "none"),
                # 添加推荐的格式字符串
                "format_selector": fmt.get("format_id", "")
            }
            
            download_formats.append(format_info)
            
            # 识别推荐格式
            # 1. 最佳视频质量（包含视频和音频）
            if (format_info["has_video"] and format_info["has_audio"] and 
                format_info["ext"] in ["mp4", "webm", "mkv"] and
                format_info["resolution"] and format_info["resolution"] != "audio only"):
                recommended_formats.append({
                    **format_info,
                    "recommendation_type": "best_combined",
                    "description": f"最佳组合格式 - {format_info['resolution']} {format_info['ext'].upper()}"
                })
            
            # 2. 仅视频格式（用于合并）
            elif (format_info["has_video"] and not format_info["has_audio"] and
                  format_info["ext"] in ["mp4", "webm", "mkv"] and
                  format_info["resolution"] and format_info["resolution"] != "audio only"):
                recommended_formats.append({
                    **format_info,
                    "recommendation_type": "video_only",
                    "description": f"仅视频 - {format_info['resolution']} {format_info['ext'].upper()}"
                })
            
            # 3. 仅音频格式
            elif (not format_info["has_video"] and format_info["has_audio"] and
                  format_info["ext"] in ["mp3", "m4a", "webm", "opus", "aac"]):
                recommended_formats.append({
                    **format_info,
                    "recommendation_type": "audio_only", 
                    "description": f"仅音频 - {format_info['ext'].upper()} {format_info['abr']}k"
                })

        # 按质量排序推荐格式
        recommended_formats.sort(key=lambda x: (
            0 if x["recommendation_type"] == "best_combined" else
            1 if x["recommendation_type"] == "video_only" else 2,
            -x.get("tbr", 0)  # 按比特率降序
        ))

        # 添加常用的预设格式选择器
        preset_formats = [
            {
                "name": "best",
                "description": "最佳质量（自动选择）",
                "format_selector": "best",
                "recommended": True
            },
            {
                "name": "best_mp4", 
                "description": "最佳MP4格式",
                "format_selector": "best[ext=mp4]",
                "recommended": True
            },
            {
                "name": "best_video",
                "description": "最佳视频质量",
                "format_selector": "bestvideo",
                "recommended": False
            },
            {
                "name": "best_audio",
                "description": "最佳音频质量", 
                "format_selector": "bestaudio",
                "recommended": False
            },
            {
                "name": "worst",
                "description": "最低质量（最小文件）",
                "format_selector": "worst",
                "recommended": False
            },
            {
                "name": "mp4_1080p",
                "description": "1080p MP4",
                "format_selector": "best[height<=1080][ext=mp4]",
                "recommended": True
            },
            {
                "name": "mp4_720p",
                "description": "720p MP4", 
                "format_selector": "best[height<=720][ext=mp4]",
                "recommended": True
            },
            {
                "name": "mp4_480p",
                "description": "480p MP4",
                "format_selector": "best[height<=480][ext=mp4]", 
                "recommended": True
            },
            {
                "name": "audio_mp3",
                "description": "MP3音频",
                "format_selector": "bestaudio[ext=mp3]",
                "recommended": True
            },
            {
                "name": "audio_m4a",
                "description": "M4A音频",
                "format_selector": "bestaudio[ext=m4a]",
                "recommended": True
            }
        ]

        return {
            "status": "success", 
            "data": {
                "formats": download_formats,
                "recommended": recommended_formats[:10],  # 限制推荐格式数量
                "presets": preset_formats,
                "total_formats": len(download_formats),
                "video_info": {
                    "has_video": any(f["has_video"] for f in download_formats),
                    "has_audio": any(f["has_audio"] for f in download_formats),
                    "available_extensions": list(set(f["ext"] for f in download_formats if f["ext"])),
                    "max_resolution": next((f["resolution"] for f in download_formats 
                                           if f["resolution"] and f["resolution"] != "audio only" 
                                           and f["has_video"]), None),
                    "max_bitrate": max((f["tbr"] for f in download_formats), default=0)
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/thumbnails", response_class=JSONResponse)
async def api_get_thumbnails(url: str = Query(..., description="The URL of the video"), cookies: str = Query(None, description="Path to cookies file or browser name")):
    """
    Get video thumbnails in different resolutions.
    """
    try:
        result = get_video_thumbnails(url, cookies=cookies)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/subtitles", response_class=JSONResponse)
async def api_list_subtitles(url: str = Query(..., description="The URL of the video"), cookies: str = Query(None, description="Path to cookies file or browser name")):
    """
    List available subtitles for a video.
    """
    try:
        result = get_video_subtitles(url, cookies=cookies)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/subtitle", response_class=FileResponse)
async def api_download_subtitle(
    url: str = Query(..., description="The URL of the video"),
    language: str = Query(..., description="Language code (e.g., 'en', 'zh', 'ja')"),
    subtitle_format: str = Query("srt", description="Subtitle format (e.g., 'srt', 'vtt', 'ass')"),
    cookies: str = Query(None, description="Path to cookies file or browser name")
):
    """
    Download subtitle for a video.
    """
    try:
        subtitle_path = download_subtitle(url, language, subtitle_format, cookies)

        # 读取文件内容并返回
        import os
        filename = os.path.basename(subtitle_path)

        return FileResponse(
            path=subtitle_path,
            filename=filename,
            media_type=f"text/{subtitle_format}"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/video-details", response_class=JSONResponse)
async def api_get_video_details(url: str = Query(..., description="The URL of the video"), cookies: str = Query(None, description="Path to cookies file or browser name")):
    """
    Get comprehensive video information including thumbnails and subtitles.
    """
    try:
        result = get_video_details(url, cookies=cookies)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-cookies")
async def upload_cookies(file: UploadFile = File(...)):
    """
    上传 cookies 文件到服务器
    """
    try:
        # 确保 cookies 目录存在
        cookies_dir = "cookies"
        os.makedirs(cookies_dir, exist_ok=True)
        
        # 验证文件类型
        if not file.filename.endswith('.txt'):
            raise HTTPException(status_code=400, detail="Only .txt files are allowed for cookies")
        
        # 保存文件
        file_path = os.path.join(cookies_dir, "cookies.txt")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 设置文件权限为仅当前用户可读写
        os.chmod(file_path, 0o600)
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Cookies 文件上传成功",
                "path": file_path,
                "filename": file.filename,
                "size": os.path.getsize(file_path)
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

@app.get("/cookies-status")
async def get_cookies_status():
    """
    检查 cookies 文件状态
    """
    cookies_path = "cookies/cookies.txt"
    if os.path.exists(cookies_path):
        file_stat = os.stat(cookies_path)
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "exists": True,
                "path": cookies_path,
                "size": file_stat.st_size,
                "modified": datetime.datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                "permissions": oct(file_stat.st_mode)[-3:]
            }
        )
    else:
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "exists": False,
                "message": "Cookies 文件不存在"
            }
        )

@app.delete("/cookies")
async def delete_cookies():
    """
    删除 cookies 文件
    """
    cookies_path = "cookies/cookies.txt"
    try:
        if os.path.exists(cookies_path):
            os.remove(cookies_path)
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "Cookies 文件删除成功"
                }
            )
        else:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": "Cookies 文件不存在"
                }
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@app.get("/download/{task_id}/file", response_class=FileResponse)
async def download_completed_video(task_id: str):
    """
    返回已完成下载任务的视频文件。
    如果任务未完成或未找到，将返回相应的错误。
    """
    task = state.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")
    
    if task.status != "completed":
        raise HTTPException(status_code=400, detail=f"Task is not completed yet. Current status: {task.status}")
    
    if not task.result:
        raise HTTPException(status_code=500, detail="Task completed but no result information available")
    
    # 获取文件路径
    try:
        # 从结果中提取文件名和路径
        filename = None
        
        # 首先尝试从requested_downloads获取文件名
        requested_downloads = task.result.get("requested_downloads", [])
        if requested_downloads and len(requested_downloads) > 0:
            filename = requested_downloads[0].get("filepath") or requested_downloads[0].get("filename")
        
        # 如果没有找到，尝试从requested_filename获取
        if not filename:
            requested_filename = task.result.get("requested_filename")
            if requested_filename:
                filename = requested_filename
        
        # 如果仍然没有找到，尝试构建文件路径
        if not filename:
            title = task.result.get("title", "video")
            ext = task.result.get("ext", "mp4")
            # 使用安全的文件名生成函数
            safe_filename = create_safe_filename(title, task.format, ext)
            filename = os.path.join(task.output_path, safe_filename)
        
        # 检查文件是否存在
        if not filename or not os.path.exists(filename):
            # 如果文件不存在，尝试在output_path目录中查找匹配的文件
            if os.path.exists(task.output_path):
                # 获取output_path目录中的所有文件
                files = os.listdir(task.output_path)
                # 尝试匹配标题的文件
                title = task.result.get("title", "video")
                # 移除特殊字符并转换为小写进行匹配
                normalized_title = NormalizeString(title).lower()
                for file in files:
                    # 检查文件名是否包含标题
                    if normalized_title in file.lower():
                        filename = os.path.join(task.output_path, file)
                        break
            
            # 如果仍然找不到文件，抛出错误
            if not filename or not os.path.exists(filename):
                raise HTTPException(status_code=404, detail="Video file not found on server")
        
        # 提取实际文件名用于Content-Disposition头
        file_basename = os.path.basename(filename)
        
        # 返回文件
        return FileResponse(
            path=filename,
            filename=file_basename,
            media_type="application/octet-stream"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error accessing video file: {str(e)}")


@app.delete("/task/{task_id}", response_class=JSONResponse)
async def delete_task(task_id: str):
    """
    删除指定的任务及其对应的文件（如果存在）
    """
    # 获取任务信息
    task = state.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")
    
    # 如果任务已完成，尝试删除对应的文件
    file_deleted = False
    if task.status == "completed" and task.result:
        file_deleted = delete_task_file(task)
    
    # 从数据库和内存中删除任务
    deleted = state.delete_task(task_id)
    
    if deleted:
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"Task {task_id} deleted successfully",
                "file_deleted": file_deleted
            }
        )
    else:
        raise HTTPException(status_code=500, detail="Failed to delete task")


@app.delete("/tasks", response_class=JSONResponse)
async def delete_all_tasks():
    """
    删除所有任务及其对应的文件（如果存在）
    """
    deleted_tasks = []
    failed_tasks = []
    
    # 获取所有任务的副本，避免在迭代时修改字典
    tasks_copy = list(state.tasks.values())
    
    for task in tasks_copy:
        # 如果任务已完成，尝试删除对应的文件
        file_deleted = False
        if task.status == "completed" and task.result:
            file_deleted = delete_task_file(task)
        
        # 从数据库和内存中删除任务
        deleted = state.delete_task(task.id)
        
        if deleted:
            deleted_tasks.append({
                "task_id": task.id,
                "file_deleted": file_deleted
            })
        else:
            failed_tasks.append(task.id)
    
    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "message": f"Deleted {len(deleted_tasks)} tasks, failed to delete {len(failed_tasks)} tasks",
            "deleted_tasks": deleted_tasks,
            "failed_tasks": failed_tasks
        }
    )


# Cookie管理API端点
@app.post("/cookies/auto-setup", response_class=JSONResponse)
async def auto_setup_cookies_endpoint():
    """
    自动设置cookies - 扫描浏览器并自动配置
    """
    try:
        result = await state.initialize_cookies()
        return JSONResponse(
            status_code=200,
            content=result
        )
    except Exception as e:
        logger.error(f"Auto setup cookies failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cookies/status", response_class=JSONResponse)
async def get_cookie_status_endpoint():
    """
    获取当前cookie状态
    """
    try:
        status = await get_cookie_status()
        return JSONResponse(
            status_code=200,
            content=status
        )
    except Exception as e:
        logger.error(f"Get cookie status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cookies/refresh", response_class=JSONResponse)
async def refresh_cookies_endpoint():
    """
    刷新cookies - 重新扫描浏览器获取最新cookies
    """
    try:
        result = await refresh_cookies()
        return JSONResponse(
            status_code=200,
            content=result
        )
    except Exception as e:
        logger.error(f"Refresh cookies failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cookies/diagnose", response_class=JSONResponse)
async def diagnose_environment_endpoint():
    """
    诊断环境问题 - 检查系统、浏览器、权限等
    """
    try:
        diagnosis = await auto_cookie_manager.diagnose_environment()
        return JSONResponse(
            status_code=200,
            content=diagnosis
        )
    except Exception as e:
        logger.error(f"Diagnose environment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cookies/list", response_class=JSONResponse)
async def list_cookies_endpoint():
    """
    列出所有可用的cookie文件
    """
    try:
        import os
        from pathlib import Path

        cookie_dir = Path("cookies")
        if not cookie_dir.exists():
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "cookies": [],
                    "message": "Cookie目录不存在"
                }
            )

        cookies = []
        for cookie_file in cookie_dir.glob("*.txt"):
            try:
                stat = cookie_file.stat()
                cookies.append({
                    "filename": cookie_file.name,
                    "path": str(cookie_file),
                    "size": stat.st_size,
                    "created": datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            except Exception as e:
                logger.warning(f"Failed to read cookie file {cookie_file}: {e}")

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "cookies": sorted(cookies, key=lambda x: x['modified'], reverse=True)
            }
        )
    except Exception as e:
        logger.error(f"List cookies failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cookies/validate/{filename}", response_class=JSONResponse)
async def validate_cookie_file_endpoint(filename: str):
    """
    验证指定的cookie文件
    """
    try:
        cookie_file = os.path.join("cookies", filename)
        if not os.path.exists(cookie_file):
            raise HTTPException(status_code=404, detail="Cookie文件不存在")

        result = await auto_cookie_manager.validate_cookie_file(cookie_file)
        return JSONResponse(
            status_code=200,
            content=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Validate cookie file failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/cookies/cleanup", response_class=JSONResponse)
async def cleanup_cookies_endpoint():
    """
    清理过期的cookies文件
    """
    try:
        result = await auto_cookie_manager.cookie_manager.cleanup_expired_cookies()
        return JSONResponse(
            status_code=200,
            content=result
        )
    except Exception as e:
        logger.error(f"Cleanup cookies failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cookies/supported-browsers", response_class=JSONResponse)
async def get_supported_browsers_endpoint():
    """
    获取支持的浏览器列表
    """
    try:
        browsers = auto_cookie_manager.get_supported_browsers()
        detected = detect_browsers()

        browser_info = []
        for browser in browsers:
            browser_info.append({
                "name": browser,
                "supported": True,
                "detected": detected.get(browser, False)
            })

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "browsers": browser_info
            }
        )
    except Exception as e:
        logger.error(f"Get supported browsers failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ytdlp/version", response_class=JSONResponse)
async def get_ytdlp_version():
    """
    获取当前yt-dlp版本信息
    """
    try:
        version = yt_dlp.version.__version__
        release = yt_dlp.version.RELEASE_GIT_HEAD if hasattr(yt_dlp.version, 'RELEASE_GIT_HEAD') else None

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "version": version,
                "release": release,
                "package": "yt-dlp"
            }
        )
    except Exception as e:
        logger.error(f"Get yt-dlp version failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ytdlp/update", response_class=JSONResponse)
async def update_ytdlp():
    """
    更新yt-dlp到最新版本
    """
    try:
        import subprocess
        import sys

        logger.info("开始更新yt-dlp...")

        # 使用pip更新yt-dlp
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )

        if result.returncode == 0:
            # 获取新版本信息
            new_version = yt_dlp.version.__version__

            # 记录更新结果
            logger.info(f"yt-dlp更新成功: {result.stdout}")

            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "yt-dlp更新成功",
                    "new_version": new_version,
                    "output": result.stdout
                }
            )
        else:
            logger.error(f"yt-dlp更新失败: {result.stderr}")
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "yt-dlp更新失败",
                    "error": result.stderr,
                    "output": result.stdout
                }
            )

    except subprocess.TimeoutExpired:
        logger.error("yt-dlp更新超时")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "更新超时，请稍后重试"
            }
        )
    except Exception as e:
        logger.error(f"Update yt-dlp failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ytdlp/check-update", response_class=JSONResponse)
async def check_ytdlp_update():
    """
    检查yt-dlp是否有可用更新
    """
    try:
        import subprocess
        import sys

        # 检查可用更新
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--outdated"],
            capture_output=True,
            text=True,
            timeout=60
        )

        current_version = yt_dlp.version.__version__
        has_update = False
        latest_version = None

        # 解析pip输出查找yt-dlp
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'yt-dlp' in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        latest_version = parts[2]
                        if latest_version != current_version:
                            has_update = True
                        break

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "current_version": current_version,
                "latest_version": latest_version,
                "has_update": has_update,
                "update_available": has_update
            }
        )

    except subprocess.TimeoutExpired:
        logger.error("检查yt-dlp更新超时")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "检查更新超时"
            }
        )
    except Exception as e:
        logger.error(f"Check yt-dlp update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ========== 调度器管理 API ==========

@app.get("/scheduler/status", response_model=SchedulerStatusResponse, response_class=JSONResponse)
async def get_scheduler_status():
    """
    获取调度器状态
    """
    try:
        status = scheduler_manager.get_scheduler_status()
        return JSONResponse(
            status_code=200,
            content=status
        )
    except Exception as e:
        logger.error(f"Get scheduler status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/scheduler/start", response_class=JSONResponse)
async def start_scheduler():
    """
    启动调度器
    """
    try:
        success = await scheduler_manager.start_scheduler()
        if success:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "调度器启动成功"
                }
            )
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "调度器已在运行或启动失败"
                }
            )
    except Exception as e:
        logger.error(f"Start scheduler failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/scheduler/stop", response_class=JSONResponse)
async def stop_scheduler():
    """
    停止调度器
    """
    try:
        success = await scheduler_manager.stop_scheduler()
        if success:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "调度器停止成功"
                }
            )
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "调度器未运行或停止失败"
                }
            )
    except Exception as e:
        logger.error(f"Stop scheduler failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/scheduler/config", response_class=JSONResponse)
async def get_scheduler_config():
    """
    获取调度器配置
    """
    try:
        config = scheduler_manager.get_config()
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "config": {
                    "enabled": config.enabled,
                    "cron_expression": config.cron_expression,
                    "timezone": config.timezone,
                    "max_retries": config.max_retries,
                    "retry_delay": config.retry_delay
                }
            }
        )
    except Exception as e:
        logger.error(f"Get scheduler config failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/scheduler/config", response_class=JSONResponse)
async def update_scheduler_config(request: SchedulerConfigRequest):
    """
    更新调度器配置
    """
    try:
        current_config = scheduler_manager.get_config()

        # 更新配置（只更新提供的字段）
        if request.enabled is not None:
            current_config.enabled = request.enabled
        if request.cron_expression is not None:
            current_config.cron_expression = request.cron_expression
        if request.timezone is not None:
            current_config.timezone = request.timezone
        if request.max_retries is not None:
            current_config.max_retries = request.max_retries
        if request.retry_delay is not None:
            current_config.retry_delay = request.retry_delay

        # 保存配置
        success = scheduler_manager.update_config(current_config)
        if not success:
            raise HTTPException(status_code=500, detail="保存配置失败")

        # 如果更新了 cron 表达式且调度器正在运行，重新调度作业
        if request.cron_expression is not None:
            await scheduler_manager.update_job_schedule(current_config.cron_expression)

        # 根据是否启用自动更新来启动或停止调度器
        if request.enabled is not None:
            if request.enabled:
                await scheduler_manager.start_scheduler()
            else:
                await scheduler_manager.stop_scheduler()

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "配置更新成功",
                "config": {
                    "enabled": current_config.enabled,
                    "cron_expression": current_config.cron_expression,
                    "timezone": current_config.timezone,
                    "max_retries": current_config.max_retries,
                    "retry_delay": current_config.retry_delay
                }
            }
        )
    except Exception as e:
        logger.error(f"Update scheduler config failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/scheduler/update-history", response_class=JSONResponse)
async def get_update_history(limit: int = Query(50, ge=1, le=200)):
    """
    获取更新历史
    """
    try:
        history = scheduler_manager.get_update_history(limit)
        history_data = []
        for record in history:
            history_data.append({
                "id": record.id,
                "timestamp": record.timestamp.isoformat() if record.timestamp else None,
                "old_version": record.old_version,
                "new_version": record.new_version,
                "status": record.status,
                "error_message": record.error_message,
                "retry_count": record.retry_count
            })

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "history": history_data,
                "total": len(history_data)
            }
        )
    except Exception as e:
        logger.error(f"Get update history failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Browser Session Management APIs ====================

@app.post("/browser/session/start", response_class=JSONResponse)
async def start_browser_session():
    """
    启动新的浏览器会话用于YouTube登录
    """
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, browser_session_manager.create_session
        )
        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        logger.error(f"Start browser session failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/browser/session/{session_id}/status", response_class=JSONResponse)
async def get_session_status(session_id: str):
    """
    获取浏览器会话状态
    """
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, browser_session_manager.get_session_status, session_id
        )
        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        logger.error(f"Get session status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/browser/session/{session_id}/extract-cookies", response_class=JSONResponse)
async def extract_session_cookies(session_id: str):
    """
    提取浏览器会话中的YouTube cookies
    """
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None, browser_session_manager.extract_cookies, session_id
        )
        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        logger.error(f"Extract cookies failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/browser/session/{session_id}", response_class=JSONResponse)
async def cleanup_browser_session(session_id: str):
    """
    清理浏览器会话资源
    """
    try:
        success = await asyncio.get_event_loop().run_in_executor(
            None, browser_session_manager.cleanup_session, session_id
        )
        return JSONResponse(
            status_code=200,
            content={
                "success": success,
                "message": "会话清理成功" if success else "会话不存在或清理失败"
            }
        )
    except Exception as e:
        logger.error(f"Cleanup session failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/browser/sessions", response_class=JSONResponse)
async def get_all_sessions():
    """
    获取所有活跃的浏览器会话
    """
    try:
        sessions = await asyncio.get_event_loop().run_in_executor(
            None, browser_session_manager.get_all_sessions
        )
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "sessions": sessions,
                "total": len(sessions)
            }
        )
    except Exception as e:
        logger.error(f"Get all sessions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cookies/browser-preference", response_class=JSONResponse)
async def get_browser_cookies_preference():
    """
    获取浏览器登录cookies的偏好设置和状态
    """
    try:
        preference = await asyncio.get_event_loop().run_in_executor(
            None, auto_cookie_manager.add_browser_cookies_preference
        )
        return JSONResponse(status_code=200, content={
            "success": True,
            "browser_preference": preference
        })
    except Exception as e:
        logger.error(f"Get browser cookies preference failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def start_api():
    logger.info("Starting FastAPI server on 0.0.0.0:8000")
    logger.info("API documentation will be available at http://0.0.0.0:8000/docs")
    logger.info("API routes:")
    for route in app.routes:
        if hasattr(route, "methods"):
            logger.info(f"  {list(route.methods)[0]} {route.path}")

    # 初始化调度器
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # 设置调度器
        loop.run_until_complete(scheduler_manager.setup_scheduler())
        logger.info("调度器初始化完成")

        # 如果启用自动更新，启动调度器
        config = scheduler_manager.get_config()
        if config.enabled:
            loop.run_until_complete(scheduler_manager.start_scheduler())
            logger.info("自动更新调度器已启动")
        else:
            logger.info("自动更新已禁用")

    except Exception as e:
        logger.error(f"初始化调度器失败: {e}")

    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    print("Starting yt-dlp API server...")
    logger.info("=" * 50)
    logger.info("yt-dlp API server starting...")
    logger.info("Server configuration:")
    logger.info("  Host: 0.0.0.0")
    logger.info("  Port: 8000")
    logger.info("  PID: %s", os.getpid())
    logger.info("=" * 50)
    
    # 注册信号处理器以便优雅关闭
    import signal
    import sys
    
    def signal_handler(sig, frame):
        logger.info("Received signal %s, shutting down gracefully...", sig)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        start_api()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error("Server error: %s", str(e))
        sys.exit(1)
