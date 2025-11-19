# Change: 添加异步字幕下载接口

## Why
当前字幕下载功能仅支持同步下载，无法处理批量字幕下载或长时间的字幕提取任务。用户需要异步字幕下载能力来支持批量处理和任务跟踪。

## What Changes
- 扩展现有任务系统支持字幕下载任务类型
- 添加新的字幕下载 API 端点
- 增强字幕格式和语言选择功能
- 添加字幕任务状态跟踪和历史记录

## Impact
- **Affected specs**: `video-download` (扩展任务类型)
- **Affected code**: `main.py` (API端点), 数据库模型, 任务处理逻辑
- **Breaking changes**: 无 - 保持现有字幕API兼容性