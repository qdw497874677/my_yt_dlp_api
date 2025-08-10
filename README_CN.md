# yt-dlp API 服务

> **快速开始：** `docker run -p 8000:8000 hipc/yt-dlp` 立即开始使用！

[English](README.md) | [中文](README_CN.md)

这是一个基于 FastAPI 和 yt-dlp 构建的 RESTful API 服务，提供视频信息获取和下载功能。

## 功能特点

- 异步下载处理
- 支持多种视频格式
- 任务状态持久化存储
- 提供详细的视频信息查询
- RESTful API 设计

## 安装要求

- Python 3.7+
- FastAPI
- yt-dlp
- uvicorn
- pydantic
- sqlite3

## 快速开始

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 启动服务器：
```bash
python main.py
```

服务器将在 http://localhost:8000 启动

## API 接口文档

### 1. 提交下载任务

**请求：**
```http
POST /download
```

**请求体：**
```json
{
    "url": "视频URL",
    "output_path": "./downloads",  // 可选，默认为 "./downloads"
    "format": "bestvideo+bestaudio/best",  // 可选，默认为最佳质量
    "quiet": false  // 可选，是否静默下载
}
```

**返回：**
```json
{
    "status": "success",
    "task_id": "任务ID"
}
```

### 2. 获取任务状态

**请求：**
```http
GET /task/{task_id}
```

**返回：**
```json
{
    "status": "success",
    "data": {
        "id": "任务ID",
        "url": "视频URL",
        "status": "pending/completed/failed",
        "result": {}, // 当任务完成时包含下载信息
        "error": "错误信息" // 当任务失败时包含
    }
}
```

### 3. 获取所有任务列表

**请求：**
```http
GET /tasks
```

**返回：**
```json
{
    "status": "success",
    "data": [
        {
            "id": "任务ID",
            "url": "视频URL",
            "status": "任务状态"
            // ... 其他任务信息
        }
    ]
}
```

### 4. 获取视频信息

**请求：**
```http
GET /info?url={video_url}
```

**返回：**
```json
{
    "status": "success",
    "data": {
        // 视频详细信息
    }
}
```

### 5. 获取视频可用格式

**请求：**
```http
GET /formats?url={video_url}
```

**返回：**
```json
{
    "status": "success",
    "data": [
        {
            "format_id": "格式ID",
            "ext": "文件扩展名",
            "resolution": "分辨率",
            // ... 其他格式信息
        }
    ]
}
```

### 6. 下载已完成任务的视频文件

**请求：**
```http
GET /download/{task_id}/file
```

**返回：**
- 成功：直接返回视频文件流
- 失败：返回错误信息
```json
{
    "detail": "错误信息"
}
```

## 错误处理

所有 API 接口在发生错误时会返回适当的 HTTP 状态码和详细的错误信息：

- 404: 资源未找到
- 400: 请求参数错误
- 500: 服务器内部错误

## 数据持久化

服务使用 SQLite 数据库存储任务信息，数据库文件默认保存为 `tasks.db`。任务信息包括：

- 任务ID
- 视频URL
- 输出路径
- 下载格式
- 任务状态
- 下载结果
- 错误信息
- 时间戳

## Docker 支持

项目提供了 Dockerfile，可以通过以下命令构建和运行容器：

```bash
# 构建镜像
docker build -t yt-dlp-api .

# 运行容器
docker run -p 8000:8000 -v $(pwd)/downloads:/app/downloads yt-dlp-api
```

### Docker Compose

此外，您也可以使用 Docker Compose 来运行服务。项目提供了 `docker-compose.yml` 文件，其中包含必要的配置：

```bash
# 启动服务
docker-compose up

# 以分离模式启动服务
docker-compose up -d

# 停止服务
docker-compose down
```

Docker Compose 配置包括：
- 端口映射 (8000:8000)
- 下载目录和任务数据库的卷挂载以实现持久化
- 环境变量以确保正确的 Python 输出
- 重启策略以实现自动恢复

## 注意事项

1. 请确保有足够的磁盘空间存储下载的视频
2. 建议在生产环境中配置适当的安全措施
3. 遵守视频平台的使用条款和版权规定
