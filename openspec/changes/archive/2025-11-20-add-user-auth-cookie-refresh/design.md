## Context
当前系统依赖用户手动从浏览器提取YouTube cookies，这种方式存在严重用户体验问题：
1. **技术门槛**：大多数用户不了解如何找到浏览器cookie文件
2. **重复操作**：YouTube cookies定期失效，需要用户重复手动操作
3. **服务中断**：cookie过期导致下载功能不可用，用户需要等待手动更新
4. **使用障碍**：复杂的操作流程阻碍了普通用户的使用

为了提供真正简单易用的YouTube视频下载服务，需要系统提供内置浏览器让用户直接登录YouTube，系统自动提取cookies。

## Goals / Non-Goals
- Goals:
  - 提供内置浏览器让用户安全登录YouTube
  - 自动提取登录后的YouTube cookies
  - 提供直观的Web界面指导用户完成登录流程
  - 与现有手动cookie功能并存，提供多种选择
  - 完全合规：用户真实登录，不存储密码
- Non-Goals:
  - 存储用户YouTube账号密码
  - 自动化登录流程
  - 绕过YouTube的安全机制
  - 多浏览器会话同时管理（初期阶段）

## Decisions
- Decision: 使用Selenium WebDriver启动Chrome浏览器实例
  - 理由：真实浏览器环境，用户熟悉操作，完全合规
  - 替代方案：HTTP客户端模拟登录（违反ToS，风险高）
- Decision: 通过调试端口提供浏览器访问
  - 理由：用户可以在自己的浏览器中访问登录页面
  - 替代方案：iframe嵌入（可能有跨域限制）
- Decision: 浏览器登录与手动cookie并存
  - 理由：给用户提供多种选择，照顾不同技术背景用户
  - 替代方案：完全替代手动方式（破坏性变更）

## Risks / Trade-offs
- 需要额外系统资源运行浏览器实例
- 多用户同时使用时资源消耗增加
- 需要管理浏览器进程的生命周期
- 浏览器版本兼容性问题

## Migration Plan
1. 添加Selenium依赖到requirements.txt
2. 实现浏览器会话管理模块
3. 在Gradio界面添加YouTube登录标签页
4. 添加浏览器管理API端点
5. 集成cookies提取到现有cookie管理器

## Open Questions
- 如何管理多个并发的浏览器会话？
- 浏览器会话的超时时间设置多久？
- 如何检测用户是否完成登录？
- 是否需要支持不同的浏览器类型？