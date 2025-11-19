# Change: Add yt-dlp Scheduled Update Service

## Why
需要提供自动化的 yt-dlp 更新功能，确保服务始终使用最新版本的 yt-dlp 以支持最新的网站和功能，同时允许用户灵活配置更新计划。

## What Changes
- 添加定时任务调度器服务
- 新增 yt-dlp 定时更新配置管理
- 实现可配置的更新频率和开关控制
- 添加更新状态监控和日志记录
- 提供更新配置的 REST API 接口

**Breaking Changes**: None

## Impact
- Affected specs: ytdlp-service (新增)
- Affected code: main.py (添加新路由和调度器)
- New dependencies: apscheduler 或类似调度库
- Database changes: 可能需要添加配置表