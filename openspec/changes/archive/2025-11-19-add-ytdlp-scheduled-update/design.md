## Context
当前项目已经具备手动更新 yt-dlp 的功能，但缺乏自动化更新机制。用户需要定期手动更新以保持 yt-dlp 与最新视频网站的兼容性。

## Goals / Non-Goals
- **Goals**:
  - 提供可配置的自动更新服务
  - 确保更新的可靠性和可监控性
  - 最小化对现有服务的影响
- **Non-Goals**:
  - 支持多种更新源（仅支持 PyPI/ GitHub）
  - 复杂的调度策略（仅支持 cron 表达式）

## Decisions
- **Decision**: 使用 APScheduler 作为调度器
  - **Why**: 与 FastAPI 集成良好，支持持久化存储，社区活跃
  - **Alternatives considered**:
    - Celery: 过于复杂，需要额外的 broker
    - 内置 asyncio.sleep: 不支持持久化，功能有限

- **Decision**: 使用 SQLite 存储配置和历史
  - **Why**: 与现有数据库一致，无需额外依赖
  - **Alternatives considered**:
    - 配置文件: 不支持动态修改
    - Redis: 需要额外依赖

- **Decision**: 集成到现有 FastAPI 应用中
  - **Why**: 简化部署，共享现有资源
  - **Alternatives considered**:
    - 独立服务: 增加部署复杂性
    - 系统服务: 跨平台兼容性问题

## Risks / Trade-offs
- **更新失败风险** → 实现重试机制和错误监控
- **服务重启风险** → 持久化调度器状态，重启后自动恢复
- **并发更新风险** → 添加更新锁，防止同时执行多个更新任务
- **依赖冲突风险** → 在独立进程中执行更新，避免影响主服务

## Migration Plan
1. 数据库迁移：添加 scheduler_config 和 update_history 表
2. 代码迁移：集成调度器到现有 FastAPI 应用
3. 配置迁移：设置默认配置（每天0点更新，默认关闭）
4. 部署迁移：更新 Docker 镜像和部署脚本

## Open Questions
- 是否需要支持更新通知功能？
- 是否需要支持灰度更新（先更新到测试环境）？
- 如何处理更新过程中进行中的下载任务？