import yt_dlp
import os
import uuid
import shutil
import traceback
import time

import asyncio

import json
import datetime
import sqlite3
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
import uvicorn
from pydantic import BaseModel, Field
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

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

class ErrorType(str, Enum):
    NETWORK_ERROR = "network_error"
    AUTHENTICATION_ERROR = "authentication_error"
    FORMAT_ERROR = "format_error"
    FILESYSTEM_ERROR = "filesystem_error"
    YOUTUBE_RESTRICTION = "youtube_restriction"
    COOKIE_EXPIRED = "cookie_expired"
    UNKNOWN_ERROR = "unknown_error"

class TaskProgress(BaseModel):
    downloaded_bytes: int = 0
    total_bytes: Optional[int] = None
    speed: Optional[float] = None
    eta: Optional[int] = None
    percentage: float = 0.0
    status: str = "idle"
    filename: Optional[str] = None
    elapsed_time: float = 0.0
    speed_str: Optional[str] = None
    eta_str: Optional[str] = None
    downloaded_str: Optional[str] = None
    total_str: Optional[str] = None

class TaskError(BaseModel):
    type: ErrorType
    message: str
    timestamp: datetime.datetime
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = {}
    retry_possible: bool = True
    suggestions: List[str] = []

class Task(BaseModel):
    id: str
    url: str
    output_path: str
    format: str
    status: str
    progress: Optional[TaskProgress] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[TaskError] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

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
    
    def _init_db(self) -> None:
        """初始化SQLite数据库"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # 检查表是否存在，如果存在则删除重建（为了支持新的字段结构）
        cursor.execute("DROP TABLE IF EXISTS tasks")
        
        # 创建任务表
        cursor.execute('''
        CREATE TABLE tasks (
            id TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            output_path TEXT NOT NULL,
            format TEXT NOT NULL,
            status TEXT NOT NULL,
            progress_json TEXT,
            result TEXT,
            error_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_tasks(self) -> None:
        """从数据库加载任务状态"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, url, output_path, format, status, progress_json, result, error_json, created_at, updated_at FROM tasks")
            rows = cursor.fetchall()
            
            for row in rows:
                task_id, url, output_path, format, status, progress_json, result_json, error_json, created_at, updated_at = row
                
                # 解析JSON数据
                result = json.loads(result_json) if result_json else None
                progress = TaskProgress(**json.loads(progress_json)) if progress_json else None
                error = TaskError(**json.loads(error_json)) if error_json else None
                
                # 创建Task对象并存储在内存中
                task = Task(
                    id=task_id,
                    url=url,
                    output_path=output_path,
                    format=format,
                    status=status,
                    progress=progress,
                    result=result,
                    error=error,
                    created_at=datetime.datetime.fromisoformat(created_at),
                    updated_at=datetime.datetime.fromisoformat(updated_at)
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
            
            now = datetime.datetime.now()
            task.updated_at = now
            
            # 序列化数据
            result_json = json.dumps(task.result) if task.result else None
            progress_json = json.dumps(task.progress.dict()) if task.progress else None
            error_json = json.dumps(task.error.dict()) if task.error else None
            
            # 使用REPLACE策略插入/更新任务
            cursor.execute('''
            INSERT OR REPLACE INTO tasks (id, url, output_path, format, status, progress_json, result, error_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task.id,
                task.url,
                task.output_path,
                task.format,
                task.status,
                progress_json,
                result_json,
                error_json,
                task.created_at.isoformat(),
                task.updated_at.isoformat()
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error saving task to database: {e}")
    
    def add_task(self, url: str, output_path: str, format: str) -> str:
        task_id = str(uuid.uuid4())
        now = datetime.datetime.now()
        task = Task(
            id=task_id,
            url=url,
            output_path=output_path,
            format=format,
            status="pending",
            progress=TaskProgress(),
            created_at=now,
            updated_at=now
        )
        self.tasks[task_id] = task
        
        # 将任务保存到数据库
        self._save_task(task)
        
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)
    
    def update_task_progress(self, task_id: str, progress: TaskProgress) -> None:
        """更新任务进度"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.progress = progress
            task.updated_at = datetime.datetime.now()
            self._save_task(task)
    
    def update_task_error(self, task_id: str, error: TaskError) -> None:
        """更新任务错误信息"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.error = error
            task.updated_at = datetime.datetime.now()
            self._save_task(task)
    
    def update_task(self, task_id: str, status: str, result: Optional[Dict[str, Any]] = None, error: Optional[TaskError] = None) -> None:
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = status
            task.updated_at = datetime.datetime.now()
            if result:
                task.result = result
            if error:
                task.error = error
            
            # 将更新后的任务状态保存到数据库
            self._save_task(task)
    
    def list_tasks(self) -> List[Task]:
        return list(self.tasks.values())

def classify_error(exception: Exception, context: Dict[str, Any]) -> TaskError:
    """分类和处理错误"""
    error_type = ErrorType.UNKNOWN_ERROR
    suggestions = []
    
    # 网络相关错误
    if isinstance(exception, (ConnectionError, TimeoutError)):
        error_type = ErrorType.NETWORK_ERROR
        suggestions = [
            "检查网络连接",
            "尝试使用代理",
            "稍后重试"
        ]
    
    # YouTube认证错误
    elif "Sign in to confirm you're not a bot" in str(exception):
        error_type = ErrorType.AUTHENTICATION_ERROR
        suggestions = [
            "更新cookies文件",
            "使用不同的浏览器cookies",
            "尝试使用VPN"
        ]
    
    # Cookie过期错误
    elif "cookies" in str(exception).lower() and ("expired" in str(exception).lower() or "invalid" in str(exception).lower()):
        error_type = ErrorType.COOKIE_EXPIRED
        suggestions = [
            "重新导出cookies文件",
            "检查cookies文件格式",
            "确认YouTube登录状态"
        ]
    
    # 格式相关错误
    elif "requested format not available" in str(exception).lower() or "format" in str(exception).lower():
        error_type = ErrorType.FORMAT_ERROR
        suggestions = [
            "检查可用格式列表",
            "尝试其他格式",
            "使用 'best' 格式"
        ]
    
    # YouTube限制错误
    elif "unavailable" in str(exception).lower() or "private" in str(exception).lower() or "restricted" in str(exception).lower():
        error_type = ErrorType.YOUTUBE_RESTRICTION
        suggestions = [
            "检查视频是否可用",
            "确认视频访问权限",
            "尝试使用cookies认证"
        ]
    
    # 文件系统错误
    elif isinstance(exception, (OSError, IOError)):
        error_type = ErrorType.FILESYSTEM_ERROR
        suggestions = [
            "检查磁盘空间",
            "检查文件权限",
            "更换输出目录"
        ]
    
    return TaskError(
        type=error_type,
        message=str(exception),
        timestamp=datetime.datetime.now(),
        stack_trace=traceback.format_exc(),
        context=context,
        retry_possible=error_type in [ErrorType.NETWORK_ERROR, ErrorType.UNKNOWN_ERROR],
        suggestions=suggestions
    )

def download_video_with_progress(url: str, output_path: str = "./downloads", format: str = "best", quiet: bool = False, cookies: str = None, task_id: str = None) -> Dict[str, Any]:
    """
    Download a video from the specified URL using yt-dlp with progress tracking.
    
    Args:
        url (str): The URL of the video to download
        output_path (str): Directory where the video will be saved
        format (str): Video format to download (e.g., "best", "bestvideo+bestaudio", "mp4")
        quiet (bool): If True, suppress output
        cookies (str): Path to cookies file or browser name for cookies
        task_id (str): Task ID for progress tracking
        
    Returns:
        Dict[str, Any]: Information about the downloaded video
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_path, exist_ok=True)
    
    # Configure yt-dlp options
    def get_safe_outtmpl(info_dict):
        """为每个视频生成安全的输出文件名"""
        title = info_dict.get('title', 'video')
        ext = info_dict.get('ext', 'mp4')
        safe_filename = create_safe_filename(title, format, ext)
        return os.path.join(output_path, safe_filename)
    
    # 创建进度钩子
    def progress_hook(d):
        if task_id:
            progress = TaskProgress()
            
            if d['status'] == 'downloading':
                progress.status = "downloading"
                progress.downloaded_bytes = d.get('downloaded_bytes', 0)
                progress.total_bytes = d.get('total_bytes')
                progress.speed = d.get('speed')
                progress.eta = d.get('eta')
                progress.percentage = float(d.get('_percent_str', '0%').replace('%', '0'))
                progress.filename = d.get('filename')
                progress.elapsed_time = d.get('elapsed', 0)
                progress.speed_str = d.get('_speed_str')
                progress.eta_str = d.get('_eta_str')
                progress.downloaded_str = d.get('_downloaded_bytes_str')
                progress.total_str = d.get('_total_bytes_str')
                
            elif d['status'] == 'finished':
                progress.status = "processing"
                progress.downloaded_bytes = d.get('total_bytes', 0)
                progress.total_bytes = d.get('total_bytes')
                progress.percentage = 100.0
                progress.filename = d.get('filename')
                
            elif d['status'] == 'error':
                progress.status = "error"
                progress.filename = d.get('filename')
                
            # 更新任务进度
            state.update_task_progress(task_id, progress)
    
    ydl_opts = {
        'outtmpl': os.path.join(output_path, '%(title).180s.%(ext)s'),
        'quiet': quiet,
        'no_warnings': quiet,
        'format': format,
        'no_abort_on_error': True,
        'progress_hooks': [progress_hook],
    }
    
    # 添加cookie支持
    if cookies:
        if cookies.endswith('.txt'):
            # 如果是cookies文件路径
            ydl_opts['cookiefile'] = cookies
        else:
            # 如果是浏览器名称
            ydl_opts['cookiesfrombrowser'] = (cookies,)
    
    # 如果需要更安全的处理，我们可以在下载前先获取信息
    temp_ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }
    
    try:
        # 先获取视频信息来生成安全的文件名
        with yt_dlp.YoutubeDL(temp_ydl_opts) as temp_ydl:
            info = temp_ydl.extract_info(url, download=False)
            if info:
                title = info.get('title', 'video')
                ext = info.get('ext', 'mp4')
                safe_filename = create_safe_filename(title, format, ext)
                ydl_opts['outtmpl'] = os.path.join(output_path, safe_filename)
    except Exception:
        # 如果获取信息失败，使用默认的安全模板
        pass
    
    # Download the video
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.sanitize_info(info)

# 创建全局状态对象
state = State()

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
    # Create output directory if it doesn't exist
    os.makedirs(output_path, exist_ok=True)
    
    # Configure yt-dlp options
    # 使用自定义函数生成安全的文件名模板
    def get_safe_outtmpl(info_dict):
        """为每个视频生成安全的输出文件名"""
        title = info_dict.get('title', 'video')
        ext = info_dict.get('ext', 'mp4')
        safe_filename = create_safe_filename(title, format, ext)
        return os.path.join(output_path, safe_filename)
    
    ydl_opts = {
        'outtmpl': os.path.join(output_path, '%(title).180s.%(ext)s'),
        'quiet': quiet,
        'no_warnings': quiet,
        'format': format,
        'no_abort_on_error': True,
        # 添加进度钩子来处理文件名
        'progress_hooks': [],
    }
    
    # 添加cookie支持
    if cookies:
        if cookies.endswith('.txt'):
            # 如果是cookies文件路径
            ydl_opts['cookiefile'] = cookies
        else:
            # 如果是浏览器名称
            ydl_opts['cookiesfrombrowser'] = (cookies,)
    
    # 如果需要更安全的处理，我们可以在下载前先获取信息
    temp_ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }
    
    try:
        # 先获取视频信息来生成安全的文件名
        with yt_dlp.YoutubeDL(temp_ydl_opts) as temp_ydl:
            info = temp_ydl.extract_info(url, download=False)
            if info:
                title = info.get('title', 'video')
                ext = info.get('ext', 'mp4')
                safe_filename = create_safe_filename(title, format, ext)
                ydl_opts['outtmpl'] = os.path.join(output_path, safe_filename)
    except Exception:
        # 如果获取信息失败，使用默认的安全模板
        pass
    
    # Download the video
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.sanitize_info(info)

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

def json_cookies_to_netscape(json_cookies: List[CookieItem]) -> str:
    """
    Convert JSON format cookies to Netscape format.
    
    Args:
        json_cookies (List[CookieItem]): List of cookie items in JSON format
        
    Returns:
        str: Netscape format cookies string
    """
    netscape_lines = []
    netscape_lines.append("# Netscape HTTP Cookie File")
    netscape_lines.append("# This file is generated by yt-dlp API. Do not edit.")
    netscape_lines.append("")
    
    for cookie in json_cookies:
        # Netscape format: domain\tflag\tpath\tsecure\texpiration\tname\tvalue
        domain = cookie.domain
        flag = "TRUE" if cookie.hostOnly else "FALSE"
        path = cookie.path
        secure = "TRUE" if cookie.secure else "FALSE"
        
        # Handle expiration date
        if cookie.expirationDate:
            expiration = str(int(cookie.expirationDate))
        elif cookie.session:
            expiration = "0"  # Session cookie
        else:
            expiration = "0"  # Default to session
        
        name = cookie.name
        value = cookie.value
        
        line = f"{domain}\t{flag}\t{path}\t{secure}\t{expiration}\t{name}\t{value}"
        netscape_lines.append(line)
    
    return "\n".join(netscape_lines)

def save_json_cookies_to_file(json_cookies: List[CookieItem], file_path: str = "cookies/cookies.txt") -> str:
    """
    Save JSON format cookies to a Netscape format file.
    
    Args:
        json_cookies (List[CookieItem]): List of cookie items in JSON format
        file_path (str): Path to save the cookies file
        
    Returns:
        str: Path to the saved cookies file
    """
    # Ensure cookies directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Convert JSON cookies to Netscape format
    netscape_content = json_cookies_to_netscape(json_cookies)
    
    # Save to file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(netscape_content)
    
    # Set file permissions to read/write for owner only
    os.chmod(file_path, 0o600)
    
    return file_path

def cleanup_temp_cookies(task_id: str = None):
    """
    Clean up temporary cookie files.
    
    Args:
        task_id (str): Specific task ID to clean up, if None cleans all temp files
    """
    try:
        cookies_dir = "cookies"
        if not os.path.exists(cookies_dir):
            return
        
        if task_id:
            # Clean up specific temp file
            temp_file = f"cookies/temp_{task_id}.txt"
            if os.path.exists(temp_file):
                os.remove(temp_file)
        else:
            # Clean up all temp files
            for filename in os.listdir(cookies_dir):
                if filename.startswith("temp_") and filename.endswith(".txt"):
                    temp_file = os.path.join(cookies_dir, filename)
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
    except Exception as e:
        print(f"Error cleaning up temp cookies: {e}")

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

app = FastAPI(title="yt-dlp API", description="API for downloading videos using yt-dlp")

class CookieItem(BaseModel):
    domain: str
    expirationDate: Optional[float] = None
    hostOnly: bool
    httpOnly: bool
    name: str
    path: str
    sameSite: Optional[str] = None
    secure: bool
    session: bool
    storeId: Optional[str] = None
    value: str

class SetCookiesRequest(BaseModel):
    cookies: List[CookieItem]

class DownloadRequest(BaseModel):
    url: str
    output_path: str = "./downloads"
    format: str = "bestvideo+bestaudio/best"
    quiet: bool = False
    cookies: Optional[str] = None
    json_cookies: Optional[List[CookieItem]] = Field(None, description="JSON format cookies for this download task")

async def process_download_task(task_id: str, url: str, output_path: str, format: str, quiet: bool, cookies: str = None):
    """Asynchronously process download task"""
    try:
        # 更新任务状态为下载中
        state.update_task(task_id, "downloading")
        
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(
                executor,
                lambda: download_video_with_progress(
                    url=url,
                    output_path=output_path,
                    format=format,
                    quiet=quiet,
                    cookies=cookies,
                    task_id=task_id
                )
            )
        state.update_task(task_id, "completed", result=result)
    except Exception as e:
        # 分类错误并更新任务状态
        error_info = classify_error(e, {
            'url': url,
            'format': format,
            'cookies_used': cookies is not None,
            'task_id': task_id
        })
        state.update_task_error(task_id, error_info)
        state.update_task(task_id, "failed")
    finally:
        # 无论任务成功还是失败，都清理临时cookie文件
        if cookies and cookies.startswith("cookies/temp_"):
            cleanup_temp_cookies(task_id)

@app.post("/download", response_class=JSONResponse)
async def api_download_video(request: DownloadRequest):
    """
    Submit a video download task and return a task ID to track progress.
    """
    # 如果有相同的url和output_path的任务已经存在，直接返回该任务
    existing_task = next((task for task in state.tasks.values() if task.format == request.format and task.url == request.url and task.output_path == request.output_path), None)
    if existing_task:
        return {"status": "success", "task_id": existing_task.id}
    task_id = state.add_task(request.url, request.output_path, request.format)
    
    # 处理cookies参数
    cookies_to_use = request.cookies
    
    # 如果提供了JSON格式的cookies，将其转换为临时文件
    if request.json_cookies:
        try:
            # 为任务创建临时cookies文件
            temp_cookies_path = f"cookies/temp_{task_id}.txt"
            save_json_cookies_to_file(request.json_cookies, temp_cookies_path)
            cookies_to_use = temp_cookies_path
        except Exception as e:
            # 如果JSON cookies转换失败，记录错误但继续使用普通cookies
            print(f"Failed to convert JSON cookies: {e}")
    
    # Asynchronously execute download task
    asyncio.create_task(process_download_task(
        task_id=task_id,
        url=request.url,
        output_path=request.output_path,
        format=request.format,
        quiet=request.quiet,
        cookies=cookies_to_use
    ))
    
    return {"status": "success", "task_id": task_id}

@app.get("/task/{task_id}", response_class=JSONResponse)
async def get_task_status(task_id: str):
    """
    Get the status of a specific download task with detailed progress and error information.
    """
    task = state.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")
    
    response = {
        "status": "success",
        "data": {
            "id": task.id,
            "url": task.url,
            "output_path": task.output_path,
            "format": task.format,
            "status": task.status,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat()
        }
    }
    
    # 添加进度信息
    if task.progress:
        response["data"]["progress"] = {
            "downloaded_bytes": task.progress.downloaded_bytes,
            "total_bytes": task.progress.total_bytes,
            "speed": task.progress.speed,
            "eta": task.progress.eta,
            "percentage": task.progress.percentage,
            "status": task.progress.status,
            "filename": task.progress.filename,
            "elapsed_time": task.progress.elapsed_time,
            "speed_str": task.progress.speed_str,
            "eta_str": task.progress.eta_str,
            "downloaded_str": task.progress.downloaded_str,
            "total_str": task.progress.total_str
        }
    
    # 添加结果信息
    if task.status == "completed" and task.result:
        response["data"]["result"] = task.result
    
    # 添加错误信息
    elif task.status == "failed" and task.error:
        response["data"]["error"] = {
            "type": task.error.type.value,
            "message": task.error.message,
            "timestamp": task.error.timestamp.isoformat(),
            "stack_trace": task.error.stack_trace,
            "context": task.error.context,
            "retry_possible": task.error.retry_possible,
            "suggestions": task.error.suggestions
        }
    
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
        result = list_available_formats(url, cookies=cookies)
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

@app.post("/set-cookies")
async def set_cookies(request: SetCookiesRequest):
    """
    通过JSON格式设置全局cookie
    """
    try:
        if not request.cookies:
            raise HTTPException(status_code=400, detail="Cookies list cannot be empty")
        
        # 保存JSON cookies到文件
        cookies_path = save_json_cookies_to_file(request.cookies)
        
        file_stat = os.stat(cookies_path)
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "JSON cookies saved successfully",
                "path": cookies_path,
                "cookie_count": len(request.cookies),
                "size": file_stat.st_size,
                "modified": datetime.datetime.fromtimestamp(file_stat.st_mtime).isoformat()
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set cookies: {str(e)}")

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
        # 从结果中提取文件名和路径 tast.result.requested_downloads[0].filename
        filename = task.result.get("requested_downloads", [{}])[0].get("filename")
        if not filename:
            requested_filename = task.result.get("requested_filename")
            if requested_filename:
                filename = requested_filename
            else:
                # 尝试构建可能的文件路径
                title = task.result.get("title", "video")
                ext = task.result.get("ext", "mp4")
                filename = os.path.join(task.output_path, f"{title}.{ext}")
        
        # 检查文件是否存在
        if not os.path.exists(filename):
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

def start_api():
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    print("Starting yt-dlp API server...")
    start_api()
