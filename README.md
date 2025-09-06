# yt-dlp API Service

> **Quick Start:** `docker run -p 18000:8000 -p 17860:7860 qdw497874677/my_yt_dlp_api:latest` to get started instantly!

[English](README.md) | [中文](README_CN.md)

A RESTful API service built with FastAPI and yt-dlp for video information retrieval and downloading. This service provides both a powerful API and an easy-to-use web interface for downloading videos from YouTube and other platforms.

## Features

- 🚀 **Asynchronous Processing**: Download tasks run in the background without blocking the API
- 📹 **Multiple Format Support**: Download videos in various formats and qualities
- 💾 **Persistent Storage**: Task status and history stored in SQLite database
- 📋 **Detailed Information**: Get comprehensive video metadata before downloading
- 🔌 **RESTful API**: Clean and intuitive API endpoints
- 🍪 **Cookie Authentication**: Bypass YouTube bot detection with cookie support
- 🌐 **Web Interface**: User-friendly Gradio interface for easy operation
- 🐳 **Docker Support**: Easy deployment with Docker and Docker Compose
- 📂 **Safe Filename Handling**: Automatic sanitization of filenames to prevent issues

## Requirements

- Docker (recommended) OR Python 3.7+
- ffmpeg (for video processing)
- Internet connection

## Quick Start

### Option 1: Using Pre-built Docker Image (Easiest)

```bash
# Run the service with one command
docker run -d \
  --name yt-dlp-api \
  -p 18000:8000 \
  -p 17860:7860 \
  -v $(pwd)/downloads:/app/downloads \
  -v $(pwd)/data:/app/data \
  qdw497874677/my_yt_dlp_api:latest

# Access the services:
# FastAPI API: http://localhost:18000
# Gradio Web Interface: http://localhost:17860
```

### Option 2: Using Docker Compose (Recommended for Development)

```bash
# Clone the repository
git clone <repository-url>
cd my_yt_dlp_api

# Start services with the provided script
./start.sh

# Or start manually:
# docker-compose up -d
```

This will start both services:
- **FastAPI API**: http://localhost:18000
- **Gradio Web Interface**: http://localhost:17860

### Option 3: Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start FastAPI server
python main.py

