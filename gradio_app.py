#!/usr/bin/env python3
"""
yt-dlp API - Gradio界面应用
提供用户友好的Web界面，包括YouTube浏览器登录功能
"""

import gradio as gr
import requests
import os
import json
import uuid
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API基础URL - 自动检测是否在Docker环境中
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')

def start_browser_session():
    """启动浏览器登录会话"""
    try:
        logger.info("启动YouTube浏览器登录会话...")
        response = requests.post(f"{API_BASE_URL}/browser/session/start", timeout=30)
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            session_id = result.get("session_id")
            debug_port = result.get("debug_port")
            debug_url = result.get("debug_url")

            message = f"""✅ 浏览器会话已启动

📋 会话信息:
- 会话ID: {session_id}
- 调试端口: {debug_port}
- 访问地址: {debug_url}

📝 使用说明:
1. 点击上面的访问地址或直接访问 {debug_url}
2. 在打开的浏览器中访问 youtube.com 并完成登录
3. 登录成功后，点击"检查登录状态"验证
4. 最后点击"提取Cookies"保存登录状态

⏰ 会话将在30分钟后自动超时
"""
            logger.info(f"浏览器会话启动成功: {session_id}")
            return message, gr.update(visible=True), session_id
        else:
            error_msg = result.get("error", "未知错误")
            logger.error(f"启动浏览器会话失败: {error_msg}")
            return f"❌ 启动失败: {error_msg}", gr.update(visible=False), None

    except requests.exceptions.Timeout:
        error_msg = "❌ 启动超时，请稍后重试"
        logger.error(error_msg)
        return error_msg, gr.update(visible=False), None
    except requests.exceptions.ConnectionError:
        error_msg = "❌ 无法连接到API服务，请确保后端服务正在运行"
        logger.error(error_msg)
        return error_msg, gr.update(visible=False), None
    except Exception as e:
        error_msg = f"❌ 启动失败: {str(e)}"
        logger.error(error_msg)
        return error_msg, gr.update(visible=False), None

def check_session_status(session_id):
    """检查浏览器会话状态"""
    if not session_id:
        return "❌ 没有活跃的浏览器会话"

    try:
        logger.info(f"检查会话状态: {session_id}")
        response = requests.get(f"{API_BASE_URL}/browser/session/{session_id}/status", timeout=10)
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            session_data = result.get("session", {})
            status = session_data.get("status", "未知")
            youtube_logged_in = session_data.get("youtube_logged_in", False)
            created_at = session_data.get("created_at", "")
            last_activity = session_data.get("last_activity", "")

            status_text = f"""📊 会话状态: {status}
🔐 YouTube登录: {'✅ 已登录' if youtube_logged_in else '❌ 未登录'}
🕐 创建时间: {created_at}
🔄 最后活动: {last_activity}"""

            if youtube_logged_in:
                status_text += "\n\n🎉 检测到YouTube登录状态！现在可以提取Cookies了。"
                return status_text
            else:
                status_text += "\n\n⚠️ 尚未检测到YouTube登录，请确保已在浏览器中完成YouTube登录。"
                return status_text
        else:
            error_msg = result.get("error", "未知错误")
            return f"❌ 状态检查失败: {error_msg}"

    except Exception as e:
        error_msg = f"❌ 状态检查失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

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

            with open(cookie_path, 'w') as f:
                f.write(net_cookies)

            message = f"""✅ Cookies提取成功！

📋 提取信息:
- Cookie数量: {cookie_count}
- 保存文件: {cookie_filename}
- 文件路径: {cookie_path}

🎉 系统将自动使用这些cookies进行视频下载
"""
            logger.info(f"成功提取 {cookie_count} 个cookies到 {cookie_path}")
            return message
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

# Alias functions to match validation expectations
def get_browser_session_status(session_id):
    """获取浏览器会话状态（别名函数）"""
    return check_session_status(session_id)

