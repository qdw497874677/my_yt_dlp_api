# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Subtitle Support**: Comprehensive subtitle download functionality
- **Multiple Subtitle Formats**: Support for SRT, VTT, ASS formats
- **Multi-language Subtitles**: Download subtitles in multiple languages simultaneously
- **Subtitle API Endpoints**:
  - `GET /subtitles` - List available subtitle languages
  - `GET /subtitle` - Download specific subtitle file
  - `POST /download-subtitles` - Async subtitle download (planned)
- **Cookie Authentication for Subtitles**: Support for private/restricted video subtitles
- **Enhanced Database Schema**: Added `task_type` and `subtitle_config` fields for subtitle tasks
- **Comprehensive Documentation**:
  - SUBTITLE_GUIDE.md - Complete subtitle usage guide
  - DATABASE_SCHEMA.md - Database schema and migration documentation
- **Performance Optimizations**: Database indexes for subtitle task queries
- **Improved Error Handling and logging throughout the application**
- **Better timeout handling in Gradio interface**
- **Enhanced Docker configuration with better log management**
- **Improved start script with better Docker Compose detection**

### Changed
- **Database Schema**: Extended tasks table to support subtitle downloads (v2.0)
- **API Documentation**: Updated README.md with subtitle endpoints and examples
- **Task Management**: Enhanced to handle both video and subtitle task types
- **Python Client**: Added subtitle download methods to example client
- **Web Interface**: Updated Gradio interface description for subtitle features
- **Optimized file name handling with better sanitization**
- **Enhanced Dockerfile with better layer organization**
- **Improved supervisor configuration with better logging**

### Fixed
- Connection error handling in Gradio interface
- File permission issues with cookies storage
- Duplicate directory creation issues

## [1.0.0] - 2025-09-05

### Added
- Initial release of yt-dlp API service
- FastAPI backend with RESTful endpoints
- Gradio web interface for easy video downloading
- Docker support with Supervisor process management
- SQLite database for task persistence
- Cookie authentication support for YouTube
- Comprehensive API documentation
