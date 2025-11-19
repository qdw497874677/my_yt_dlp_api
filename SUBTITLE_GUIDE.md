# 字幕下载功能使用指南

## 功能概述

yt-dlp API 服务提供完整的字幕下载功能，支持多种格式和语言的字幕处理，包括同步下载和异步任务处理。

### 核心特性
- **多格式支持**: SRT、VTT、ASS、SSA
- **多语言支持**: 支持视频的可用字幕语言
- **自动选择**: 智能选择最佳可用字幕（人工字幕优先）
- **异步处理**: 后台任务处理，支持批量下载
- **Cookie认证**: 绕过YouTube限制访问私有视频字幕
- **任务跟踪**: 完整的任务状态管理和进度监控

## API 接口详细说明

### 1. 获取可用字幕语言

列出指定视频的所有可用字幕语言和格式。

**请求格式:**
```http
GET /subtitles?url={video_url}&cookies={cookies_path}
```

**参数说明:**
- `url` (必需): YouTube视频URL
- `cookies` (可选): Cookie文件路径或浏览器名称

**响应格式:**
```json
{
    "status": "success",
    "data": {
        "subtitles": {
            "en": {
                "name": "English",
                "code": "en",
                "formats": ["srt", "vtt"]
            },
            "zh": {
                "name": "Chinese",
                "code": "zh",
                "formats": ["srt", "vtt"]
            }
        },
        "automatic_captions": {
            "en": {
                "name": "English (auto-generated)",
                "code": "en",
                "formats": ["srt", "vtt"]
            }
        }
    }
}
```

**字段说明:**
- `subtitles`: 人工字幕列表
- `automatic_captions`: 自动生成的字幕
- `name`: 语言显示名称
- `code`: ISO 639-1 语言代码
- `formats`: 支持的格式列表

### 2. 下载指定字幕

直接下载指定语言和格式的字幕文件。

**请求格式:**
```http
GET /subtitle?url={video_url}&language={lang}&format={format}&cookies={cookies_path}
```

**参数说明:**
- `url` (必需): YouTube视频URL
- `language` (必需): 语言代码（如 'en', 'zh', 'es'）
- `format` (可选): 字幕格式，默认 'srt'，支持 'srt', 'vtt', 'ass', 'ssa'
- `cookies` (可选): Cookie文件路径或浏览器名称

**响应:**
- 成功: 直接返回字幕文件流
- 失败: JSON格式的错误信息

**示例:**
```bash
# 下载英文字幕（SRT格式）
curl -L "http://localhost:8000/subtitle?url=https://www.youtube.com/watch?v=VIDEO_ID&language=en&format=srt" -o subtitle.srt

# 使用Cookie认证下载字幕
curl -L "http://localhost:8000/subtitle?url=https://www.youtube.com/watch?v=VIDEO_ID&language=zh&format=vtt&cookies=chrome" -o subtitle.vtt
```

### 3. 异步字幕下载（规划中功能）

提交后台字幕下载任务，支持批量语言下载和任务跟踪。

**请求格式:**
```http
POST /download-subtitles
```

**请求体:**
```json
{
    "url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "output_path": "./downloads",
    "languages": ["en", "zh", "es"],
    "auto_select": true,
    "subtitle_format": "srt",
    "cookies": "cookies/cookies.txt"
}
```

**参数说明:**
- `url` (必需): YouTube视频URL
- `output_path` (可选): 输出目录，默认 "./downloads"
- `languages` (可选): 语言代码列表，默认 ["en"]
- `auto_select` (可选): 自动选择最佳字幕，默认 true
- `subtitle_format` (可选): 字幕格式，默认 "srt"
- `cookies` (可选): Cookie文件路径或浏览器名称

**响应:**
```json
{
    "status": "success",
    "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**任务状态查询:**
```http
GET /task/{task_id}
```

**字幕任务状态示例:**
```json
{
    "status": "success",
    "data": {
        "id": "task_id",
        "url": "https://www.youtube.com/watch?v=VIDEO_ID",
        "status": "completed",
        "task_type": "subtitle",
        "subtitle_config": {
            "languages": ["en", "zh"],
            "format": "srt",
            "auto_select": true
        },
        "result": {
            "downloaded_files": [
                {
                    "language": "en",
                    "path": "./downloads/video_en.srt",
                    "size": 24576
                },
                {
                    "language": "zh",
                    "path": "./downloads/video_zh.srt",
                    "size": 18432
                }
            ],
            "total_files": 2
        }
    }
}
```

## 使用示例

### Python 客户端示例

```python
import requests

class SubtitleClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url

    def get_available_subtitles(self, video_url, cookies_path=None):
        """获取可用字幕列表"""
        params = {"url": video_url}
        if cookies_path:
            params["cookies"] = cookies_path

        response = requests.get(f"{self.base_url}/subtitles", params=params)
        response.raise_for_status()
        return response.json()['data']

    def download_subtitle(self, video_url, language, format="srt", cookies_path=None):
        """下载单个字幕文件"""
        params = {
            "url": video_url,
            "language": language,
            "format": format
        }
        if cookies_path:
            params["cookies"] = cookies_path

        response = requests.get(f"{self.base_url}/subtitle", params=params)
        response.raise_for_status()
        return response.content

    def download_subtitles_async(self, video_url, languages, output_path="./downloads",
                                auto_select=True, format="srt", cookies_path=None):
        """异步下载多个字幕"""
        payload = {
            "url": video_url,
            "languages": languages,
            "output_path": output_path,
            "auto_select": auto_select,
            "subtitle_format": format
        }
        if cookies_path:
            payload["cookies"] = cookies_path

        response = requests.post(f"{self.base_url}/download-subtitles", json=payload)
        response.raise_for_status()
        return response.json()['task_id']

# 使用示例
client = SubtitleClient()

video_url = "https://www.youtube.com/watch?v=VIDEO_ID"

# 1. 获取可用字幕
subtitles = client.get_available_subtitles(video_url)
print("可用字幕:", subtitles)

# 2. 下载英文字幕
subtitle_content = client.download_subtitle(video_url, "en", "srt")
with open("subtitle.srt", "wb") as f:
    f.write(subtitle_content)
print("字幕下载完成: subtitle.srt")

# 3. 批量下载字幕（异步）
task_id = client.download_subtitles_async(
    video_url,
    languages=["en", "zh", "es"],
    auto_select=True,
    format="srt"
)
print(f"异步字幕下载任务提交: {task_id}")
```

### Shell 脚本示例

```bash
#!/bin/bash

# 配置
SERVER_URL="http://localhost:8000"
VIDEO_URL="https://www.youtube.com/watch?v=VIDEO_ID"

# 1. 获取可用字幕
echo "获取可用字幕..."
subtitles=$(curl -s "$SERVER_URL/subtitles?url=$VIDEO_URL")
echo "可用字幕: $subtitles"

# 2. 下载英文字幕
echo "下载英文字幕..."
curl -L "$SERVER_URL/subtitle?url=$VIDEO_URL&language=en&format=srt" -o "english_subtitle.srt"

# 3. 下载中文字幕
echo "下载中文字幕..."
curl -L "$SERVER_URL/subtitle?url=$VIDEO_URL&language=zh&format=vtt" -o "chinese_subtitle.vtt"

echo "字幕下载完成!"
```

## Web 界面使用

### Gradio 界面操作步骤

1. **打开界面**: 访问 http://localhost:7860 (本地) 或 http://localhost:17860 (Docker)

2. **导航到字幕下载页面**: 选择 "Subtitle Download" 标签页

3. **输入视频信息**:
   - 在 "Video URL" 字段输入 YouTube 视频链接
   - 选择所需的字幕语言（可多选）
   - 选择字幕格式（SRT、VTT、ASS）

4. **配置选项**:
   - 启用 "Auto Select Best Subtitles" 自动选择最佳字幕
   - 设置输出目录
   - 配置 Cookie 认证（如需要）

5. **提交下载任务**: 点击 "Download Subtitles" 按钮

6. **监控进度**: 查看实时任务状态和下载进度

7. **下载文件**: 任务完成后，直接下载生成的字幕文件

## 格式说明

### SRT (SubRip Subtitle)
- **扩展名**: .srt
- **特点**: 最常见的字幕格式，兼容性好
- **用途**: 适合大多数播放器和编辑软件
- **时间格式**: `00:00:00,000 --> 00:00:05,000`

### VTT (WebVTT)
- **扩展名**: .vtt
- **特点**: Web标准字幕格式，支持HTML5视频
- **用途**: 网页视频播放，支持样式定义
- **时间格式**: `00:00:00.000 --> 00:00:05.000`

### ASS (Advanced SubStation Alpha)
- **扩展名**: .ass
- **特点**: 高级字幕格式，支持复杂样式和动画
- **用途**: 动漫字幕，高级视频编辑
- **特性**: 支持字体、颜色、位置、特效

## 语言代码

### 常用语言代码
- `en` - English (英语)
- `zh` - Chinese (中文)
- `es` - Spanish (西班牙语)
- `fr` - French (法语)
- `de` - German (德语)
- `ja` - Japanese (日语)
- `ko` - Korean (韩语)
- `ru` - Russian (俄语)
- `ar` - Arabic (阿拉伯语)
- `hi` - Hindi (印地语)

### 语言代码格式
- 使用 ISO 639-1 标准的2字母语言代码
- 支持区域特定代码，如 `zh-CN`, `en-US`
- 大多数YouTube视频使用标准语言代码

## Cookie 认证

### 何时需要 Cookie
- 私有或受限访问的视频
- 需要登录才能访问的内容
- 避免YouTube机器人检测

### Cookie 设置方法

#### 方法 1: 上传 Cookie 文件
```bash
# 上传 cookies.txt 文件
curl -X POST "http://localhost:8000/upload-cookies" \
     -F "file=@/path/to/cookies.txt"
