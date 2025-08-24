# 服务器部署环境下的 Cookie 认证 API 使用指南

## 概述

当您的 yt-dlp API 服务部署在服务器上时，由于服务器环境通常没有图形界面和浏览器，直接使用浏览器 cookies 的方法不可行。本指南将详细介绍在服务器环境下如何通过 API 使用 cookie 认证。

## 服务器环境下的 Cookie 解决方案

### 方案一：上传 Cookies 文件（推荐）

#### 1. 在本地获取 Cookies 文件

**在您的本地电脑上执行以下步骤：**

**Chrome 浏览器：**
1. 安装 "Get cookies.txt" 扩展程序
2. 访问 YouTube 并登录您的账户
3. 点击扩展程序图标
4. 选择 "Export" → "Export as Netscape HTTP Cookie File"
5. 将文件保存为 `cookies.txt`

**Firefox 浏览器：**
1. 安装 "cookies.txt" 扩展程序
2. 访问 YouTube 并登录您的账户
3. 点击扩展程序图标
4. 选择 "Export" → "Export as Netscape HTTP Cookie File"
5. 将文件保存为 `cookies.txt`

#### 2. 将 Cookies 文件上传到服务器

**方法 A：通过 SCP 上传**
```bash
# 将本地 cookies.txt 文件上传到服务器
scp /path/to/local/cookies.txt user@your-server:/path/to/server/cookies.txt
```

**方法 B：通过 SFTP 上传**
```bash
# 使用 sftp 连接服务器
sftp user@your-server
# 上传文件
put /path/to/local/cookies.txt /path/to/server/cookies.txt
quit
```

**方法 C：通过 API 上传（如果您有文件上传功能）**
```bash
# 如果您的 API 支持文件上传，可以使用类似以下的接口
curl -X POST "http://your-server:8000/upload-cookies" \
     -F "file=@/path/to/local/cookies.txt"
```

#### 3. 通过 API 使用 Cookies 文件

**下载视频 API 调用：**
```bash
curl -X POST "http://your-server:8000/download" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://www.youtube.com/watch?v=VIDEO_ID",
       "format": "bestvideo+bestaudio/best",
       "output_path": "./downloads",
       "cookies": "/path/to/server/cookies.txt"
     }'
```

**获取视频信息 API 调用：**
```bash
curl -X GET "http://your-server:8000/info?url=https://www.youtube.com/watch?v=VIDEO_ID&cookies=/path/to/server/cookies.txt"
```

**获取格式列表 API 调用：**
```bash
curl -X GET "http://your-server:8000/formats?url=https://www.youtube.com/watch?v=VIDEO_ID&cookies=/path/to/server/cookies.txt"
```

### 方案二：程序化生成 Cookies 文件

如果您需要在服务器上自动更新 cookies，可以创建一个脚本来生成 cookies 文件：

#### 1. 创建 Cookie 生成脚本

**创建 `generate_cookies.py`：**
```python
import requests
import json
from datetime import datetime, timedelta

def generate_youtube_cookies():
    """
    生成 YouTube cookies 文件
    注意：这需要您提供有效的认证信息
    """
    # 这里需要根据实际情况调整
    # 可能需要使用 YouTube API 或其他认证方式
    
    # 示例：从某个认证服务获取 cookies
    auth_url = "https://accounts.google.com/o/oauth2/token"
    
    # 您的客户端凭据（需要从 Google Cloud Console 获取）
    client_id = "YOUR_CLIENT_ID"
    client_secret = "YOUR_CLIENT_SECRET"
    refresh_token = "YOUR_REFRESH_TOKEN"
    
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    
    try:
        response = requests.post(auth_url, data=data)
        response.raise_for_status()
        
        # 获取访问令牌
        access_token = response.json().get("access_token")
        
        # 使用访问令牌获取 YouTube cookies
        # 这里需要根据实际情况实现
        cookies = {
            "ACCESS_TOKEN": access_token,
            "LOGIN_INFO": "some_login_info",
            # 其他必要的 cookies
        }
        
        # 生成 cookies.txt 文件内容
        cookies_content = """# Netscape HTTP Cookie File
# This is a generated file

.youtube.com	TRUE	/	TRUE	${expires}	ACCESS_TOKEN	${access_token}
.youtube.com	TRUE	/	TRUE	${expires}	LOGIN_INFO	${login_info}
"""
        
        # 替换占位符
        expires = int((datetime.now() + timedelta(days=7)).timestamp())
        cookies_content = cookies_content.replace("${expires}", str(expires))
        cookies_content = cookies_content.replace("${access_token}", access_token)
        cookies_content = cookies_content.replace("${login_info}", "your_login_info")
        
        # 保存到文件
        with open("/path/to/server/cookies.txt", "w") as f:
            f.write(cookies_content)
            
        print("Cookies 文件生成成功")
        return True
        
    except Exception as e:
        print(f"生成 cookies 失败: {e}")
        return False

if __name__ == "__main__":
    generate_youtube_cookies()
```

