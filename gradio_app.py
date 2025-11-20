import gradio as gr
import requests
import os
import time
import json
import logging
import threading
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API配置
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
# 在Docker容器中，使用容器服务名
if os.getenv("DOCKER_ENV"):
    API_BASE_URL = "http://yt-dlp-api:8000"

# 设置环境变量以避免Gradio的API文档错误
os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"

# YouTube登录相关函数
def start_browser_session():
    """启动浏览器登录会话"""
    try:
        logger.info("启动YouTube浏览器登录会话...")
        response = requests.post(f"{API_BASE_URL}/browser/session/start", timeout=30)
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            session_id = result.get("session_id")
            debug_url = result.get("debug_url")
            instructions = result.get("instructions")

            message = f"""✅ 浏览器会话已启动！

📍 访问地址: {debug_url}
📝 会话ID: {session_id}

💡 使用说明:
{instructions}

⚠️ 重要提示:
- 请在新打开的浏览器窗口中完成YouTube登录
- 登录完成后回到本页面点击"提取Cookies"按钮
- 会话将在30分钟后自动过期"""

            logger.info(f"浏览器会话启动成功: {session_id}")
            return message, gr.update(visible=True), gr.update(visible=True), session_id
        else:
            error_msg = result.get("error", "未知错误")
            logger.error(f"启动浏览器会话失败: {error_msg}")
            return f"❌ 启动失败: {error_msg}", gr.update(visible=False), gr.update(visible=False), None

    except requests.exceptions.ConnectionError:
        error_msg = "❌ 连接失败: 无法连接到API服务，请检查服务是否运行"
        logger.error(error_msg)
        return error_msg, gr.update(visible=False), gr.update(visible=False), None
    except requests.exceptions.Timeout:
        error_msg = "❌ 请求超时: 启动浏览器会话超时，请重试"
        logger.error(error_msg)
        return error_msg, gr.update(visible=False), gr.update(visible=False), None
    except Exception as e:
        error_msg = f"❌ 启动失败: {str(e)}"
        logger.error(error_msg)
        return error_msg, gr.update(visible=False), gr.update(visible=False), None

def check_session_status(session_id):
    """检查会话状态"""
    if not session_id:
        return "❌ 没有活跃的浏览器会话"

    try:
        response = requests.get(f"{API_BASE_URL}/browser/session/{session_id}/status", timeout=10)
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            status = result.get("status")
            youtube_logged_in = result.get("youtube_logged_in", False)
            cookies_extracted = result.get("cookies_extracted", False)
            resource_info = result.get("resource_info", {})
            error_message = result.get("error_message")

            # 状态图标映射
            status_icons = {
                "initializing": "🔄 初始化中",
                "ready": "🟢 准备就绪",
                "login_complete": "✅ 登录完成",
                "extracting": "⏳ 提取Cookies中",
                "completed": "✨ 完成",
                "error": "❌ 错误"
            }

            status_text = status_icons.get(status, f"📋 {status}")

            info_lines = [
                f"📊 会话状态: {status_text}",
                f"🔐 YouTube登录: {'✅ 已登录' if youtube_logged_in else '❌ 未登录'}",
                f"🍪 Cookies提取: {'✅ 已提取' if cookies_extracted else '❌ 未提取'}",
                f"🆔 会话ID: {session_id}"
            ]

            if error_message:
                info_lines.append(f"⚠️ 错误信息: {error_message}")

            # 添加资源使用信息
            if resource_info:
                if "memory_mb" in resource_info:
                    info_lines.append(f"💾 内存使用: {resource_info['memory_mb']:.1f} MB")
                if "cpu_percent" in resource_info:
                    info_lines.append(f"🖥️ CPU使用: {resource_info['cpu_percent']:.1f}%")

            # 添加操作建议
            if status == "ready" and not youtube_logged_in:
                info_lines.append("\n💡 建议: 请在浏览器中完成YouTube登录")
            elif status == "login_complete" and not cookies_extracted:
                info_lines.append("\n💡 建议: 请点击'提取Cookies'按钮")
            elif status == "completed":
                info_lines.append("\n✅ 完成: Cookies已成功提取，可以开始下载视频了")

            return "\n".join(info_lines)
        else:
            error_msg = result.get("error", "未知错误")
            return f"❌ 获取状态失败: {error_msg}"

    except Exception as e:
        return f"❌ 检查状态失败: {str(e)}"

