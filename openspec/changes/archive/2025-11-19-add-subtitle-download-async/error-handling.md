# 错误处理和边界情况分析

## 错误分类体系

### 1. 客户端错误 (4xx)
**参数验证错误**
- 无效的URL格式
- 不支持的视频平台
- 无效的语言代码格式
- 不支持的字幕格式
- 请求体格式错误

**资源访问错误**
- 视频不存在或已被删除
- 视频为私有或需要登录
- 地理位置限制
- 字幕不可用

**请求限制错误**
- 超出频率限制
- 并发任务数量超限
- 请求体过大

### 2. 服务器错误 (5xx)
**字幕提取错误**
- yt-dlp工具错误
- 网络连接超时
- 视频解析失败
- 字幕文件损坏

**系统资源错误**
- 磁盘空间不足
- 内存不足
- 数据库连接失败
- 文件系统权限错误

## 详细错误处理

### URL验证边界情况

```python
def validate_subtitle_url(url: str) -> Tuple[bool, str]:
    """URL验证和错误消息"""

    # 空URL
    if not url or not url.strip():
        return False, "URL cannot be empty"

    url = url.strip()

    # 格式验证
    if not url.startswith(('http://', 'https://')):
        return False, "URL must start with http:// or https://"

    # 长度限制
    if len(url) > 2048:
        return False, "URL too long (max 2048 characters)"

    # 支持的域名验证
    supported_patterns = [
        r'^https?://(www\.)?youtube\.com/watch\?v=',
        r'^https?://youtu\.be/',
        r'^https?://(www\.)?youtube\.com/embed/',
    ]

    if not any(re.search(pattern, url) for pattern in supported_patterns):
        return False, "Unsupported URL. Only YouTube URLs are supported"

    return True, ""
```

**边界情况测试用例:**
- `""` → "URL cannot be empty"
- `"   "` → "URL cannot be empty"
- `"invalid-url"` → "URL must start with http:// or https://"
- `"https://example.com/video"` → "Unsupported URL. Only YouTube URLs are supported"
- `"https://www.youtube.com/watch?v=" + "a" * 1000` → "URL too long"

### 语言代码验证边界情况

```python
def validate_subtitle_languages(languages: List[str]) -> Tuple[bool, str]:
    """语言代码验证和错误消息"""

    # 空列表
    if not languages:
        return False, "Languages list cannot be empty"

    # 数量限制
    if len(languages) > 10:
        return False, "Too many languages requested (max 10)"

    # 重复检查
    if len(set(languages)) != len(languages):
        return False, "Duplicate language codes found"

    # 格式验证
    valid_pattern = re.compile(r'^[a-z]{2,3}(-[A-Z]{2})?$')  # en, en-US, zh-CN等
    invalid_codes = [lang for lang in languages if not valid_pattern.match(lang)]

    if invalid_codes:
        return False, f"Invalid language codes: {', '.join(invalid_codes)}"

    return True, ""
```

**边界情况测试用例:**
- `[]` → "Languages list cannot be empty"
- `["en", "en"]` → "Duplicate language codes found"
- `["EN", "ZH"]` → "Invalid language codes: EN, ZH"（大小写敏感）
- `["invalid", "xyz"]` → "Invalid language codes: invalid, xyz"
- `["a" * 10] * 20` → "Too many languages requested (max 10)"

### 字幕格式验证边界情况

```python
def validate_subtitle_format(format_str: str) -> Tuple[bool, str]:
    """字幕格式验证"""

    if not format_str:
        return False, "Subtitle format cannot be empty"

    format_str = format_str.lower().strip()

    if format_str not in ['srt', 'vtt', 'ass', 'ssa']:
        return False, f"Unsupported subtitle format: '{format_str}'. Supported: srt, vtt, ass, ssa"

    return True, ""
```

### 输出路径验证边界情况

```python
def validate_output_path(path: str) -> Tuple[bool, str]:
    """输出路径验证和规范化"""

    if not path:
        return False, "Output path cannot be empty"

    # 路径规范化
    path = os.path.normpath(path)

    # 绝对路径检查
    if os.path.isabs(path):
        return False, "Absolute paths not allowed for security reasons"

    # 路径遍历攻击防护
    if '..' in path or path.startswith('/'):
        return False, "Path traversal not allowed"

    # 长度限制
    if len(path) > 255:
        return False, "Output path too long"

    # 非法字符检查
    illegal_chars = ['<', '>', ':', '"', '|', '?', '*']
    if any(char in path for char in illegal_chars):
        return False, f"Invalid characters in path: {', '.join(illegal_chars)}"

    return True, path
```

## 异常场景处理

### yt-dlp异常处理

```python
import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError

class SubtitleDownloadError(Exception):
    """字幕下载自定义异常"""
    pass

async def handle_subtitle_download_exceptions(url: str, config: Dict):
    """统一处理字幕下载异常"""

    try:
        # 配置yt-dlp选项
        ydl_opts = {
            'writesubtitles': True,
            'subtitleslangs': config.get('languages', ['en']),
            'skip_download': True,  # 只要字幕，不要视频
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            # 检查字幕可用性
            if not info.get('subtitles') and not info.get('automatic_captions'):
                raise SubtitleDownloadError("No subtitles available for this video")

            return info

    except ExtractorError as e:
        if "Video unavailable" in str(e):
            raise SubtitleDownloadError("Video is unavailable or private")
        elif "geoblocked" in str(e).lower():
            raise SubtitleDownloadError("Video is geo-blocked in your region")
        else:
            raise SubtitleDownloadError(f"Failed to extract video info: {str(e)}")

    except DownloadError as e:
        if "network" in str(e).lower():
            raise SubtitleDownloadError("Network error while downloading subtitles")
        else:
            raise SubtitleDownloadError(f"Download failed: {str(e)}")

    except Exception as e:
        # 捕获所有其他异常
        raise SubtitleDownloadError(f"Unexpected error: {str(e)}")
```