def cleanup_browser_session(session_id):
    """清理浏览器会话（别名函数）"""
    return cleanup_session(session_id)

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

        if response.status_code == 200:
            result = response.json()
            task_id = result.get("task_id")
            logger.info(f"下载任务已提交，任务ID: {task_id}")
            return f"✅ 下载任务已提交！\n任务ID: {task_id}\n请使用任务ID查询下载进度。", task_id
        else:
            error_detail = response.text
            logger.error(f"下载请求失败: {response.status_code} - {error_detail}")
            return f"❌ 下载请求失败: {response.status_code}\n{error_detail}", None

    except requests.exceptions.Timeout:
        error_msg = "❌ 请求超时，请检查网络连接或API服务状态"
        logger.error(error_msg)
        return error_msg, None
    except requests.exceptions.ConnectionError:
        error_msg = "❌ 无法连接到API服务，请确保后端服务正在运行"
        logger.error(error_msg)
        return error_msg, None
    except Exception as e:
        error_msg = f"❌ 下载请求失败: {str(e)}"
        logger.error(error_msg)
        return error_msg, None

def check_task_status(task_id):
    """检查任务状态"""
    if not task_id:
        return "❌ 请提供任务ID", None

    try:
        logger.info(f"查询任务状态: {task_id}")
        response = requests.get(f"{API_BASE_URL}/task/{task_id}", timeout=10)
        response.raise_for_status()

        result = response.json()
        status = result.get("status", "未知")
        progress = result.get("progress", {})

        # 格式化进度信息
        if isinstance(progress, dict):
            progress_text = "\n".join([f"{k}: {v}" for k, v in progress.items()])
        else:
            progress_text = str(progress)

        status_text = f"""任务ID: {task_id}
状态: {status}
进度信息: {progress_text}"""

        # 如果任务完成，显示下载链接
        if status == "completed":
            download_url = f"{API_BASE_URL}/download/{task_id}/file"
            status_text += f"\n\n✅ 下载完成！\n下载链接: {download_url}"
            return status_text, download_url
        elif status == "failed":
            error = result.get("error", "未知错误")
            status_text += f"\n\n❌ 下载失败: {error}"
            return status_text, None
        else:
            status_text += "\n\n⏳ 下载中，请稍后查询..."
            return status_text, None

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return f"❌ 任务不存在: {task_id}", None
        else:
            return f"❌ 查询失败: {e.response.status_code}", None
    except Exception as e:
        error_msg = f"❌ 查询任务状态失败: {str(e)}"
        logger.error(error_msg)
        return error_msg, None

def get_video_info(url):
    """获取视频信息"""
    if not url:
        return "❌ 请提供视频URL", None

    try:
        logger.info(f"获取视频信息: {url}")
        response = requests.get(f"{API_BASE_URL}/info?url={url}", timeout=30)
        response.raise_for_status()

        result = response.json()

        if result.get("success"):
            info = result.get("info", {})
            title = info.get("title", "未知标题")
            duration = info.get("duration", "未知时长")
            uploader = info.get("uploader", "未知上传者")
            view_count = info.get("view_count", "未知播放量")

            info_text = f"""标题: {title}
时长: {duration}秒
上传者: {uploader}
播放量: {view_count}"""

            return info_text, info
        else:
            error_msg = result.get("error", "未知错误")
            return f"❌ 获取视频信息失败: {error_msg}", None

    except Exception as e:
        error_msg = f"❌ 获取视频信息失败: {str(e)}"
        logger.error(error_msg)
        return error_msg, None

def list_formats(url):
    """列出可用格式"""
    if not url:
        return "❌ 请提供视频URL"

    try:
        logger.info(f"获取视频格式列表: {url}")
        response = requests.get(f"{API_BASE_URL}/formats?url={url}", timeout=30)
        response.raise_for_status()

        result = response.json()

        if result.get("success"):
            formats = result.get("formats", [])
            if not formats:
                return "❌ 没有找到可用格式"

            format_text = "可用格式:\n\n"
            for fmt in formats[:20]:  # 只显示前20个格式
                format_id = fmt.get("format_id", "未知")
                ext = fmt.get("ext", "未知")
                quality = fmt.get("format_note", "未知质量")
                file_size = fmt.get("filesize", "未知大小")

                format_text += f"ID: {format_id} | 扩展名: {ext} | 质量: {quality} | 大小: {file_size}\n"

            if len(formats) > 20:
                format_text += f"\n... 还有 {len(formats) - 20} 个格式"

            return format_text
        else:
            error_msg = result.get("error", "未知错误")
            return f"❌ 获取格式列表失败: {error_msg}"

    except Exception as e:
        error_msg = f"❌ 获取格式列表失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

