# API端点设计详细规范

## 新增API端点

### POST /download-subtitles
提交字幕下载任务，支持单个或多个语言的异步下载。

**请求格式:**
```python
class SubtitleDownloadRequest(BaseModel):
    url: str                           # 视频URL（必需）
    output_path: str = "./downloads"   # 输出目录（可选，默认值）
    languages: List[str] = ["en"]      # 语言代码列表，默认英语
    auto_select: bool = True           # 自动选择最佳字幕（默认True）
    subtitle_format: str = "srt"       # 字幕格式（默认srt）
```

**请求示例:**
```json
// 基础请求 - 下载英文字幕
{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "languages": ["en"]
}

// 批量请求 - 下载多语言字幕
{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "languages": ["en", "zh", "es"],
    "auto_select": true,
    "output_path": "./subtitles"
}

// 自动选择 - 让系统选择最佳可用字幕
{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "auto_select": true
}
```

**响应格式:**
```json
{
    "status": "success",
    "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**错误响应:**
```json
// 400错误 - 参数验证失败
{
    "detail": "Invalid URL format"
}

// 500错误 - 服务器错误
{
    "detail": "Failed to create subtitle download task: internal error"
}
```

## 现有API端点的扩展

### GET /task/{task_id}
查询任务状态，扩展支持字幕任务类型。

**响应格式扩展:**
```json
// 视频任务（现有格式不变）
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "format": "mp4",
    "status": "completed",
    "task_type": "video",
    "result": {
        "output_path": "./downloads/video.mp4",
        "size": 52428800
    },
    "created_at": "2025-01-19T10:30:00Z",
    "updated_at": "2025-01-19T10:32:15Z"
}

// 字幕任务（新增格式）
{
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "format": "en,zh",
    "status": "completed",
    "task_type": "subtitle",
    "subtitle_config": {
        "languages": ["en", "zh"],
        "auto_select": true,
        "format": "srt"
    },
    "result": {
        "downloaded_files": [
            {
                "language": "en",
                "path": "./downloads/video_en.srt",
                "size": 24576
            },
            {
                "language": "zh",
                "path": "./downloads/video_zh.srt",
                "size": 18432
            }
        ],
        "total_files": 2
    },
    "created_at": "2025-01-19T10:35:00Z",
    "updated_at": "2025-01-19T10:35:45Z"
}
```

### GET /tasks
任务列表查询，添加任务类型过滤功能。

**新增查询参数:**
- `task_type`: 过滤任务类型（video/subtitle）
- `language`: 过滤包含特定语言的字幕任务

**查询示例:**
```
# 获取所有字幕任务
GET /tasks?task_type=subtitle

# 获取包含英文字幕的任务
GET /tasks?task_type=subtitle&language=en

# 获取所有任务（现有行为不变）
GET /tasks
```

**响应格式扩展:**
```json
{
    "status": "success",
    "data": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "format": "mp4",
            "status": "completed",
            "task_type": "video",
            "created_at": "2025-01-19T10:30:00Z"
        },
        {
            "id": "550e8400-e29b-41d4-a716-446655440001",
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "format": "en,zh",
            "status": "completed",
            "task_type": "subtitle",
            "created_at": "2025-01-19T10:35:00Z"
        }
    ],
    "total": 2
}
```

## 现有端点的兼容性

### GET /download/{task_id}/file
文件下载端点，无需修改即可支持字幕文件下载。

**行为说明:**
- 对于单个字幕任务：返回该字幕文件
- 对于多个字幕任务：返回第一个字幕文件作为主要文件
- 对于视频任务：行为保持不变

### POST /download
现有视频下载端点行为完全不变，向后兼容性100%。

### 字幕相关现有端点
以下现有端点保持完全不变，确保向后兼容：

- `GET /subtitles` - 列出可用字幕语言
- `GET /subtitle` - 同步下载单个字幕文件

## 请求验证规则

### URL验证
```python
def validate_url(url: str) -> bool:
    """验证URL格式和域名支持"""
    if not url.startswith(('http://', 'https://')):
        return False

    # 支持的域名列表（复用现有逻辑）
    supported_domains = ['youtube.com', 'youtu.be', 'www.youtube.com']
    return any(domain in url for domain in supported_domains)
```

### 语言代码验证
```python
def validate_languages(languages: List[str]) -> bool:
    """验证ISO 639-1语言代码格式"""
    if not languages or len(languages) > 10:  # 限制最多10种语言
        return False

    # ISO 639-1语言代码正则（2-3个字母）
    language_pattern = re.compile(r'^[a-z]{2,3}$')
    return all(language_pattern.match(lang) for lang in languages)
```

### 格式验证
```python
SUPPORTED_FORMATS = ['srt', 'vtt', 'ass', 'ssa']

def validate_subtitle_format(format_str: str) -> bool:
    """验证字幕格式支持"""
    return format_str.lower() in SUPPORTED_FORMATS
```

## 错误处理规范

### 400 Bad Request - 参数错误
```json
{
    "detail": "Invalid languages parameter: expected list of ISO 639-1 codes"
}

{
    "detail": "Unsupported subtitle format: 'txt'. Supported formats: srt, vtt, ass"
}
```

### 404 Not Found - 资源不存在
```json
{
    "detail": "Task not found: invalid-task-id"
}

{
    "detail": "Subtitles not available for this video"
}
```

### 500 Internal Server Error - 服务器错误
```json
{
    "detail": "Failed to process subtitle download: yt-dlp extraction error"
}
```

## 状态码约定

### 成功响应
- `200 OK`: 查询操作成功
- `201 Created`: 资源创建成功（任务创建）

### 客户端错误
- `400 Bad Request`: 参数验证失败
- `404 Not Found`: 资源不存在
- `429 Too Many Requests`: 请求频率限制

### 服务器错误
- `500 Internal Server Error`: 服务器内部错误
- `503 Service Unavailable`: 服务暂时不可用

## HTTP头约定

### 响应头
```http
Content-Type: application/json
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, DELETE
Access-Control-Allow-Headers: Content-Type
```

### 文件下载头
```http
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="video_en.srt"
Content-Length: 24576
```

## 速率限制

### 端点限制
- `POST /download-subtitles`: 5请求/分钟/IP
- `GET /task/{task_id}`: 30请求/分钟/IP
- `GET /tasks`: 20请求/分钟/IP

### 全局限制
- 总并发字幕下载任务：10个
- 单用户并发任务：3个

## 示例工作流

### 基础字幕下载流程
```bash
# 1. 提交字幕下载任务
curl -X POST "http://localhost:8000/download-subtitles" \
     -H "Content-Type: application/json" \
     -d '{
         "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
         "languages": ["en"]
     }'

# 响应: {"status": "success", "task_id": "uuid-string"}

# 2. 查询任务状态
curl -X GET "http://localhost:8000/task/uuid-string"

# 响应: 包含status和其他信息的JSON

# 3. 下载字幕文件
curl -X GET "http://localhost:8000/download/uuid-string/file" \
     -o "subtitle.srt"
```

### 批量字幕下载流程
```bash
# 提交批量字幕下载任务
curl -X POST "http://localhost:8000/download-subtitles" \
     -H "Content-Type: application/json" \
     -d '{
         "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
         "languages": ["en", "zh", "es", "fr"],
         "auto_select": true
     }'

# 任务完成后，每个语言的字幕文件都可以通过相同的端点下载
# 文件命名：video_en.srt, video_zh.srt, video_es.srt, video_fr.srt
```