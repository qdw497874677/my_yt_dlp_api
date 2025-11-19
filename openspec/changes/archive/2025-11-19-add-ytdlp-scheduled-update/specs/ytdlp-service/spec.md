## ADDED Requirements

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