def extract_browser_cookies(session_id):
    """提取浏览器Cookies"""
    if not session_id:
        return "❌ 没有活跃的浏览器会话"

    try:
        logger.info(f"提取会话 {session_id} 的cookies...")
        response = requests.post(f"{API_BASE_URL}/browser/session/{session_id}/extract-cookies", timeout=30)
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            cookie_count = result.get("cookie_count", 0)
            net_cookies = result.get("netscape_cookies", "")

            # 保存cookies到文件
            cookie_filename = f"youtube_cookies_{session_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            cookie_path = os.path.join("./cookies", cookie_filename)

            # 确保cookies目录存在
            os.makedirs("./cookies", exist_ok=True)

            with open(cookie_path, 'w', encoding='utf-8') as f:
                f.write(net_cookies)

            success_message = f"""🎉 Cookies提取成功！

📊 提取统计:
- Cookie数量: {cookie_count}
- 保存位置: {cookie_path}
- 文件大小: {len(net_cookies)} 字符

✨ 使用方法:
1. 在下载视频时，在"Cookies设置"字段中填入: {cookie_path}
2. 或者选择"使用浏览器提取的Cookies"选项（如果可用）

🔄 下次下载:
- Cookies将保存30分钟
- 过期后请重新提取

💡 提示: 现在你可以下载需要登录的YouTube视频了！"""

            logger.info(f"成功提取 {cookie_count} 个cookies到 {cookie_path}")
            return success_message
        else:
            error_msg = result.get("error", "未知错误")
            logger.error(f"提取cookies失败: {error_msg}")
            return f"❌ 提取失败: {error_msg}"

    except Exception as e:
        error_msg = f"❌ 提取失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

def cleanup_session(session_id):
    """清理会话"""
    if not session_id:
        return "✅ 没有需要清理的会话"

    try:
        logger.info(f"清理会话 {session_id}...")
        response = requests.delete(f"{API_BASE_URL}/browser/session/{session_id}", timeout=10)
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            message = "✅ 会话已清理，浏览器窗口已关闭"
            logger.info(message)
            return message
        else:
            error_msg = result.get("error", "未知错误")
            return f"⚠️ 清理部分失败: {error_msg}"

    except Exception as e:
        logger.warning(f"清理会话时出错: {e}")
        return "✅ 会话引用已清理（可能有部分资源未完全释放）"

