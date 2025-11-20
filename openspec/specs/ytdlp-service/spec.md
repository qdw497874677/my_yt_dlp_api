# ytdlp-service Specification

## Purpose
TBD - created by archiving change add-ytdlp-scheduled-update. Update Purpose after archive.
## Requirements
### Requirement: Scheduler Service Management
系统 SHALL 提供调度器服务管理功能，支持启动、停止和状态查询。

#### Scenario: Start scheduler service
- **WHEN** 管理员通过 API 发送启动请求
- **THEN** 系统启动调度器服务并返回成功状态

#### Scenario: Stop scheduler service
- **WHEN** 管理员通过 API 发送停止请求
- **THEN** 系统停止调度器服务并持久化当前状态

#### Scenario: Get scheduler status
- **WHEN** 用户查询调度器状态
- **THEN** 系统返回当前运行状态、下次执行时间等信息

### Requirement: yt-dlp Automatic Update Configuration
系统 SHALL 支持可配置的 yt-dlp 自动更新功能，包括开关控制和频率设置。

#### Scenario: Configure update schedule
- **WHEN** 管理员设置新的更新计划
- **THEN** 系统更新配置并重新调度更新任务

#### Scenario: Enable automatic updates
- **WHEN** 管理员启用自动更新
- **THEN** 系统开始按配置的计划执行 yt-dlp 更新

#### Scenario: Disable automatic updates
- **WHEN** 管理员禁用自动更新
- **THEN** 系统停止所有计划的更新任务

### Requirement: Scheduled Update Execution
系统 SHALL 按照配置的计划自动执行 yt-dlp 更新，并记录更新历史。

#### Scenario: Daily update execution
- **WHEN** 每天配置的时间到达（默认0点）
- **THEN** 系统自动执行 yt-dlp 更新并记录结果

#### Scenario: Update success handling
- **WHEN** yt-dlp 更新成功完成
- **THEN** 系统记录新版本信息和更新时间

#### Scenario: Update failure handling
- **WHEN** yt-dlp 更新失败
- **THEN** 系统记录错误信息并执行重试机制

### Requirement: Update Configuration Management
系统 SHALL 提供更新配置的查询和修改接口，支持动态调整更新参数。

#### Scenario: Get current configuration
- **WHEN** 用户查询当前更新配置
- **THEN** 系统返回更新开关状态、频率、下次执行时间等信息

#### Scenario: Update configuration
- **WHEN** 管理员修改更新配置
- **THEN** 系统验证配置参数的有效性并应用新配置

#### Scenario: Validate cron expression
- **WHEN** 管理员提供新的 cron 表达式
- **THEN** 系统验证表达式的有效性并返回验证结果

### Requirement: Update History Tracking
系统 SHALL 维护 yt-dlp 更新的历史记录，支持查询和监控。

#### Scenario: Record update attempt
- **WHEN** 系统执行 yt-dlp 更新
- **THEN** 系统记录更新时间、版本变化、执行状态等信息

#### Scenario: Query update history
- **WHEN** 用户查询更新历史
- **THEN** 系统返回按时间排序的更新记录列表

#### Scenario: Monitor update failures
- **WHEN** 系统检测到连续更新失败
- **THEN** 系统记录警告信息并可能暂停自动更新

### Requirement: 任务类型支持
系统 SHALL 支持多种任务类型，包括视频下载和字幕下载。

#### Scenario: 任务类型区分
- **WHEN** 创建新任务时
- **THEN** 系统根据请求类型设置 task_type 字段
- **AND** task_type 支持 'video' 和 'subtitle' 类型
- **AND** 不同类型任务使用相应的处理逻辑

#### Scenario: 任务列表过滤
- **WHEN** 查询任务列表时
- **THEN** 用户可按任务类型过滤任务
- **AND** 系统支持按 task_type、status 等字段筛选

### Requirement: 文件下载管理
文件下载接口 SHALL 支持不同类型任务的文件下载。

#### Scenario: 多文件任务下载
- **WHEN** 任务包含多个文件（如批量字幕）
- **THEN** GET /download/{task_id}/file 返回主要文件
- **AND** GET /download/{task_id}/files 返回所有文件列表
- **AND** GET /download/{task_id}/archive 返回包含所有文件的ZIP包