### 文件系统异常处理

```python
def safe_filename_generator(video_title: str, language: str, format: str) -> str:
    """安全的文件名生成"""

    # 基础清理
    safe_title = re.sub(r'[<>:"/\\|?*]', '_', video_title)
    safe_title = re.sub(r'\s+', '_', safe_title)
    safe_title = safe_title.strip('._')

    # 长度限制
    if len(safe_title) > 200:
        safe_title = safe_title[:200]

    # 构建文件名
    filename = f"{safe_title}_{language}.{format}"

    # 最终检查
    if len(filename) > 255:
        filename = f"subtitle_{language}.{format}"

    return filename

def ensure_directory_exists(path: str) -> None:
    """确保目录存在，处理权限问题"""

    try:
        os.makedirs(path, exist_ok=True)
    except PermissionError:
        raise SubtitleDownloadError(f"Permission denied: cannot create directory '{path}'")
    except OSError as e:
        raise SubtitleDownloadError(f"Failed to create directory '{path}': {str(e)}")
```

## 错误响应标准化

### HTTP状态码映射

```python
class SubtitleErrorCode:
    """字幕下载错误代码"""

    # 客户端错误 (400)
    INVALID_URL = "INVALID_URL"
    UNSUPPORTED_PLATFORM = "UNSUPPORTED_PLATFORM"
    INVALID_LANGUAGES = "INVALID_LANGUAGES"
    INVALID_FORMAT = "INVALID_FORMAT"
    INVALID_PATH = "INVALID_PATH"
    TOO_MANY_REQUESTS = "TOO_MANY_REQUESTS"

    # 资源错误 (404)
    VIDEO_NOT_FOUND = "VIDEO_NOT_FOUND"
    SUBTITLES_UNAVAILABLE = "SUBTITLES_UNAVAILABLE"

    # 服务器错误 (500)
    EXTRACTION_ERROR = "EXTRACTION_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    FILESYSTEM_ERROR = "FILESYSTEM_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"

def map_exception_to_http_error(exception: Exception) -> Tuple[int, Dict]:
    """将异常映射为HTTP错误响应"""

    if isinstance(exception, SubtitleDownloadError):
        error_msg = str(exception)

        if "URL" in error_msg:
            return 400, {
                "error_code": SubtitleErrorCode.INVALID_URL,
                "detail": error_msg,
                "error_type": "validation_error"
            }
        elif "language" in error_msg.lower():
            return 400, {
                "error_code": SubtitleErrorCode.INVALID_LANGUAGES,
                "detail": error_msg,
                "error_type": "validation_error"
            }
        elif "format" in error_msg.lower():
            return 400, {
                "error_code": SubtitleErrorCode.INVALID_FORMAT,
                "detail": error_msg,
                "error_type": "validation_error"
            }
        elif "unavailable" in error_msg.lower():
            return 404, {
                "error_code": SubtitleErrorCode.VIDEO_NOT_FOUND,
                "detail": error_msg,
                "error_type": "resource_error"
            }
        elif "subtitles" in error_msg.lower():
            return 404, {
                "error_code": SubtitleErrorCode.SUBTITLES_UNAVAILABLE,
                "detail": error_msg,
                "error_type": "resource_error"
            }
        elif "network" in error_msg.lower():
            return 500, {
                "error_code": SubtitleErrorCode.NETWORK_ERROR,
                "detail": error_msg,
                "error_type": "transient_error"  # 可重试错误
            }
        else:
            return 500, {
                "error_code": SubtitleErrorCode.EXTRACTION_ERROR,
                "detail": error_msg,
                "error_type": "permanent_error"
            }

    # 其他异常
    return 500, {
        "error_code": SubtitleErrorCode.INTERNAL_ERROR,
        "detail": "Internal server error",
        "error_type": "system_error"
    }
```

## 重试机制

### 自动重试策略

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=lambda e: isinstance(e, SubtitleDownloadError) and "network" in str(e).lower()
)
async def robust_subtitle_download(url: str, config: Dict):
    """带重试的字幕下载"""

    return await handle_subtitle_download_exceptions(url, config)
```

### 任务状态管理

```python
class TaskStateManager:
    """任务状态管理和错误恢复"""

    @staticmethod
    def update_task_with_error(task_id: str, error: Exception):
        """更新任务状态为错误，记录详细错误信息"""

        status_code, error_info = map_exception_to_http_error(error)

        # 更新数据库中的任务状态
        error_json = json.dumps({
            "error_code": error_info["error_code"],
            "error_type": error_info["error_type"],
            "timestamp": datetime.utcnow().isoformat(),
            "details": error_info["detail"]
        })

        state.update_task_status(
            task_id=task_id,
            status="failed",
            error=error_json
        )

        return status_code, error_info
```

## 监控和日志

### 错误监控

```python
import logging

# 配置日志
logger = logging.getLogger("subtitle_download")

def log_subtitle_error(task_id: str, error: Exception, context: Dict):
    """详细的错误日志"""

    error_info = {
        "task_id": task_id,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context,
        "timestamp": datetime.utcnow().isoformat()
    }

    # 根据错误类型选择日志级别
    if isinstance(error, SubtitleDownloadError):
        if "network" in str(error).lower():
            logger.warning(f"Network error for task {task_id}: {error_info}")
        else:
            logger.error(f"Subtitle download error for task {task_id}: {error_info}")
    else:
        logger.critical(f"Unexpected error for task {task_id}: {error_info}")
```

这个错误处理框架覆盖了所有主要的边界情况和异常场景，确保系统的健壮性和用户体验的一致性。