def download_video(url, format_choice, output_path="./downloads", cookies=None):
    """提交下载任务"""
    logger.info(f"开始下载视频: {url}")
    try:
        # 准备请求数据
        payload = {
            "url": url,
            "output_path": output_path,
            "format": format_choice
        }
        
        # 添加cookies参数（如果提供）
        if cookies:
            payload["cookies"] = cookies
        
        # 发送POST请求到API
        logger.info(f"发送下载请求到: {API_BASE_URL}/download")
        response = requests.post(f"{API_BASE_URL}/download", json=payload, timeout=30)
        response.raise_for_status()
        
        # 解析响应
        result = response.json()
        task_id = result.get("task_id")
        
        if not task_id:
            error_msg = "错误：无法获取任务ID"
            logger.error(error_msg)
            return error_msg, None
        
        logger.info(f"任务ID: {task_id}")
        
        # 轮询任务状态直到完成
        status_output = ""
        max_attempts = 30  # 最多尝试30次（约1分钟）
        attempt = 0
        
        while attempt < max_attempts:
            try:
                status_response = requests.get(f"{API_BASE_URL}/task/{task_id}", timeout=10)
                status_response.raise_for_status()
                status_data = status_response.json()
                
                task_status = status_data.get("data", {}).get("status", "unknown")
                status_output += f"任务状态: {task_status}\n"
                logger.info(f"任务 {task_id} 状态: {task_status}")
                
                if task_status == "completed":
                    # 获取下载文件
                    logger.info(f"下载完成，获取文件: {API_BASE_URL}/download/{task_id}/file")
                    file_response = requests.get(f"{API_BASE_URL}/download/{task_id}/file", timeout=30)
                    if file_response.status_code == 200:
                        # 保存文件
                        filename = f"downloaded_video_{task_id}.mp4"
                        with open(filename, "wb") as f:
                            f.write(file_response.content)
                        success_msg = status_output + "下载完成！"
                        logger.info(success_msg)
                        return success_msg, filename
                    else:
                        error_msg = status_output + f"错误：无法下载文件 (状态码: {file_response.status_code})"
                        logger.error(error_msg)
                        return error_msg, None
                elif task_status == "failed":
                    error = status_data.get("data", {}).get("error", "未知错误")
                    error_msg = status_output + f"下载失败: {error}"
                    logger.error(error_msg)
                    return error_msg, None
                
                # 等待一段时间后再次检查
                time.sleep(2)
                attempt += 1
            except requests.exceptions.ConnectionError as e:
                error_msg = f"连接错误: 无法连接到API服务，请检查服务是否运行"
                logger.error(error_msg)
                return error_msg, None
            except requests.exceptions.Timeout as e:
                error_msg = f"请求超时: {str(e)}"
                logger.error(error_msg)
                # 继续重试而不是直接返回错误
                time.sleep(2)
                attempt += 1
                continue
                
        # 超时处理
        timeout_msg = status_output + "下载超时，请稍后查看任务状态"
        logger.warning(timeout_msg)
        return timeout_msg, None
            
    except requests.exceptions.ConnectionError as e:
        error_msg = f"连接错误: 无法连接到API服务，请检查服务是否运行"
        logger.error(error_msg)
        return error_msg, None
    except requests.exceptions.Timeout as e:
        error_msg = f"请求超时: {str(e)}"
        logger.error(error_msg)
        return error_msg, None
    except Exception as e:
        error_msg = f"错误: {str(e)}"
        logger.error(error_msg)
        return error_msg, None