### Requirement: Enhanced Cookie Selection for Downloads
系统 SHALL 在视频下载过程中智能选择最佳的cookies来源，优先使用浏览器登录提取的cookies。

#### Scenario: Browser cookie priority selection
- **WHEN** 用户发起视频下载请求
- **THEN** 系统首先检查是否存在有效的浏览器登录cookies（30分钟内）
- **AND** 如果存在则优先使用浏览器登录cookies进行下载
- **AND** 如果不存在则回退到当前活跃的全局cookies
- **AND** 最后尝试自动检测的浏览器cookies

#### Scenario: Cookie validation for download
- **WHEN** 系统选择cookies用于下载
- **THEN** 系统验证cookies对YouTube服务的有效性
- **AND** 测试是否能访问需要登录的内容
- **AND** 记录cookies来源和验证结果用于调试

#### Scenario: Download failure fallback
- **WHEN** 使用优先选择的cookies下载失败
- **THEN** 系统尝试使用其他可用的cookies源
- **AND** 提供详细的失败原因和重试建议
- **AND** 记录所有尝试的cookies源和结果

### Requirement: Browser Session Integration with Download Flow
系统 SHALL 将浏览器登录会话与视频下载流程无缝集成。

#### Scenario: Session-aware downloads
- **WHEN** 用户通过浏览器登录后发起下载
- **THEN** 系统自动关联浏览器会话和下载任务
- **AND** 优先使用该会话提取的cookies进行下载
- **AND** 在下载完成后保持会话状态供后续使用

#### Scenario: Cookie extraction timing
- **WHEN** 浏览器登录状态检测成功
- **THEN** 系统自动提示用户提取cookies
- **AND** 提供一键提取和保存功能
- **AND** 验证提取的cookies并显示状态

#### Scenario: Download session optimization
- **WHEN** 系统检测到多个有效的浏览器会话
- **THEN** 系统选择最新活跃的会话cookies
- **AND** 根据YouTube访问验证结果选择最佳cookies
- **AND** 优化cookies选择策略以提高下载成功率

### Requirement: Enhanced Download Authentication Status
系统 SHALL 在下载过程中提供详细的认证状态信息。

#### Scenario: Authentication status display
- **WHEN** 下载任务使用cookies进行认证
- **THEN** 系统显示cookies来源（浏览器登录/自动检测/手动上传）
- **AND** 显示cookies的有效期和验证状态
- **AND** 提供认证失败的详细原因

#### Scenario: Download success metrics
- **WHEN** 下载任务完成时
- **THEN** 系统记录使用的cookies类型和成功率
- **AND** 统计不同cookies源的下载性能
- **AND** 用于优化后续的cookies选择策略

### Requirement: Cookie Management Integration
系统 SHALL 提供智能的cookie管理功能，支持多来源cookies的优先级管理和自动选择。

#### Scenario: Cookie source tracking
- **WHEN** 系统保存或使用cookies时
- **THEN** 系统记录cookies的来源（浏览器登录/自动检测/手动上传）
- **AND** 记录cookies的提取时间和验证状态
- **AND** 根据来源设置不同的优先级和过期策略

#### Scenario: Cookie cleanup optimization
- **WHEN** 系统执行cookies清理
- **THEN** 系统优先保留浏览器登录的新鲜cookies
- **AND** 根据下载成功率智能清理过期cookies
- **AND** 保持cookies多样性的同时优化存储空间

### Requirement: Enhanced Download API
系统 SHALL 提供增强的下载API，支持浏览器登录cookies的集成和详细的认证状态报告。

#### Scenario: Enhanced download request
- **WHEN** 客户端发送下载请求
- **THEN** 系统在下载流程中自动应用最佳cookies选择
- **AND** 返回使用的cookies来源和认证状态信息
- **AND** 提供cookies相关的详细错误信息

#### Scenario: Cookie status reporting
- **WHEN** 查询下载任务状态时
- **THEN** 系统返回认证使用的cookies信息
- **AND** 包括cookies类型、有效性、来源等详情
- **AND** 提供cookies相关的诊断信息

