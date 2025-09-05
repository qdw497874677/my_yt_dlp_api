# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a yt-dlp API service built with FastAPI and Gradio, providing a RESTful API and web interface for video downloading. The service includes:

1. FastAPI backend (port 8000/18000) - RESTful API service
2. Gradio frontend (port 7860/17860) - Web interface
3. SQLite database for task persistence
4. Docker support with Supervisor for process management

## Common Development Commands

### Running the Service

Local development:
```bash
# Install dependencies
pip install -r requirements.txt

# Start FastAPI server
python main.py

# In another terminal, start Gradio interface
python gradio_app.py
```

Docker (recommended):
```bash
# Using start script (recommended)
./start.sh

# Or using Docker Compose directly
docker-compose up -d

# Or using pre-built images
docker-compose -f docker-compose-pull.yml up -d
```

### Building Docker Images

```bash
# Build image
docker build -t yt-dlp-api .

# Run container
docker run -p 8000:8000 -v $(pwd)/downloads:/app/downloads yt-dlp-api
```

## Architecture Overview

### Core Components

1. **FastAPI Service** (`main.py`):
   - RESTful API endpoints for video download, info retrieval, and format listing
   - Asynchronous task processing with ThreadPoolExecutor
   - SQLite database for task persistence
   - Cookie authentication support for YouTube
   - File management and safe filename generation
   - Comprehensive logging for debugging and monitoring

2. **Gradio Interface** (`gradio_app.py`):
   - Web UI with tabs for downloading, video info, and format listing
   - Communicates with FastAPI backend via HTTP requests
   - Docker-aware endpoint configuration
   - Real-time task status monitoring
   - Enhanced error handling and timeout management

3. **Database Layer**:
   - SQLite database (`data/tasks.db`) for persistent task storage
   - Task model with status tracking (pending/completed/failed)
   - Automatic initialization and task persistence

4. **Docker Infrastructure**:
   - Multi-stage Dockerfile with Python 3.9 base
   - Supervisor configuration for process management
   - Volume mounts for downloads and data persistence
   - Environment variable configuration for container detection
   - Enhanced logging configuration

### Key Features

1. **Asynchronous Processing**: Download tasks run asynchronously without blocking the API
2. **Task Management**: Persistent task tracking with status updates
3. **Cookie Authentication**: Support for YouTube bot detection bypass using cookies
4. **Format Selection**: Multiple video format support with quality options
5. **File Management**: Safe filename generation and file download endpoints
6. **Container Awareness**: Automatic endpoint detection in Docker environments
7. **Enhanced Error Handling**: Comprehensive error handling and logging
8. **Timeout Management**: Better timeout handling in web interface

### API Endpoints

- POST /download - Submit download task
- GET /task/{task_id} - Get task status
- GET /tasks - List all tasks
- GET /info?url={url} - Get video information
- GET /formats?url={url} - List available formats
- POST /upload-cookies - Upload cookies file
- GET /cookies-status - Check cookies status
- DELETE /cookies - Delete cookies file
- GET /download/{task_id}/file - Download completed video file
- DELETE /task/{task_id} - Delete a specific task and its associated file
- DELETE /tasks - Delete all tasks and their associated files

## Development Notes

1. The project uses Supervisor to manage both FastAPI and Gradio services in Docker
2. Cookie files are stored with 600 permissions for security
3. File names are sanitized to prevent filesystem issues
4. Both services share the same SQLite database and download directory
5. The web interface automatically detects container environments
6. All tasks are persisted in the database and loaded on startup
7. Safe filename generation prevents filesystem issues with special characters
8. Enhanced logging helps with debugging and monitoring
9. Better error handling improves user experience

## Testing

To test the API endpoints, you can use curl commands:

```bash
# Submit a download task
curl -X POST "http://localhost:8000/download" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID", "format": "best"}'

# Check task status
curl -X GET "http://localhost:8000/task/{task_id}"

# Get video information
curl -X GET "http://localhost:8000/info?url=https://www.youtube.com/watch?v=VIDEO_ID"

# List available formats
curl -X GET "http://localhost:8000/formats?url=https://www.youtube.com/watch?v=VIDEO_ID"

# Delete a specific task
curl -X DELETE "http://localhost:8000/task/{task_id}"

# Delete all tasks
curl -X DELETE "http://localhost:8000/tasks"
```

## Project Structure

```
.
├── main.py                 # FastAPI backend service
├── gradio_app.py           # Gradio frontend interface
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker image definition
├── docker-compose.yml      # Docker Compose configuration
├── docker-compose-pull.yml # Pre-built image configuration
├── supervisord.conf        # Supervisor process management
├── start.sh                # Startup script
├── data/                   # SQLite database storage
├── downloads/              # Downloaded video storage
├── cookies/                # Uploaded cookies files
├── CHANGELOG.md            # Project changelog
├── .gitignore              # Git ignore file
└── CLAUDE.md               # This file
```