# In another terminal, start Gradio interface
python gradio_app.py
```

Services:
- **FastAPI API**: http://localhost:8000
- **Gradio Web Interface**: http://localhost:7860

## API Documentation

### 1. Submit Download Task

**Request:**
```http
POST /download
```

**Request Body:**
```json
{
    "url": "video_url",
    "output_path": "./downloads",  // Optional, defaults to "./downloads"
    "format": "bestvideo+bestaudio/best",  // Optional, defaults to best quality
    "quiet": false  // Optional, whether to download quietly
}
```

**Response:**
```json
{
    "status": "success",
    "task_id": "task_id"
}
```

### 2. Get Task Status

**Request:**
```http
GET /task/{task_id}
```

**Response:**
```json
{
    "status": "success",
    "data": {
        "id": "task_id",
        "url": "video_url",
        "status": "pending/completed/failed",
        "result": {}, // Contains download info when completed
        "error": "error message" // Contains error when failed
    }
}
```

### 3. List All Tasks

**Request:**
```http
GET /tasks
```

**Response:**
```json
{
    "status": "success",
    "data": [
        {
            "id": "task_id",
            "url": "video_url",
            "status": "task_status"
            // ... other task information
        }
    ]
}
```

### 4. Get Video Information

**Request:**
```http
GET /info?url={video_url}
```

**Response:**
```json
{
    "status": "success",
    "data": {
        // Detailed video information
    }
}
```

### 5. List Available Video Formats

**Request:**
```http
GET /formats?url={video_url}
```

**Response:**
```json
{
    "status": "success",
    "data": [
        {
            "format_id": "format_id",
            "ext": "file_extension",
            "resolution": "resolution",
            // ... other format information
        }
    ]
}
```

### 6. Cookie Authentication Management

#### Upload Cookies File

**Request:**
```http
POST /upload-cookies
```

**Request Body (multipart/form-data):**
```
file: @cookies.txt
```

**Response:**
```json
{
    "status": "success",
    "message": "Cookies 文件上传成功",
    "path": "cookies/cookies.txt",
    "filename": "cookies.txt",
    "size": 1024
}
```

#### Check Cookies Status

**Request:**
```http
GET /cookies-status
```

**Response:**
```json
{
    "status": "success",
    "exists": true,
    "path": "cookies/cookies.txt",
    "size": 1024,
    "modified": "2023-12-01T10:30:00.123456",
    "permissions": "600"
}
```

#### Delete Cookies File

**Request:**
```http
DELETE /cookies
```

**Response:**
```json
{
    "status": "success",
    "message": "Cookies 文件删除成功"
}
```

### 7. Download with Cookie Authentication

**Request:**
```http
POST /download
```

**Request Body:**
```json
{
    "url": "video_url",
    "output_path": "./downloads",
    "format": "bestvideo+bestaudio/best",
    "quiet": false,
    "cookies": "cookies/cookies.txt"  // Path to cookies file or browser name
}
```

**Response:**
```json
{
    "status": "success",
    "task_id": "task_id"
}
```

### 8. Get Video Information with Cookie Authentication

**Request:**
```http
GET /info?url={video_url}&cookies={cookies_path}
```

**Response:**
```json
{
    "status": "success",
    "data": {
        // Detailed video information
    }
}
```

### 9. List Available Video Formats with Cookie Authentication

**Request:**
```http
GET /formats?url={video_url}&cookies={cookies_path}
```

**Response:**
```json
{
    "status": "success",
    "data": [
        {
            "format_id": "format_id",
            "ext": "file_extension",
            "resolution": "resolution",
            // ... other format information
        }
    ]
}
```

### 10. Download Completed Task's Video File

**Request:**
```http
GET /download/{task_id}/file
```

**Response:**
- Success: Returns video file stream directly
- Failure: Returns error message
```json
{
    "detail": "error message"
}
```

## Cookie Authentication Guide

### Why Use Cookie Authentication?

YouTube may detect automated access and return the following error:
```
ERROR: [youtube] VIDEO_ID: Sign in to confirm you're not a bot.
```

Cookie authentication helps bypass this detection by using valid user session cookies.

### Getting Cookies File

#### Method 1: Browser Extension (Recommended)

1. **Chrome/Firefox**: Install "Get cookies.txt" extension
2. Visit YouTube and log in to your account
3. Click the extension icon
4. Select "Export" → "Export as Netscape HTTP Cookie File"
5. Save the file as `cookies.txt`

#### Method 2: Manual Export

1. Log in to YouTube in your browser
2. Open Developer Tools (F12)
3. Go to Application/Storage tab
4. Find cookies for youtube.com
5. Export them in Netscape format

### Using Cookie Authentication

#### Step 1: Upload Cookies to Server

```bash
curl -X POST "http://localhost:8000/upload-cookies" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@/path/to/cookies.txt"
```

#### Step 2: Verify Cookies Status

```bash
curl -X GET "http://localhost:8000/cookies-status"
```

#### Step 3: Download Video with Cookies

```bash
curl -X POST "http://localhost:8000/download" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://www.youtube.com/watch?v=VIDEO_ID",
       "format": "best",
       "cookies": "cookies/cookies.txt"
     }'
```

### Alternative: Browser Cookies

Instead of uploading a cookies file, you can use browser cookies directly by specifying the browser name:

```json
{
    "url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "format": "best",
    "cookies": "chrome"  // or "firefox", "edge", "safari", "brave", "opera"
}
```

### Complete Workflow Example

```bash
#!/bin/bash

# Server URL
SERVER_URL="http://localhost:8000"
VIDEO_URL="https://www.youtube.com/watch?v=VIDEO_ID"

# 1. Upload cookies file
echo "Uploading cookies..."
curl -X POST "$SERVER_URL/upload-cookies" \
     -F "file=@cookies.txt"

# 2. Check cookies status
echo "Checking cookies status..."
curl -X GET "$SERVER_URL/cookies-status"

# 3. Get video information with cookies
echo "Getting video information..."
curl -X GET "$SERVER_URL/info?url=$VIDEO_URL&cookies=cookies/cookies.txt"

# 4. Submit download task with cookies
echo "Submitting download task..."
response=$(curl -s -X POST "$SERVER_URL/download" \
     -H "Content-Type: application/json" \
     -d "{
       \"url\": \"$VIDEO_URL\",
       \"format\": \"best\",
       \"cookies\": \"cookies/cookies.txt\"
     }")

# Extract task ID
task_id=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin)['task_id'])")
echo "Task ID: $task_id"

# 5. Monitor task status
echo "Monitoring download status..."
while true; do
    status_response=$(curl -s "$SERVER_URL/task/$task_id")
    status=$(echo "$status_response" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['status'])")
    echo "Status: $status"
    
    if [ "$status" = "completed" ]; then
        echo "Download completed!"
        break
    elif [ "$status" = "failed" ]; then
        error=$(echo "$status_response" | python3 -c "import sys, json; print(json.load(sys.stdin)['data'].get('error', 'Unknown error'))")
        echo "Download failed: $error"
        exit 1
    fi
    
    sleep 2