#### 2. 设置定时任务自动更新 Cookies

**使用 crontab 设置定时任务：**
```bash
# 编辑 crontab
crontab -e

# 添加以下行，每天凌晨 2 点更新 cookies
0 2 * * * /usr/bin/python3 /path/to/generate_cookies.py
```

### 方案三：通过 API 端点管理 Cookies

您可以扩展 API 来支持 cookies 文件的管理：

#### 1. 添加 Cookies 管理端点

**在 `main.py` 中添加以下代码：**
```python
import shutil
from fastapi import UploadFile, File

# 添加到 FastAPI 应用中

@app.post("/upload-cookies")
async def upload_cookies(file: UploadFile = File(...)):
    """
    上传 cookies 文件
    """
    try:
        # 确保 cookies 目录存在
        cookies_dir = "cookies"
        os.makedirs(cookies_dir, exist_ok=True)
        
        # 保存文件
        file_path = os.path.join(cookies_dir, "cookies.txt")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {"status": "success", "message": "Cookies 文件上传成功", "path": file_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

@app.get("/cookies-status")
async def get_cookies_status():
    """
    检查 cookies 文件状态
    """
    cookies_path = "cookies/cookies.txt"
    if os.path.exists(cookies_path):
        file_stat = os.stat(cookies_path)
        return {
            "status": "success",
            "exists": True,
            "path": cookies_path,
            "size": file_stat.st_size,
            "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat()
        }
    else:
        return {
            "status": "success",
            "exists": False,
            "message": "Cookies 文件不存在"
        }
```

#### 2. 使用新的 Cookies 管理端点

**上传 Cookies 文件：**
```bash
curl -X POST "http://your-server:8000/upload-cookies" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@/path/to/local/cookies.txt"
```

**检查 Cookies 状态：**
```bash
curl -X GET "http://your-server:8000/cookies-status"
```

**使用上传的 Cookies：**
```bash
curl -X POST "http://your-server:8000/download" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://www.youtube.com/watch?v=VIDEO_ID",
       "format": "best",
       "cookies": "cookies/cookies.txt"
     }'
```

## 完整的 API 使用示例

### 1. Python 客户端示例

**创建 `youtube_downloader_client.py`：**
```python
import requests
import json
import time

class YouTubeDownloaderClient:
    def __init__(self, base_url, cookies_path=None):
        self.base_url = base_url.rstrip('/')
        self.cookies_path = cookies_path
    
    def upload_cookies(self, cookies_file_path):
        """上传 cookies 文件到服务器"""
        try:
            with open(cookies_file_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(f"{self.base_url}/upload-cookies", files=files)
                response.raise_for_status()
                result = response.json()
                self.cookies_path = result.get('path')
                print(f"Cookies 上传成功: {self.cookies_path}")
                return True
        except Exception as e:
            print(f"Cookies 上传失败: {e}")
            return False
    
    def check_cookies_status(self):
        """检查 cookies 状态"""
        try:
            response = requests.get(f"{self.base_url}/cookies-status")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"检查 cookies 状态失败: {e}")
            return None
    
    def download_video(self, url, format="best", output_path="./downloads"):
        """下载视频"""
        payload = {
            "url": url,
            "format": format,
            "output_path": output_path
        }
        
        if self.cookies_path:
            payload["cookies"] = self.cookies_path
        
        try:
            response = requests.post(f"{self.base_url}/download", json=payload)
            response.raise_for_status()
            result = response.json()
            task_id = result.get("task_id")
            
            if task_id:
                return self._wait_for_task(task_id)
            else:
                return None
        except Exception as e:
            print(f"下载失败: {e}")
            return None
    
    def get_video_info(self, url):
        """获取视频信息"""
        params = {"url": url}
        if self.cookies_path:
            params["cookies"] = self.cookies_path
        
        try:
            response = requests.get(f"{self.base_url}/info", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"获取视频信息失败: {e}")
            return None
    
    def _wait_for_task(self, task_id, timeout=300):
        """等待任务完成"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.base_url}/task/{task_id}")
                response.raise_for_status()
                data = response.json()
                task_data = data.get("data", {})
                status = task_data.get("status")
                
                if status == "completed":
                    return task_data
                elif status == "failed":
                    error = task_data.get("error", "未知错误")
                    print(f"任务失败: {error}")
                    return None
                
                time.sleep(2)
            except Exception as e:
                print(f"检查任务状态失败: {e}")
                return None
        
        print("任务超时")
        return None

# 使用示例
if __name__ == "__main__":
    # 初始化客户端
    client = YouTubeDownloaderClient("http://your-server:8000")
    
    # 上传 cookies 文件
    client.upload_cookies("/path/to/local/cookies.txt")
    
    # 检查 cookies 状态
    status = client.check_cookies_status()
    print(f"Cookies 状态: {status}")
    
    # 下载视频
    video_url = "https://www.youtube.com/watch?v=VIDEO_ID"
    result = client.download_video(video_url)
    
    if result:
        print("下载成功:", result)
    else:
        print("下载失败")
```