```

#### 方法 2: 使用浏览器 Cookies
```json
{
    "url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "languages": ["en"],
    "cookies": "chrome"  // 或 "firefox", "edge", "safari"
}
```

### 支持的浏览器
- Chrome / Chromium
- Firefox
- Edge
- Safari
- Brave
- Opera

## 错误处理

### 常见错误及解决方案

#### 404 错误: 视频不存在
```
{"detail": "Video not found"}
```
**解决方案**: 检查视频URL是否正确，视频是否已被删除

#### 400 错误: 参数无效
```
{"detail": "Invalid language code"}
```
**解决方案**: 使用有效的ISO 639-1语言代码

#### 404 错误: 字幕不可用
```
{"detail": "No subtitles available for this video"}
```
**解决方案**: 该视频没有字幕，尝试其他视频或自动字幕

#### 500 错误: 服务器内部错误
```
{"detail": "Failed to extract subtitles"}
```
**解决方案**:
1. 检查网络连接
2. 尝试使用Cookie认证
3. 稍后重试

### 错误处理代码示例

```python
def safe_subtitle_download(client, video_url, language):
    try:
        # 检查字幕可用性
        subtitles = client.get_available_subtitles(video_url)

        if language not in subtitles.get('subtitles', {}):
            if language in subtitles.get('automatic_captions', {}):
                print(f"警告: 只有自动字幕可用 ({language})")
            else:
                raise Exception(f"语言 {language} 的字幕不可用")

        # 下载字幕
        content = client.download_subtitle(video_url, language)
        return content

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            raise Exception("视频不存在或字幕不可用")
        elif e.response.status_code == 400:
            raise Exception("请求参数错误")
        else:
            raise Exception(f"下载失败: {e}")
    except Exception as e:
        raise Exception(f"字幕下载错误: {e}")
```

## 性能优化

### 批量下载建议
1. **使用异步接口**: 对于多语言字幕，使用异步下载API
2. **合理设置超时**: 网络不稳定时设置适当的超时时间
3. **并发控制**: 避免同时提交过多任务

### 缓存策略
- 字幕文件通常较小，可以缓存重复使用
- 字幕信息查询结果可以缓存一段时间（如30分钟）

### 网络优化
- 使用稳定的网络连接
- 考虑使用代理服务器（如果网络受限）
- 设置合适的重试机制

## 法律和版权须知

### 使用限制
1. **版权保护**: 下载的字幕受版权法保护
2. **合理使用**: 仅用于个人学习和研究
3. **禁止分发**: 不要分发受版权保护的字幕文件
4. **商业用途**: 商业使用需要获得版权方许可

### 最佳实践
- 尊重内容创作者的版权
- 不要批量下载用于商业目的
- 遵守相关法律法规
- 注意个人隐私和敏感信息

## 故障排除

### 常见问题

**Q: 为什么有些视频没有字幕？**
A: 不是所有视频都有字幕，特别是用户上传的内容可能缺少字幕。

**Q: 字幕显示乱码怎么办？**
A: 确保字幕文件使用UTF-8编码，或者尝试不同的字幕格式。

**Q: 自动字幕质量差怎么办？**
A: 自动字幕由机器生成，质量可能不如人工字幕。可以尝试其他语言的字幕。

**Q: 下载速度慢怎么办？**
A: 检查网络连接，尝试使用不同的服务器位置，或者选择较小的字幕格式。

**Q: Cookie 认证失败怎么办？**
A: 确保Cookie文件有效且未过期，或者尝试不同的浏览器Cookie。

### 技术支持

如果遇到技术问题，可以：
1. 查看服务器日志
2. 检查API响应状态码和错误信息
3. 验证视频URL的有效性
4. 测试网络连接
5. 尝试使用Cookie认证

## 更新日志

### 最新版本
- 添加异步字幕下载功能
- 支持批量语言下载
- 改进错误处理和用户反馈
- 增强Cookie认证支持

### 计划中的功能
- 字幕格式转换
- 字幕质量检测
- 字幕内容搜索
- 多语言字幕合并
- 字幕时间轴调整

---

*本文档最后更新时间: 2025-01-19*