done

# 6. Download the video file
echo "Downloading video file..."
curl -s "$SERVER_URL/download/$task_id/file" -o "downloaded_video.mp4"
echo "Video saved as: downloaded_video.mp4"
```

### Python Client Example

```python
import requests
import time

class YouTubeDownloaderClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
    
    def upload_cookies(self, cookies_file_path):
        """Upload cookies file to server"""
        with open(cookies_file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{self.base_url}/upload-cookies", files=files)
            response.raise_for_status()
            return response.json()
    
    def download_video(self, url, format="best", cookies_path="cookies/cookies.txt"):
        """Download video with cookie authentication"""
        payload = {
            "url": url,
            "format": format,
            "cookies": cookies_path
        }
        
        response = requests.post(f"{self.base_url}/download", json=payload)
        response.raise_for_status()
        task_id = response.json()['task_id']
        
        # Wait for completion
        while True:
            status_response = requests.get(f"{self.base_url}/task/{task_id}")
            status_data = status_response.json()['data']
            status = status_data['status']
            
            if status == 'completed':
                return status_data
            elif status == 'failed':
                raise Exception(f"Download failed: {status_data.get('error', 'Unknown error')}")
            
            time.sleep(2)

# Usage
client = YouTubeDownloaderClient("http://localhost:8000")

# Upload cookies
client.upload_cookies("cookies.txt")

# Download video
result = client.download_video("https://www.youtube.com/watch?v=VIDEO_ID")
print("Download completed:", result)
```

### Important Notes

1. **Cookie Expiration**: Browser cookies typically expire after a period. If downloads start failing, re-upload a fresh cookies file.
2. **Security**: Cookies contain sensitive authentication information. Keep them secure and don't share them.
3. **File Permissions**: Uploaded cookies files are automatically set to 600 permissions (read/write for owner only).
4. **Server Environment**: In Docker or server environments, use the file upload method rather than browser cookies.
5. **Supported Browsers**: chrome, firefox, edge, safari, brave, opera

For more detailed information, see [API_COOKIE_GUIDE.md](API_COOKIE_GUIDE.md).

## Error Handling

All API endpoints return appropriate HTTP status codes and detailed error messages when errors occur:

- 404: Resource not found
- 400: Bad request parameters
- 500: Internal server error

## Data Persistence

The service uses SQLite database to store task information, with the database file defaulting to `tasks.db`. Task information includes:

- Task ID
- Video URL
- Output path
- Download format
- Task status
- Download result
- Error message
- Timestamp

## Docker Support

The project includes a Dockerfile and can be built and run using the following commands:

```bash
# Build image
docker build -t yt-dlp-api-service .

# Run container
docker run -p 8000:8000 -v $(pwd)/downloads:/app/downloads yt-dlp-api-service
```

### Docker Compose

Alternatively, you can use Docker Compose to run the service. A `docker-compose.yml` file is provided with the necessary configuration:

```bash
# Start the service
docker-compose up

# Start the service in detached mode
docker-compose up -d

docker-compose --file docker-compose-pull.yml up -d

# Stop the service
docker-compose down
```

The Docker Compose configuration includes:
- Port mapping (8000:8000)
- Volume mounts for downloads and task database persistence
- Environment variables for proper Python output
- Restart policy for automatic recovery

## Web Interface

The project includes a user-friendly Gradio web interface that provides easy access to all API features:

### Features
- **Video Download**: Submit download tasks with format selection
- **Video Information**: View video metadata (title, duration, uploader)
- **Format Selection**: Browse and select from available video formats
- **Real-time Status**: Monitor download progress with live updates

### Access
- **Docker**: http://localhost:17860
- **Local Development**: http://localhost:7860

### Usage
1. Open the web interface in your browser
2. Navigate between tabs for different functions
3. Enter video URLs and select desired formats
4. Monitor download progress in real-time
5. Download completed videos directly through the interface

## Architecture Overview

### Service Components
- **FastAPI Service** (Port 8000/18000): RESTful API backend
- **Gradio Service** (Port 7860/17860): Web frontend interface
- **Supervisor**: Process manager for both services
- **SQLite Database**: Persistent task storage
- **File Storage**: Downloaded video files

### Service Communication
- Gradio interface communicates with FastAPI via HTTP requests
- Both services share the same SQLite database and file storage
- Supervisor ensures both services run simultaneously and auto-restart on failure

## Important Notes

1. Ensure sufficient disk space for storing downloaded videos
2. Configure appropriate security measures in production environment
3. Comply with video platform terms of service and copyright regulations
4. Both services are designed to work together in the same container
5. Web interface automatically detects container environment and adjusts API endpoints
