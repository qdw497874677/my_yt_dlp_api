<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

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
docker build -t yt-dlp-api-service .

# Run container
docker run -p 8000:8000 -v $(pwd)/downloads:/app/downloads yt-dlp-api-service
```

### Development Tools

```bash
# Cookie management and testing
python cookie_tool.py  # Interactive cookie management tool

# Run with specific port for local testing
python main.py --port 8001

# Run with debug mode
export PYTHONPATH=/app && python -m debugpy --listen 5678 --wait-for-client main.py

# Test cookie auto-detection
python -c "from cookie_manager import auto_setup_cookies; import asyncio; print(asyncio.run(auto_setup_cookies()))"
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

5. **Cookie Management System** (`cookie_manager/` and `utils/`):
   - Automatic browser cookie detection and extraction
   - Cross-platform browser support (Chrome, Firefox, Edge, Safari, Opera)
   - Cookie validation and management with expiration handling
   - Browser process detection and file locking checks
   - Multi-browser cookie file management and cleanup

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

### Cookie Management Endpoints

- POST /cookies/auto-setup - Automatically setup cookies from detected browsers
- GET /cookies/status - Get current cookie status and validation
- POST /cookies/refresh - Refresh cookies from browsers
- GET /cookies/diagnose - Diagnose environment and browser issues
- GET /cookies/list - List all available cookie files
- POST /cookies/validate/{filename} - Validate specific cookie file
- DELETE /cookies/cleanup - Clean up expired cookies
- GET /cookies/supported-browsers - Get list of supported browsers

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

### Architecture Details

**Task Management Flow:**
- Tasks are stored in SQLite with UUID generation
- Async processing using ThreadPoolExecutor for yt-dlp operations
- File cleanup on task deletion with comprehensive path resolution
- Automatic task resumption from database on restart

**Cookie System Architecture:**
- `cookie_manager/`: Core cookie management with detection, validation, and auto-refresh
- `utils/browser_utils.py`: Cross-platform browser detection and system integration
- Supports multiple cookie sources: browser detection, file upload, and manual paths
- Automatic cookie validation and expiration handling

**Container Considerations:**
- In Docker: API runs on port 8000, Gradio on 7860
- Host mapping: API on 18000, Gradio on 17860
- Volume mounts for persistent data across container restarts
- Environment variable `DOCKER_ENV` for container-aware behavior

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
├── cookie_tool.py          # Interactive cookie management tool
├── mcp_server.py           # MCP server integration
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker image definition
├── docker-compose.yml      # Docker Compose configuration
├── docker-compose-pull.yml # Pre-built image configuration
├── supervisord.conf        # Supervisor process management
├── start.sh                # Startup script
├── cookie_manager/         # Cookie management module
│   ├── __init__.py        # Main cookie manager interface
│   ├── config.py          # Configuration management
│   ├── scanner.py         # Browser cookie scanner
│   └── validator.py       # Cookie validation and management
├── utils/
│   └── browser_utils.py   # Cross-platform browser utilities
├── data/                   # SQLite database storage
├── downloads/              # Downloaded video storage
├── cookies/                # Uploaded cookies files
├── CHANGELOG.md            # Project changelog
├── .gitignore              # Git ignore file
└── CLAUDE.md               # This file
```

## Key Dependencies

**Core Services:**
- `fastapi==0.115.12` - Web framework for API
- `gradio==4.39.0` - Web interface framework
- `yt-dlp==2025.3.31` - Video downloading backend
- `uvicorn==0.115.6` - ASGI server

**Cookie Management:**
- `browser-cookie3==0.19.1` - Browser cookie extraction
- `psutil==6.1.1` - System process monitoring
- `aiohttp==3.11.12` - Async HTTP client

**Development:**
- `supervisor==4.2.5` - Process management (Docker)
- `requests==2.32.3` - HTTP client library