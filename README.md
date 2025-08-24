# yt-dlp API Service

> **Quick Start:** `docker run -p 8000:8000 hipc/yt-dlp` to get started instantly!

[English](README.md) | [中文](README_CN.md)

A RESTful API service built with FastAPI and yt-dlp for video information retrieval and downloading.

## Features

- Asynchronous download processing
- Multiple video format support
- Persistent task status storage
- Detailed video information queries
- RESTful API design

## Requirements

- Python 3.7+
- FastAPI
- yt-dlp
- uvicorn
- pydantic
- sqlite3

## Quick Start

### Option 1: Using Docker (Recommended)

1. Clone and start the services:
```bash
git clone <repository-url>
cd my_yt_dlp_api
./start.sh
```

This will start both services:
- **FastAPI API**: http://localhost:18000
- **Gradio Web Interface**: http://localhost:17860

### Option 2: Manual Docker Setup

```bash
# Build and start with Docker Compose
docker-compose up -d

# Or use pre-built image
docker-compose -f docker-compose-pull.yml up -d
```

### Option 3: Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start FastAPI server:
```bash
python main.py
```

3. In another terminal, start Gradio interface:
```bash
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

### 6. Download Completed Task's Video File

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
docker build -t yt-dlp-api .

# Run container
docker run -p 8000:8000 -v $(pwd)/downloads:/app/downloads yt-dlp-api
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
