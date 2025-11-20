## ADDED Requirements

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