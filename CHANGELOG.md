# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Improved error handling and logging throughout the application
- Better timeout handling in Gradio interface
- Enhanced Docker configuration with better log management
- Improved start script with better Docker Compose detection

### Changed
- Optimized file name handling with better sanitization
- Updated README.md with clearer instructions and examples
- Enhanced Dockerfile with better layer organization
- Improved supervisor configuration with better logging

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
