## ADDED Requirements

### Requirement: 异步字幕下载任务
系统 SHALL 支持异步字幕下载任务，允许用户提交字幕下载请求并跟踪任务状态。

#### Scenario: 提交字幕下载任务
- **WHEN** 用户通过 POST /download-subtitles 提交字幕下载请求
- **THEN** 系统创建字幕下载任务并返回任务ID
- **AND** 任务状态设置为 "pending"
- **AND** 系统在后台异步处理字幕下载

#### Scenario: 查询字幕下载任务状态
- **WHEN** 用户通过 GET /task/{task_id} 查询字幕下载任务
- **THEN** 系统返回任务状态、进度和结果信息
- **AND** 任务状态包含 pending/completed/failed

#### Scenario: 下载完成的字幕文件
- **WHEN** 字幕下载任务完成
- **THEN** 用户可通过 GET /download/{task_id}/file 下载字幕文件
- **AND** 系统提供正确的文件名和MIME类型

### Requirement: 批量字幕下载
系统 SHALL 支持批量下载多种语言的字幕。

#### Scenario: 批量字幕下载请求
- **WHEN** 用户指定多个语言代码进行字幕下载
- **THEN** 系统为每个语言创建独立的字幕文件
- **AND** 所有文件组织在任务目录中
- **AND** 用户可下载包含所有字幕的ZIP文件

#### Scenario: 字幕语言自动检测
- **WHEN** 用户未指定特定语言
- **THEN** 系统自动下载可用语言的字幕
- **AND** 优先选择人工字幕而非自动字幕

### Requirement: 字幕格式支持
系统 SHALL 支持多种字幕格式的下载和转换。

#### Scenario: 多格式字幕下载
- **WHEN** 用户指定字幕格式（srt、vtt、ass等）
- **THEN** 系统下载指定格式的字幕文件
- **AND** 在格式不可用时提供替代选项

#### Scenario: 字幕格式转换
- **WHEN** 请求的字幕格式与源格式不同
- **THEN** 系统自动转换为请求的格式
- **AND** 保持时间轴和文本内容准确性

## ADDED Requirements

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