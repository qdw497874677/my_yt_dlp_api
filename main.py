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
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
import uvicorn
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor

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
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

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
        
        # 创建任务表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            output_path TEXT NOT NULL,
            format TEXT NOT NULL,
            status TEXT NOT NULL,
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
            
            cursor.execute("SELECT id, url, output_path, format, status, result, error_json FROM tasks")
            rows = cursor.fetchall()
            
            for row in rows:
                task_id, url, output_path, format, status, result_json, error = row
                
                # 解析JSON结果（如果有）
                result = json.loads(result_json) if result_json else None
                error = json.loads(error) if error else None
                
                # 创建Task对象并存储在内存中
                task = Task(
                    id=task_id,
                    url=url,
                    output_path=output_path,
                    format=format,
                    status=status,
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
            
            # 使用REPLACE策略插入/更新任务
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
    
    def add_task(self, url: str, output_path: str, format: str) -> str:
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            url=url,
            output_path=output_path,
            format=format,
            status="pending"
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
    }
    
    # 如果需要更安全的处理，我们可以在下载前先获取信息
    temp_ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
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

app = FastAPI(title="yt-dlp API", description="API for downloading videos using yt-dlp")

class DownloadRequest(BaseModel):
    url: str
    output_path: str = "./downloads"
    format: str = "bestvideo+bestaudio/best"
    quiet: bool = False
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

@app.post("/download", response_class=JSONResponse)
async def api_download_video(request: DownloadRequest):
    """
    Submit a video download task and return a task ID to track progress.
    """
    print(f"Received download request for URL: {request.url}")
    # 如果有相同的url和output_path的任务已经存在，直接返回该任务
    existing_task = next((task for task in state.tasks.values() if task.format == request.format and task.url == request.url and task.output_path == request.output_path), None)
    if existing_task:
        print(f"Found existing task with ID: {existing_task.id}")
        return {"status": "success", "task_id": existing_task.id}
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
