# 自动Cookie管理功能使用指南

本文档介绍如何使用yt-dlp API的自动cookie管理功能，包括自动扫描浏览器、验证cookies、管理过期等完整功能。

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 基本使用

#### 自动设置cookies
```bash
# 使用命令行工具
python cookie_tool.py auto-setup

# 或使用API
curl -X POST "http://localhost:8000/cookies/auto-setup"
```

#### 查看cookie状态
```bash
# 使用命令行工具
python cookie_tool.py status

# 或使用API
curl -X GET "http://localhost:8000/cookies/status"
```

## 📋 功能特性

### 🔍 自动扫描浏览器
- **支持的浏览器**: Chrome, Firefox, Edge, Safari, Opera
- **跨平台**: Windows, macOS, Linux
- **智能检测**: 自动检测浏览器安装状态和运行状态
- **安全提取**: 无需关闭浏览器即可提取cookies

### ✅ Cookie验证系统
- **在线验证**: 使用真实YouTube链接验证cookie有效性
- **健康检查**: 检查cookie过期时间和使用状态
- **访问测试**: 测试对不同类型内容的访问权限
- **性能评估**: 评估cookie质量和功能完整性

### 🔄 智能管理
- **自动续期**: 提前检测并续期即将过期的cookies
- **清理机制**: 自动清理失效的cookie文件
- **备份系统**: 安全备份重要cookie文件
- **缓存优化**: 智能缓存验证结果

## 🛠️ API接口

### Cookie管理接口

#### 1. 自动设置Cookies
```http
POST /cookies/auto-setup
```

响应示例:
```json
{
  "success": true,
  "active_cookie": "cookies/youtube_chrome_auto_20240101_120000.txt",
  "scan_summary": {
    "total_browsers": 3,
    "successful_browsers": 2,
    "total_cookies": 15
  },
  "recommendations": ["✅ Cookie自动设置成功，可以正常使用"]
}
```

#### 2. 获取Cookie状态
```http
GET /cookies/status
```

响应示例:
```json
{
  "has_active_cookie": true,
  "cookie_file": "cookies/youtube_chrome_auto_20240101_120000.txt",
  "health_status": "healthy",
  "validation_result": {
    "valid": true,
    "video_title": "Example Video",
    "duration": 180,
    "uploader": "Example Channel",
    "premium_content": false,
    "age_restricted": false
  },
  "recommendation": "Cookie状态良好，可以正常使用"
}
```

#### 3. 刷新Cookies
```http
POST /cookies/refresh
```

#### 4. 环境诊断
```http
GET /cookies/diagnose
```

#### 5. 列出Cookie文件
```http
GET /cookies/list
```

#### 6. 验证指定Cookie
```http
POST /cookies/validate/{filename}
```

#### 7. 清理过期Cookies
```http
DELETE /cookies/cleanup
```

#### 8. 获取支持的浏览器
```http
GET /cookies/supported-browsers
```

## 📖 使用示例

### 1. 服务器部署自动化

```python
import asyncio
from cookie_manager import auto_cookie_manager

async def setup_server():
    # 1. 环境诊断
    diagnosis = await auto_cookie_manager.diagnose_environment()
    print(f"系统状态: {diagnosis}")

    # 2. 自动设置cookies
    setup_result = await auto_cookie_manager.auto_setup()

    if setup_result["success"]:
        print(f"✅ Cookie设置成功: {setup_result['active_cookie']}")

        # 3. 启动定期刷新任务
        while True:
            await asyncio.sleep(3600)  # 每小时检查一次
            await auto_cookie_manager.refresh_cookies()
    else:
        print(f"❌ Cookie设置失败: {setup_result.get('error')}")

# 运行设置
asyncio.run(setup_server())
```

### 2. 集成到下载流程

```python
from cookie_manager import get_cookie_status

async def download_with_auto_cookies(url):
    # 获取当前cookie状态
    cookie_status = await get_cookie_status()

    cookies = None
    if cookie_status.get("has_active_cookie"):
        cookies = cookie_status["cookie_file"]
        print(f"🍪 使用自动cookies: {cookies}")

    # 执行下载
    result = await download_video(url, cookies=cookies)
    return result
```

### 3. 监控和维护脚本