### 2. Shell 脚本示例

**创建 `download_with_cookies.sh`：**
```bash
#!/bin/bash

# 服务器配置
SERVER_URL="http://your-server:8000"
COOKIES_FILE="/path/to/server/cookies.txt"
VIDEO_URL="$1"
FORMAT="${2:-best}"

if [ -z "$VIDEO_URL" ]; then
    echo "Usage: $0 <video_url> [format]"
    exit 1
fi

# 检查 cookies 文件是否存在
if [ ! -f "$COOKIES_FILE" ]; then
    echo "Error: Cookies file not found: $COOKIES_FILE"
    exit 1
fi

echo "Starting download..."
echo "Video URL: $VIDEO_URL"
echo "Format: $FORMAT"
echo "Cookies: $COOKIES_FILE"

# 提交下载任务
response=$(curl -s -X POST "$SERVER_URL/download" \
    -H "Content-Type: application/json" \
    -d "{
        \"url\": \"$VIDEO_URL\",
        \"format\": \"$FORMAT\",
        \"cookies\": \"$COOKIES_FILE\"
    }")

# 解析响应获取任务ID
task_id=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin)['task_id'])")

if [ -z "$task_id" ]; then
    echo "Error: Failed to get task ID"
    echo "Response: $response"
    exit 1
fi

echo "Task ID: $task_id"

# 等待任务完成
while true; do
    status_response=$(curl -s "$SERVER_URL/task/$task_id")
    status=$(echo "$status_response" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['status'])")
    
    echo "Task status: $status"
    
    if [ "$status" = "completed" ]; then
        echo "Download completed successfully!"
        break
    elif [ "$status" = "failed" ]; then
        error=$(echo "$status_response" | python3 -c "import sys, json; print(json.load(sys.stdin)['data'].get('error', 'Unknown error'))")
        echo "Download failed: $error"
        exit 1
    fi
    
    sleep 2
done

# 下载文件
echo "Downloading video file..."
curl -s "$SERVER_URL/download/$task_id/file" -o "downloaded_video_$task_id.mp4"

echo "Download completed: downloaded_video_$task_id.mp4"
```

## 部署建议

### 1. 服务器配置

**确保服务器有足够的权限：**
```bash
# 创建 cookies 目录并设置权限
sudo mkdir -p /opt/yt-dlp-api/cookies
sudo chown -R $USER:$USER /opt/yt-dlp-api/cookies
chmod 755 /opt/yt-dlp-api/cookies
```

### 2. 安全考虑

**限制 cookies 文件访问权限：**
```bash
# 设置 cookies 文件为仅当前用户可读写
chmod 600 /path/to/cookies.txt
```

**使用 HTTPS 保护 API：**
```bash
# 建议使用 Nginx 反向代理并启用 HTTPS
server {
    listen 443 ssl;
    server_name your-server.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. 监控和日志

**设置日志监控：**
```bash
# 监控 API 日志
tail -f /var/log/yt-dlp-api.log

# 监控 cookies 文件变化
inotifywait -m /path/to/cookies.txt
```

## 故障排除

### 常见问题

1. **Cookies 文件路径错误**
   ```bash
   # 检查文件是否存在
   ls -la /path/to/cookies.txt
   
   # 使用绝对路径
   /home/user/cookies.txt  # 正确
   ./cookies.txt          # 可能错误
   ```

2. **Cookies 过期**
   ```bash
   # 检查文件修改时间
   stat /path/to/cookies.txt
   
   # 如果超过 7 天，建议重新生成
   ```

3. **权限问题**
   ```bash
   # 检查文件权限
   ls -la /path/to/cookies.txt
   
   # 设置正确权限
   chmod 644 /path/to/cookies.txt
   ```

4. **API 连接问题**
   ```bash
   # 测试 API 连接
   curl -X GET "http://your-server:8000/"
   
   # 检查防火墙设置
   sudo ufw status
   ```

通过以上方法，您可以在服务器环境下成功使用 cookie 认证来解决 YouTube 的机器人验证问题。