def create_gradio_interface():
    """创建Gradio界面"""
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

        with gr.Tab("🔐 YouTube登录"):
            gr.Markdown("""
            ## YouTube浏览器登录

            使用真实浏览器完成YouTube登录，系统会自动提取cookies用于视频下载。

            **优势:**
            - ✅ 真实用户登录，避免机器人检测
            - ✅ 支持会员内容下载
            - ✅ 自动cookies管理和更新
            - ✅ 安全隔离的浏览器环境

            **使用步骤:**
            1. 点击"启动浏览器登录"
            2. 访问显示的浏览器地址
            3. 完成 YouTube 登录
            4. 点击"检查登录状态"验证
            5. 点击"提取Cookies"保存状态
            """)

            # 会话控制按钮
            with gr.Row():
                start_session_btn = gr.Button("🚀 启动浏览器登录", variant="primary")
                check_status_btn = gr.Button("🔍 检查登录状态")
                extract_cookies_btn = gr.Button("🍪 提取Cookies", variant="secondary")
                cleanup_btn = gr.Button("🧹 清理会话", variant="stop")

            # 状态显示
            login_status = gr.Textbox(
                label="登录状态",
                lines=8,
                max_lines=15,
                interactive=False
            )

            # 会话控制区域（初始隐藏）
            with gr.Group(visible=False) as session_controls:
                gr.Markdown("### 会话控制")
                cookie_result = gr.Textbox(
                    label="操作结果",
                    lines=6,
                    max_lines=10,
                    interactive=False
                )

            # 隐藏的会话ID存储
            session_id_hidden = gr.State()

            # 绑定事件
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

        with gr.Tab("📥 下载视频"):
            with gr.Row():
                url_input = gr.Textbox(label="视频URL", placeholder="请输入视频链接")
            with gr.Row():
                format_choice = gr.Dropdown(
                    choices=["best", "worst", "bestvideo+bestaudio", "mp4", "webm"],
                    label="选择格式",
                    value="best"
                )
                output_path = gr.Textbox(label="输出路径", value="./downloads", placeholder="下载目录")
            with gr.Row():
                download_btn = gr.Button("开始下载", variant="primary")

            download_result = gr.Textbox(label="下载结果", lines=3, interactive=False)
            task_id_output = gr.Textbox(label="任务ID", interactive=False)

        with gr.Tab("📊 任务状态"):
            with gr.Row():
                task_id_input = gr.Textbox(label="任务ID", placeholder="输入任务ID查询状态")
                check_status_btn = gr.Button("查询状态")
            with gr.Row():
                status_output = gr.Textbox(label="任务状态", lines=8, interactive=False)
                download_link = gr.Textbox(label="下载链接", interactive=False)

        with gr.Tab("ℹ️ 视频信息"):
            with gr.Row():
                info_url_input = gr.Textbox(label="视频URL", placeholder="输入视频URL获取信息")
                get_info_btn = gr.Button("获取信息")
            with gr.Row():
                info_output = gr.Textbox(label="视频信息", lines=6, interactive=False)

        with gr.Tab("📋 格式列表"):
            with gr.Row():
                formats_url_input = gr.Textbox(label="视频URL", placeholder="输入视频URL获取格式列表")
                list_formats_btn = gr.Button("获取格式")
            with gr.Row():
                formats_output = gr.Textbox(label="可用格式", lines=15, interactive=False)

        # 绑定事件
        download_btn.click(
            fn=download_video,
            inputs=[url_input, format_choice, output_path],
            outputs=[download_result, task_id_output]
        )

        check_status_btn.click(
            fn=check_task_status,
            inputs=[task_id_input],
            outputs=[status_output, download_link]
        )

        get_info_btn.click(
            fn=get_video_info,
            inputs=[info_url_input],
            outputs=[info_output, gr.State()]
        )

        list_formats_btn.click(
            fn=list_formats,
            inputs=[formats_url_input],
            outputs=[formats_output]
        )

    return demo

if __name__ == "__main__":
    logger.info("启动Gradio应用...")
    logger.info(f"API基础URL: {API_BASE_URL}")
    logger.info(f"DOCKER_ENV环境变量: {os.getenv('DOCKER_ENV')}")

    try:
        # 创建界面
        demo = create_gradio_interface()

        # 启动应用
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            prevent_thread_lock=False  # 在supervisor中不需要prevent_thread_lock
        )
        logger.info("Gradio应用启动成功")

    except Exception as e:
        logger.error(f"Gradio应用启动失败: {str(e)}")
        raise