```bash
#!/bin/bash
# cookie_monitor.sh - Cookie监控脚本

# 检查cookie健康状态
STATUS=$(curl -s http://localhost:8000/cookies/status)
HEALTH=$(echo $STATUS | grep -o '"health_status":"[^"]*"' | cut -d'"' -f4)

case $HEALTH in
    "healthy")
        echo "✅ Cookie状态良好"
        ;;
    "warning")
        echo "⚠️ Cookie即将过期，准备刷新..."
        curl -X POST http://localhost:8000/cookies/refresh
        ;;
    "critical"|"invalid")
        echo "🚨 Cookie已失效，立即修复..."
        curl -X POST http://localhost:8000/cookies/auto-setup
        ;;
    *)
        echo "❓ 未知状态，执行诊断..."
        curl -X GET http://localhost:8000/cookies/diagnose
        ;;
esac
```

## 🔧 故障排除

### 常见问题

#### 1. 找不到浏览器
```bash
# 诊断环境问题
python cookie_tool.py diagnose

# 手动检测浏览器
python cookie_tool.py detect
```

**解决方案**:
- 确保浏览器已正确安装
- 检查浏览器数据目录权限
- 尝试关闭浏览器后重试

#### 2. 文件权限问题
```bash
# 检查权限
ls -la cookies/

# 修复权限
chmod 755 cookies/
chmod 600 cookies/*.txt
```

#### 3. Cookie验证失败
```bash
# 验证特定cookie文件
python cookie_tool.py validate cookies/your_cookie.txt --detailed

# 检查网络连接
curl -I https://www.youtube.com
```

#### 4. 浏览器文件锁定
```bash
# 诊断浏览器状态
python cookie_tool.py diagnose

# 关闭浏览器后重试
# Windows: taskkill /f /im chrome.exe
# macOS: killall Google\ Chrome
# Linux: pkill chrome
```

### 日志分析

启用详细日志:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 或在启动时设置环境变量
export PYTHONPATH=/path/to/project
export LOG_LEVEL=DEBUG
```

## 🏗️ 架构说明

### 模块结构
```
cookie_manager/
├── __init__.py          # 主要接口和便捷函数
├── config.py            # 配置管理
├── scanner.py          # 浏览器cookie扫描器
└── validator.py        # Cookie验证和管理器

utils/
├── __init__.py
└── browser_utils.py     # 浏览器工具函数

cookie_tool.py          # 命令行工具
```

### 主要组件

#### 1. BrowserCookieScanner
- 自动扫描浏览器安装
- 提取YouTube相关cookies
- 支持多种浏览器和数据格式

#### 2. CookieValidator
- 在线验证cookie有效性
- 健康状态评估
- 过期时间管理

#### 3. CookieManager
- Cookie生命周期管理
- 自动续期和清理
- 缓存和性能优化

#### 4. AutoCookieManager
- 统一管理接口
- 环境诊断
- 智能建议系统

## 📊 性能优化

### 1. 缓存策略
- 验证结果缓存5分钟
- 浏览器检测缓存1小时
- 文件状态缓存实时更新

### 2. 并发控制
- 最大并发浏览器数量: 3
- 超时控制: 扫描30秒，验证15秒
- 资源限制: 内存和CPU使用监控

### 3. 错误处理
- 自动重试机制
- 优雅降级处理
- 详细的错误日志

## 🔒 安全考虑

### 1. 文件权限
- Cookie文件权限: 600 (仅所有者可读写)
- 目录权限: 755 (所有者可读写，其他可读执行)
- 备份文件权限: 600

### 2. 数据保护
- 不收集用户数据
- 本地处理，不上传到外部服务
- 敏感信息过滤

### 3. 访问控制
- API访问控制 (生产环境建议添加认证)
- 文件系统访问限制
- 进程隔离

## 🔄 更新和维护

### 定期维护任务
```bash
# 每日: 检查cookie状态
python cookie_tool.py status

# 每周: 刷新cookies
python cookie_tool.py refresh

# 每月: 清理过期文件
python cookie_tool.py cleanup

# 季度: 完整环境诊断
python cookie_tool.py diagnose
```

### 自动化部署
```yaml
# 示例: GitHub Actions配置
name: Cookie Maintenance

on:
  schedule:
    - cron: '0 2 * * 0'  # 每周日凌晨2点

jobs:
  maintain-cookies:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Refresh cookies
        run: python cookie_tool.py refresh
      - name: Cleanup old files
        run: python cookie_tool.py cleanup
```

---

## 📞 支持

如果遇到问题或需要帮助，请：

1. 查看日志文件获取详细错误信息
2. 运行诊断命令检查环境状态
3. 参考故障排除章节
4. 查看项目Issue和文档

自动Cookie管理功能将为您的yt-dlp API服务提供稳定、可靠的认证支持！