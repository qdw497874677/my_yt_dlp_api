# YouTube Cookie 认证设置指南

## 问题描述
当使用 yt-dlp 下载 YouTube 视频时，可能会遇到以下错误：
```
ERROR: [youtube] 1GQnqGDw8uU: Sign in to confirm you're not a bot.
```

这是因为 YouTube 检测到自动化访问并要求身份验证。

## 解决方案

### 方法一：使用浏览器 Cookies（推荐）

#### 1. 导出浏览器 Cookies

**Chrome 浏览器：**
1. 安装 "Get cookies.txt" 扩展程序
2. 访问 YouTube 并登录您的账户
3. 点击扩展程序图标，然后点击 "Export" → "Export as Netscape HTTP Cookie File"
4. 将文件保存为 `cookies.txt`

**Firefox 浏览器：**
1. 安装 "cookies.txt" 扩展程序
2. 访问 YouTube 并登录您的账户
3. 点击扩展程序图标，然后点击 "Export" → "Export as Netscape HTTP Cookie File"
4. 将文件保存为 `cookies.txt`

#### 2. 使用 Cookies 文件

将 `cookies.txt` 文件放在项目目录中，然后在 Web 界面中输入文件路径：
```
/path/to/your/cookies.txt
```

### 方法二：直接使用浏览器 Cookies

如果您不想导出 cookies 文件，可以直接在 Web 界面中输入浏览器名称：

支持的浏览器名称：
- `chrome`
- `firefox` 
- `edge`
- `safari`
- `brave`
- `opera`

例如，如果您使用 Chrome 浏览器，只需在 "Cookies设置" 字段中输入：
```
chrome
```

### 方法三：使用命令行选项

如果您通过命令行使用 yt-dlp，可以使用以下选项：

```bash
# 使用 cookies 文件
yt-dlp --cookies /path/to/cookies.txt "VIDEO_URL"

# 使用浏览器 cookies
yt-dlp --cookies-from-browser chrome "VIDEO_URL"
```

## 在本项目中使用

### Web 界面使用

1. **Gradio 界面**：
   - 打开 http://localhost:7860
   - 在任意标签页的 "Cookies设置" 字段中输入：
     - cookies 文件路径（如：`/path/to/cookies.txt`）
     - 或浏览器名称（如：`chrome`）

2. **API 使用**：
   ```bash
   # 下载视频（使用 cookies 文件）
   curl -X POST "http://localhost:8000/download" \
        -H "Content-Type: application/json" \
        -d '{
          "url": "VIDEO_URL",
          "format": "best",
          "cookies": "/path/to/cookies.txt"
        }'

   # 下载视频（使用浏览器 cookies）
   curl -X POST "http://localhost:8000/download" \
        -H "Content-Type: application/json" \
        -d '{
          "url": "VIDEO_URL",
          "format": "best",
          "cookies": "chrome"
        }'
   ```

### Python 代码使用

```python
import requests

# 使用 cookies 文件
response = requests.post("http://localhost:8000/download", json={
    "url": "VIDEO_URL",
    "format": "best",
    "cookies": "/path/to/cookies.txt"
})

# 使用浏览器 cookies
response = requests.post("http://localhost:8000/download", json={
    "url": "VIDEO_URL",
    "format": "best", 
    "cookies": "chrome"
})
```

## 注意事项

1. **Cookie 有效期**：浏览器 cookies 通常会在一段时间后过期，如果下载失败，请重新导出 cookies

2. **隐私安全**：
   - 不要与他人分享您的 cookies 文件
   - cookies 包含您的登录信息，请妥善保管
   - 使用完成后建议删除 cookies 文件

3. **浏览器兼容性**：
   - 确保在使用 cookies 时对应的浏览器正在运行
   - 某些浏览器的隐私设置可能会阻止 cookies 访问

4. **Docker 环境**：
   - 如果在 Docker 容器中运行，请确保 cookies 文件路径正确
   - 建议将 cookies 文件挂载到容器中

## 常见问题

### Q: 仍然出现机器人验证错误？
A: 可能是 cookies 已过期，请重新导出 cookies 文件。

### Q: 找不到浏览器 cookies？
A: 确保浏览器正在运行，并且您已登录 YouTube 账户。

### Q: Docker 容器中无法访问浏览器 cookies？
A: Docker 容器无法访问主机浏览器的 cookies，请使用 cookies 文件方法。

### Q: cookies 文件路径错误？
A: 请使用绝对路径，如 `/Users/username/cookies.txt` 而不是 `./cookies.txt`。

## 其他解决方案

如果 cookies 方法仍然无法解决问题，您还可以尝试：

1. **使用代理**：
   ```bash
   yt-dlp --proxy "http://proxy:port" "VIDEO_URL"
   ```

2. **更改 User-Agent**：
   ```bash
   yt-dlp --user-agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" "VIDEO_URL"
   ```

3. **使用 VPN**：切换到不同的 IP 地址可能有助于避免检测。

通过以上方法，您应该能够成功解决 YouTube 的机器人验证问题并正常下载视频。
