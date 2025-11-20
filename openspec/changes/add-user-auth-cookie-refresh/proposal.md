# Change: add-youtube-browser-login

## Why
当前系统的YouTube cookie依赖手动从浏览器提取，存在以下问题：
1. **手动操作繁琐**：用户需要手动找到浏览器cookie文件并上传
2. **自动过期问题**：YouTube cookies会定期失效，需要重复手动操作
3. **技术门槛高**：普通用户不熟悉cookie文件位置和提取方法
4. **服务中断频繁**：cookie过期导致下载功能不可用，用户体验差

添加内置浏览器YouTube登录功能，让用户能够：
- 通过系统启动的浏览器窗口安全登录YouTube
- 系统自动提取登录后的YouTube cookies
- 提供简单直观的Web界面操作流程
- 完全合规：用户真实登录，不违反YouTube服务条款

## What Changes
- 添加浏览器会话管理系统（启动/监控/停止浏览器）
- 实现YouTube登录Web界面（基于Gradio）
- 添加自动cookie提取和存储机制
- 实现浏览器状态监控和用户指导
- 提供登录状态检测和cookies验证
- **BREAKING**: 无，与现有手动cookie功能并存

## Impact
- Affected specs: ytdlp-service (需要添加YouTube浏览器登录功能)
- Affected code: gradio_app.py (添加登录界面), main.py (添加浏览器管理API), cookie_manager模块 (支持浏览器提取的cookies)
- New capabilities: youtube-browser-login, browser-session-management