def get_video_info(url, cookies=None):
    """获取视频信息"""
    logger.info(f"获取视频信息: {url}")
    try:
        params = {"url": url}
        if cookies:
            params["cookies"] = cookies
        response = requests.get(f"{API_BASE_URL}/info", params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        info = data.get("data", {})
        title = info.get("title", "未知标题")
        duration = info.get("duration", "未知时长")
        uploader = info.get("uploader", "未知上传者")
        
        # 格式化时长
        if isinstance(duration, (int, float)):
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            duration = f"{minutes}分{seconds}秒"
        
        result = f"标题: {title}\n时长: {duration}\n上传者: {uploader}"
        logger.info(f"获取视频信息成功: {title}")
        return result
    except requests.exceptions.ConnectionError as e:
        error_msg = "连接错误: 无法连接到API服务，请检查服务是否运行"
        logger.error(error_msg)
        return error_msg
    except requests.exceptions.Timeout as e:
        error_msg = f"请求超时: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"获取视频信息失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

def list_formats(url, cookies=None):
    """列出可用格式"""
    logger.info(f"获取视频格式列表: {url}")
    try:
        params = {"url": url}
        if cookies:
            params["cookies"] = cookies
        response = requests.get(f"{API_BASE_URL}/formats", params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        formats = data.get("data", [])
        format_list = []
        for fmt in formats:
            format_id = fmt.get("format_id", "未知")
            ext = fmt.get("ext", "未知")
            resolution = fmt.get("resolution", "未知")
            format_note = fmt.get("format_note", "")
            if format_note:
                format_list.append(f"{format_id}: {resolution} ({ext}) - {format_note}")
            else:
                format_list.append(f"{format_id}: {resolution} ({ext})")
        
        result = "\n".join(format_list) if format_list else "未找到可用格式"
        logger.info(f"获取到 {len(format_list)} 个格式")
        return result
    except requests.exceptions.ConnectionError as e:
        error_msg = "连接错误: 无法连接到API服务，请检查服务是否运行"
        logger.error(error_msg)
        return error_msg
    except requests.exceptions.Timeout as e:
        error_msg = f"请求超时: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"获取格式列表失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

def download_subtitles(url, languages, auto_select, subtitle_format, output_path="./downloads", cookies=None):
    """提交字幕下载任务"""
    logger.info(f"开始下载字幕: {url}, 语言: {languages}")
    try:
        # 准备请求数据
        payload = {
            "url": url,
            "languages": languages,
            "auto_select": auto_select,
            "subtitle_format": subtitle_format,
            "output_path": output_path
        }

        # 添加cookies参数（如果提供）
        if cookies:
            payload["cookies"] = cookies

        # 发送POST请求到API
        logger.info(f"发送字幕下载请求到: {API_BASE_URL}/download-subtitles")
        response = requests.post(f"{API_BASE_URL}/download-subtitles", json=payload, timeout=30)
        response.raise_for_status()

        # 解析响应
        result = response.json()
        task_id = result.get("task_id")

        if not task_id:
            error_msg = "错误：无法获取任务ID"
            logger.error(error_msg)
            return error_msg, None

        logger.info(f"字幕任务ID: {task_id}")

        # 轮询任务状态直到完成
        status_output = ""
        max_attempts = 60  # 最多尝试60次（约2分钟）
        attempt = 0

        while attempt < max_attempts:
            try:
                status_response = requests.get(f"{API_BASE_URL}/task/{task_id}", timeout=10)
                status_response.raise_for_status()
                status_data = status_response.json()

                task_status = status_data.get("data", {}).get("status", "unknown")
                status_output += f"字幕任务状态: {task_status}\n"
                logger.info(f"字幕任务 {task_id} 状态: {task_status}")

                if task_status == "completed":
                    result_data = status_data.get("data", {}).get("result", {})
                    total_files = result_data.get("total_files", 0)
                    downloaded_files = result_data.get("downloaded_files", [])

                    if downloaded_files:
                        file_list = "\n".join([f"- {f['language']}: {f['path']}" for f in downloaded_files])
                        success_msg = status_output + f"字幕下载完成！\n下载文件数: {total_files}\n文件列表:\n{file_list}"
                        logger.info(success_msg)
                        return success_msg, downloaded_files
                    else:
                        error_msg = status_output + "字幕下载完成但没有文件"
                        logger.warning(error_msg)
                        return error_msg, None

                elif task_status == "failed":
                    error = status_data.get("data", {}).get("error", "未知错误")
                    error_msg = status_output + f"字幕下载失败: {error}"
                    logger.error(error_msg)
                    return error_msg, None

                # 等待一段时间后再次检查
                time.sleep(2)
                attempt += 1
            except requests.exceptions.ConnectionError as e:
                error_msg = f"连接错误: 无法连接到API服务，请检查服务是否运行"
                logger.error(error_msg)
                return error_msg, None
            except requests.exceptions.Timeout as e:
                error_msg = f"请求超时: {str(e)}"
                logger.error(error_msg)
                return error_msg, None
            except Exception as e:
                error_msg = f"错误: {str(e)}"
                logger.error(error_msg)
                return error_msg, None

        timeout_msg = status_output + "字幕下载超时"
        logger.warning(timeout_msg)
        return timeout_msg, None

    except requests.exceptions.ConnectionError as e:
        error_msg = f"连接错误: 无法连接到API服务，请检查服务是否运行"
        logger.error(error_msg)
        return error_msg, None
    except requests.exceptions.Timeout as e:
        error_msg = f"请求超时: {str(e)}"
        logger.error(error_msg)
        return error_msg, None
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP错误: {e.response.status_code} - {e.response.text}"
        logger.error(error_msg)
        return error_msg, None
    except Exception as e:
        error_msg = f"错误: {str(e)}"
        logger.error(error_msg)
        return error_msg, None

# Gradio界面
with gr.Blocks(title="yt-dlp 视频下载器") as demo:
    gr.Markdown("# yt-dlp 视频下载器")
    gr.Markdown("使用此工具下载YouTube等平台的视频和字幕")
    
    # 添加健康检查函数
    def health_check():
        """检查API服务是否可用"""
        try:
            response = requests.get(f"{API_BASE_URL}/docs", timeout=5)
            if response.status_code == 200:
                return "服务状态: 正常运行"
            else:
                return f"服务状态: 异常 (状态码: {response.status_code})"
        except Exception as e:
            return f"服务状态: 无法连接 ({str(e)})"
    
    # 在界面顶部添加健康检查显示
    health_status = gr.Textbox(label="服务状态", value=health_check())

    # YouTube登录相关变量
    current_session_id = None
    
    with gr.Tab("下载视频"):
        with gr.Row():
            url_input = gr.Textbox(label="视频URL", placeholder="请输入视频链接")
        with gr.Row():
            format_choice = gr.Dropdown(
                choices=[
                    "best[ext=mp4]",           # MP4格式最佳质量
                    "best[height<=1080]",      # 1080p以下最佳质量
                    "best[height<=720]",       # 720p以下最佳质量
                    "best[height<=480]",       # 480p以下最佳质量
                    "mp4",                     # 通用MP4格式
                    "webm",                    # WebM格式
                    "best",                    # 最佳可用格式(兜底)
                    "worst"                    # 最低质量(用于测试)
                ],
                value="best[ext=mp4]",
                label="下载格式"
            )
        with gr.Row():
            cookies_input = gr.Textbox(
                label="Cookies设置", 
                placeholder="输入cookies文件路径(如: /path/to/cookies.txt) 或浏览器名称(如: chrome, firefox, edge, safari)",
                value=""
            )
        with gr.Row():
            output_path = gr.Textbox(label="输出路径", value="./downloads")
        with gr.Row():
            download_btn = gr.Button("开始下载")
        with gr.Row():
            status_output = gr.Textbox(label="下载状态", interactive=False, lines=10)
        with gr.Row():
            video_output = gr.Video(label="下载的视频")
        
        download_btn.click(
            fn=download_video,
            inputs=[url_input, format_choice, output_path, cookies_input],
            outputs=[status_output, video_output]
        )
    
    with gr.Tab("视频信息"):
        with gr.Row():
            info_url = gr.Textbox(label="视频URL", placeholder="请输入视频链接")
        with gr.Row():
            info_cookies = gr.Textbox(
                label="Cookies设置", 
                placeholder="输入cookies文件路径或浏览器名称",
                value=""
            )
        with gr.Row():
            info_btn = gr.Button("获取信息")
        with gr.Row():
            info_output = gr.Textbox(label="视频信息", interactive=False, lines=10)
        
        info_btn.click(
            fn=get_video_info,
            inputs=[info_url, info_cookies],
            outputs=[info_output]
        )
    
    with gr.Tab("格式列表"):
        with gr.Row():
            formats_url = gr.Textbox(label="视频URL", placeholder="请输入视频链接")
        with gr.Row():
            formats_cookies = gr.Textbox(
                label="Cookies设置", 
                placeholder="输入cookies文件路径或浏览器名称",
                value=""
            )
        with gr.Row():
            formats_btn = gr.Button("列出格式")
        with gr.Row():
            formats_output = gr.Textbox(label="可用格式", interactive=False, lines=15)
        
        formats_btn.click(
            fn=list_formats,
            inputs=[formats_url, formats_cookies],
            outputs=[formats_output]
        )

    with gr.Tab("下载字幕"):
        with gr.Row():
            subtitle_url = gr.Textbox(label="视频URL", placeholder="请输入视频链接")
        with gr.Row():
            subtitle_languages = gr.CheckboxGroup(
                choices=["en", "zh", "es", "fr", "de", "ja", "ko", "ru", "ar", "hi", "pt", "it", "nl", "pl", "sv", "da", "no", "fi"],
                value=["en"],
                label="选择字幕语言"
            )
        with gr.Row():
            subtitle_format = gr.Dropdown(
                choices=["srt", "vtt", "ass", "ssa"],
                value="srt",
                label="字幕格式"
            )
        with gr.Row():
            auto_select = gr.Checkbox(
                label="自动选择最佳字幕（如果指定语言不可用）",
                value=True
            )
        with gr.Row():
            subtitle_cookies = gr.Textbox(
                label="Cookies设置",
                placeholder="输入cookies文件路径或浏览器名称",
                value=""
            )
        with gr.Row():
            subtitle_output_path = gr.Textbox(label="输出路径", value="./downloads")
        with gr.Row():
            subtitle_download_btn = gr.Button("下载字幕")
        with gr.Row():
            subtitle_status = gr.Textbox(label="下载状态", interactive=False, lines=10)

        subtitle_download_btn.click(
            fn=download_subtitles,
            inputs=[subtitle_url, subtitle_languages, auto_select, subtitle_format, subtitle_output_path, subtitle_cookies],
            outputs=[subtitle_status]
        )

    with gr.Tab("🔐 YouTube登录"):
        gr.Markdown("### 🔐 YouTube浏览器登录获取Cookies")
        gr.Markdown("通过系统启动的浏览器安全登录YouTube，自动提取cookies用于视频下载。")

        with gr.Row():
            start_session_btn = gr.Button("🚀 启动浏览器登录", variant="primary", size="lg")

        with gr.Row():
            login_status = gr.Textbox(
                label="📊 登录状态",
                interactive=False,
                lines=8,
                placeholder="等待启动浏览器会话..."
            )

        # 隐藏的会话ID存储
        session_id_hidden = gr.Textbox(visible=False, label="Session ID")

        # 会话控制按钮区域（初始隐藏）
        with gr.Row() as session_controls:
            check_status_btn = gr.Button("🔄 刷新状态", variant="secondary")
            extract_cookies_btn = gr.Button("🍪 提取Cookies", variant="primary")
            cleanup_btn = gr.Button("🧹 清理会话", variant="stop")

        # 会话统计信息
        with gr.Row():
            cookie_result = gr.Textbox(
                label="🎉 提取结果",
                interactive=False,
                lines=12,
                placeholder="Cookies提取结果将显示在这里..."
            )

        # 帮助信息
        with gr.Accordion("📖 使用说明", open=False):
            gr.Markdown("""
            ### 🚀 使用步骤

            1. **启动浏览器**: 点击"启动浏览器登录"按钮
            2. **访问链接**: 在提供的URL中完成YouTube登录
            3. **检查状态**: 点击"刷新状态"查看登录进度
            4. **提取Cookies**: 登录成功后点击"提取Cookies"
            5. **开始下载**: 使用提取的cookies下载视频

            ### ⚠️ 注意事项

            - 浏览器会话将在30分钟后自动过期
            - 支持所有YouTube登录方式（包括2FA）
            - Cookies将保存在本地，不会传输密码
            - 每次只能有一个活跃会话

            ### 🔧 故障排除

            - **启动失败**: 检查Chrome浏览器是否安装
            - **登录失败**: 确保网络连接正常
            - **提取失败**: 确保已完成YouTube登录
            """)

        # 绑定事件
        session_controls.visible = False  # 初始隐藏

        start_session_btn.click(
            fn=start_browser_session,
            outputs=[login_status, session_controls, session_id_hidden]
        )

        check_status_btn.click(
            fn=check_session_status,
            inputs=[session_id_hidden],
            outputs=[login_status]
        )

        extract_cookies_btn.click(
            fn=extract_browser_cookies,
            inputs=[session_id_hidden],
            outputs=[cookie_result]
        )

        cleanup_btn.click(
            fn=cleanup_session,
            inputs=[session_id_hidden],
            outputs=[cookie_result]
        )

if __name__ == "__main__":
    logger.info("启动Gradio应用...")
    logger.info(f"API基础URL: {API_BASE_URL}")
    logger.info(f"DOCKER_ENV环境变量: {os.getenv('DOCKER_ENV')}")
    
    try:
        demo.launch(
            server_name="0.0.0.0", 
            server_port=7860,
            prevent_thread_lock=True  # 防止线程锁，允许应用正常运行
        )
        logger.info("Gradio应用启动成功")
        
        # 保持应用运行
        import time
        while True:
            time.sleep(1)
    except Exception as e:
        logger.error(f"Gradio应用启动失败: {str(e)}")
        raise
