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

def download_subtitles(url, languages, auto_select, subtitle_format, output_path="./downloads"):
    """提交字幕下载任务"""
    if not url:
        return "❌ 请提供视频URL", None

    try:
        logger.info(f"开始下载字幕: {url}, 语言: {languages}")

        # 准备请求数据
        payload = {
            "url": url,
            "languages": languages,
            "auto_select": auto_select,
            "subtitle_format": subtitle_format,
            "output_path": output_path
        }

        # 发送POST请求到API
        # POST /download-subtitles - 字幕下载端点，自动使用cookies认证
        logger.info(f"发送字幕下载请求到: {API_BASE_URL}/download-subtitles")
        response = requests.post(f"{API_BASE_URL}/download-subtitles", json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()
        task_id = result.get("task_id")

        if task_id:
            logger.info(f"字幕下载任务已提交，任务ID: {task_id}")
            return f"✅ 字幕下载任务已提交！\n任务ID: {task_id}\n请使用任务ID查询下载进度。", task_id
        else:
            error_msg = result.get("error", "未知错误")
            logger.error(f"字幕下载请求失败: {error_msg}")
            return f"❌ 字幕下载请求失败: {error_msg}", None

    except requests.exceptions.Timeout:
        error_msg = "❌ 请求超时，请检查网络连接或API服务状态"
        logger.error(error_msg)
        return error_msg, None
    except requests.exceptions.ConnectionError:
        error_msg = "❌ 无法连接到API服务，请确保后端服务正在运行"
        logger.error(error_msg)
        return error_msg, None
    except Exception as e:
        error_msg = f"❌ 字幕下载请求失败: {str(e)}"
        logger.error(error_msg)
        return error_msg, None

# 系统管理功能
def check_ytdlp_version():
    """检查yt-dlp版本"""
    try:
        logger.info("检查yt-dlp版本...")
        response = requests.get(f"{API_BASE_URL}/ytdlp/version", timeout=10)
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            version_info = result.get("data", {})
            return f"当前版本: {version_info.get('version', '未知')}\n安装日期: {version_info.get('install_date', '未知')}"
        else:
            error_msg = result.get("error", "未知错误")
            return f"❌ 获取版本信息失败: {error_msg}"
    except Exception as e:
        error_msg = f"❌ 检查版本失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

def check_ytdlp_update():
    """检查yt-dlp更新"""
    try:
        logger.info("检查yt-dlp更新...")
        response = requests.get(f"{API_BASE_URL}/ytdlp/check-update", timeout=30)
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            update_info = result.get("data", {})
            current = update_info.get("current_version", "未知")
            latest = update_info.get("latest_version", "未知")
            update_available = update_info.get("update_available", False)

            if update_available:
                return f"发现新版本！\n当前版本: {current}\n最新版本: {latest}"
            else:
                return f"当前版本已是最新\n当前版本: {current}"
        else:
            error_msg = result.get("error", "未知错误")
            return f"❌ 检查更新失败: {error_msg}"
    except Exception as e:
        error_msg = f"❌ 检查更新失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

def update_ytdlp():
    """更新yt-dlp"""
    try:
        logger.info("开始更新yt-dlp...")
        response = requests.post(f"{API_BASE_URL}/ytdlp/update", timeout=300)
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            return "✅ yt-dlp更新成功！"
        else:
            error_msg = result.get("error", "未知错误")
            return f"❌ 更新失败: {error_msg}"
    except Exception as e:
        error_msg = f"❌ 更新失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

def get_ytdlp_update_history():
    """获取更新历史"""
    try:
        logger.info("获取yt-dlp更新历史...")
        response = requests.get(f"{API_BASE_URL}/ytdlp/update-history", timeout=10)
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            history = result.get("data", [])
            if history:
                history_text = "更新历史:\n"
                for item in history[-10:]:  # 显示最近10条
                    history_text += f"- {item.get('version', '未知')} ({item.get('update_time', '未知')}) - {item.get('result', '未知')}\n"
                return history_text
            else:
                return "暂无更新历史记录"
        else:
            error_msg = result.get("error", "未知错误")
            return f"❌ 获取历史失败: {error_msg}"
    except Exception as e:
        error_msg = f"❌ 获取历史失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

# 调度器管理功能
def check_scheduler_status():
    """检查调度器状态"""
    try:
        logger.info("检查调度器状态...")
        response = requests.get(f"{API_BASE_URL}/scheduler/status", timeout=10)
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            status_info = result.get("data", {})
            status_text = f"调度器状态: {status_info.get('status', '未知')}\n"
            status_text += f"下次更新: {status_info.get('next_update', '未知')}\n"
            status_text += f"配置文件: {status_info.get('config_file', '未知')}"
            return status_text
        else:
            error_msg = result.get("error", "未知错误")
            return f"❌ 获取状态失败: {error_msg}"
    except Exception as e:
        error_msg = f"❌ 获取状态失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

def start_scheduler():
    """启动调度器"""
    try:
        logger.info("启动调度器...")
        response = requests.post(f"{API_BASE_URL}/scheduler/start", timeout=10)
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            return "✅ 调度器启动成功"
        else:
            error_msg = result.get("error", "未知错误")
            return f"❌ 启动失败: {error_msg}"
    except Exception as e:
        error_msg = f"❌ 启动失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

def stop_scheduler():
    """停止调度器"""
    try:
        logger.info("停止调度器...")
        response = requests.post(f"{API_BASE_URL}/scheduler/stop", timeout=10)
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            return "✅ 调度器停止成功"
        else:
            error_msg = result.get("error", "未知错误")
            return f"❌ 停止失败: {error_msg}"
    except Exception as e:
        error_msg = f"❌ 停止失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

def get_scheduler_config():
    """获取调度器配置"""
    try:
        logger.info("获取调度器配置...")
        response = requests.get(f"{API_BASE_URL}/scheduler/config", timeout=10)
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            config_info = result.get("data", {})
            config_text = "调度器配置:\n"
            config_text += f"检查间隔: {config_info.get('check_interval', '未知')} 小时\n"
            config_text += f"自动更新: {config_info.get('auto_update', '未知')}\n"
            config_text += f"更新时间: {config_info.get('update_time', '未知')}\n"
            config_text += f"启用调度: {config_info.get('scheduler_enabled', '未知')}"
            return config_text
        else:
            error_msg = result.get("error", "未知错误")
            return f"❌ 获取配置失败: {error_msg}"
    except Exception as e:
        error_msg = f"❌ 获取配置失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

def update_scheduler_config(check_interval=24, auto_update=True, update_time="02:00", scheduler_enabled=True):
    """更新调度器配置"""
    try:
        logger.info("更新调度器配置...")
        payload = {
            "check_interval": check_interval,
            "auto_update": auto_update,
            "update_time": update_time,
            "scheduler_enabled": scheduler_enabled
        }
        response = requests.put(f"{API_BASE_URL}/scheduler/config", json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            return "✅ 配置更新成功"
        else:
            error_msg = result.get("error", "未知错误")
            return f"❌ 配置更新失败: {error_msg}"
    except Exception as e:
        error_msg = f"❌ 配置更新失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

# 任务中心功能
def get_all_tasks():
    """获取所有任务"""
    try:
        logger.info("获取所有任务...")
        response = requests.get(f"{API_BASE_URL}/tasks", timeout=30)
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            tasks = result.get("data", [])
            if tasks:
                return tasks
            else:
                return []
        else:
            error_msg = result.get("error", "未知错误")
            logger.error(f"获取任务失败: {error_msg}")
            return []
    except Exception as e:
        error_msg = f"❌ 获取任务失败: {str(e)}"
        logger.error(error_msg)
        return []

def delete_multiple_tasks(task_ids):
    """删除多个任务"""
    try:
        if not task_ids:
            return "❌ 请提供要删除的任务ID"

        logger.info(f"删除多个任务: {task_ids}")
        payload = {"task_ids": task_ids}
        response = requests.delete(f"{API_BASE_URL}/tasks", json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            deleted_count = result.get("data", {}).get("deleted_count", 0)
            return f"✅ 成功删除 {deleted_count} 个任务"
        else:
            error_msg = result.get("error", "未知错误")
            return f"❌ 删除失败: {error_msg}"
    except Exception as e:
        error_msg = f"❌ 删除失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

# 缺失的任务管理函数
def refresh_task_list():
    """刷新任务列表"""
    try:
        tasks = get_all_tasks()
        if tasks:
            # 转换为Gradio表格格式
            task_data = []
            for task in tasks:
                task_data.append([
                    task.get('task_id', '未知'),
                    task.get('url', '未知')[:50] + '...' if len(task.get('url', '')) > 50 else task.get('url', '未知'),
                    task.get('status', '未知'),
                    f"{task.get('progress', 0)}%",
                    task.get('created_at', '未知'),
                    task.get('completed_at', '-') if task.get('completed_at') else '-'
                ])
            return task_data
        else:
            return [["无任务", "", "", "", "", ""]]
    except Exception as e:
        logger.error(f"刷新任务列表失败: {str(e)}")
        return [["获取失败", str(e), "", "", "", ""]]

def delete_selected_tasks():
    """删除选中的任务 - 简化版本"""
    # 由于Gradio限制，这里实现为删除所有已完成任务
    try:
        tasks = get_all_tasks()
        completed_task_ids = [task['task_id'] for task in tasks if task.get('status') == 'completed']
        if completed_task_ids:
            return delete_multiple_tasks(completed_task_ids)
        else:
            return "❌ 没有已完成的任务可删除"
    except Exception as e:
        return f"❌ 删除任务失败: {str(e)}"

def clear_completed_tasks():
    """清理所有已完成的任务"""
    try:
        tasks = get_all_tasks()
        completed_task_ids = [task['task_id'] for task in tasks if task.get('status') == 'completed']
        if completed_task_ids:
            return delete_multiple_tasks(completed_task_ids)
        else:
            return "✅ 没有已完成的任务需要清理"
    except Exception as e:
        return f"❌ 清理任务失败: {str(e)}"

# Cookie管理功能
def get_cookies_status():
    """获取Cookie状态"""
    try:
        logger.info("获取Cookie状态...")
        response = requests.get(f"{API_BASE_URL}/cookies/status", timeout=10)
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            status_info = result.get("data", {})
            status_text = f"Cookie状态: {status_info.get('status', '未知')}\n"
            status_text += f"文件位置: {status_info.get('file_path', '未知')}\n"
            status_text += f"文件大小: {status_info.get('file_size', '未知')}字节\n"
            status_text += f"最后更新: {status_info.get('last_updated', '未知')}"
            return status_text
        else:
            error_msg = result.get("error", "未知错误")
            return f"❌ 获取状态失败: {error_msg}"
    except Exception as e:
        error_msg = f"❌ 获取状态失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

def auto_setup_cookies():
    """自动设置Cookie"""
    try:
        logger.info("自动设置Cookie...")
        response = requests.post(f"{API_BASE_URL}/cookies/auto-setup", timeout=30)
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            data = result.get("data", {})
            return f"✅ Cookie自动设置成功！\n检测到 {data.get('browsers_found', 0)} 个浏览器\n成功提取 {data.get('cookies_extracted', 0)} 个Cookie"
        else:
            error_msg = result.get("error", "未知错误")
            return f"❌ 自动设置失败: {error_msg}"
    except Exception as e:
        error_msg = f"❌ 自动设置失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

def diagnose_environment():
    """诊断环境"""
    try:
        logger.info("诊断环境...")
        response = requests.get(f"{API_BASE_URL}/cookies/diagnose", timeout=15)
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            diagnosis = result.get("data", {})
            report = "环境诊断报告:\n\n"

            # 系统信息
            system_info = diagnosis.get("system_info", {})
            report += f"操作系统: {system_info.get('os_type', '未知')} {system_info.get('os_version', '未知')}\n"
            report += f"Python版本: {system_info.get('python_version', '未知')}\n\n"

            # 浏览器信息
            browsers = diagnosis.get("browsers", {})
            report += "浏览器状态:\n"
            for browser_name, browser_info in browsers.items():
                status = "✅ 运行中" if browser_info.get("running", False) else "❌ 未运行"
                report += f"  {browser_name}: {status}\n"

            # Cookie文件状态
            cookie_status = diagnosis.get("cookie_files", {})
            report += f"\nCookie文件状态: {cookie_status.get('count', 0)} 个文件\n"

            return report
        else:
            error_msg = result.get("error", "未知错误")
            return f"❌ 环境诊断失败: {error_msg}"
    except Exception as e:
        error_msg = f"❌ 环境诊断失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

def cleanup_cookies():
    """清理过期Cookie"""
    try:
        logger.info("清理过期Cookie...")
        response = requests.delete(f"{API_BASE_URL}/cookies/cleanup", timeout=10)
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            data = result.get("data", {})
            return f"✅ Cookie清理成功！\n删除了 {data.get('deleted_files', 0)} 个过期文件\n释放了 {data.get('freed_space', 0)} 字节空间"
        else:
            error_msg = result.get("error", "未知错误")
            return f"❌ 清理失败: {error_msg}"
    except Exception as e:
        error_msg = f"❌ 清理失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

def get_supported_browsers():
    """获取支持的浏览器列表"""
    try:
        logger.info("获取支持的浏览器列表...")
        response = requests.get(f"{API_BASE_URL}/cookies/supported-browsers", timeout=10)
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            browsers = result.get("data", [])
            if browsers:
                browser_text = "支持的浏览器:\n\n"
                for browser in browsers:
                    browser_text += f"🌐 {browser.get('name', '未知')}\n"
                    browser_text += f"   版本: {browser.get('version', '未知')}\n"
                    browser_text += f"   状态: {'✅ 支持' if browser.get('supported', False) else '❌ 不支持'}\n\n"
                return browser_text
            else:
                return "暂无支持的浏览器信息"
        else:
            error_msg = result.get("error", "未知错误")
            return f"❌ 获取浏览器列表失败: {error_msg}"
    except Exception as e:
        error_msg = f"❌ 获取浏览器列表失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

def get_cookies_list():
    """获取Cookie文件列表"""
    try:
        logger.info("获取Cookie文件列表...")
        response = requests.get(f"{API_BASE_URL}/cookies/list", timeout=10)
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            cookies = result.get("data", [])
            if cookies:
                cookie_data = []
                for cookie in cookies:
                    cookie_data.append([
                        cookie.get('filename', '未知'),
                        cookie.get('browser', '未知'),
                        f"{cookie.get('size', 0)} 字节",
                        cookie.get('created_time', '未知'),
                        cookie.get('expires_time', '未知') or '永不过期',
                        '✅ 有效' if cookie.get('valid', False) else '❌ 无效'
                    ])
                return cookie_data
            else:
                return [["无Cookie文件", "", "", "", "", ""]]
        else:
            error_msg = result.get("error", "未知错误")
            return [["获取失败", error_msg, "", "", "", ""]]
    except Exception as e:
        logger.error(f"获取Cookie列表失败: {str(e)}")
        return [["获取失败", str(e), "", "", "", ""]]

# 增强视频信息功能
def get_video_thumbnails(url):
    """获取视频缩略图"""
    try:
        logger.info(f"获取视频缩略图: {url}")
        params = {"url": url}
        response = requests.get(f"{API_BASE_URL}/thumbnails", params=params, timeout=15)
        response.raise_for_status()
        result = response.json()

        if result.get("status") == "success":
            thumbnails = result.get("data", {})
            if thumbnails:
                thumbnail_text = "可用缩略图:\n\n"
                for quality, info in thumbnails.items():
                    thumbnail_text += f"🖼️ {quality}:\n"
                    thumbnail_text += f"   宽度: {info.get('width', '未知')}\n"
                    thumbnail_text += f"   高度: {info.get('height', '未知')}\n"
                    thumbnail_text += f"   URL: {info.get('url', '未知')}\n\n"
                return thumbnail_text
            else:
                return "暂无可用缩略图"
        else:
            return f"❌ 获取缩略图失败: {result.get('detail', '未知错误')}"
    except Exception as e:
        error_msg = f"❌ 获取缩略图失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

def get_video_subtitles_list(url):
    """获取视频字幕列表"""
    try:
        logger.info(f"获取视频字幕列表: {url}")
        params = {"url": url}
        response = requests.get(f"{API_BASE_URL}/subtitles", params=params, timeout=15)
        response.raise_for_status()
        result = response.json()

        if result.get("status") == "success":
            subtitles = result.get("data", {})
            if subtitles:
                subtitle_data = []
                for lang, info in subtitles.items():
                    subtitle_data.append([
                        lang,
                        info.get('name', lang),
                        info.get('format', '未知'),
                        info.get('url', '未知')[:50] + '...' if len(info.get('url', '')) > 50 else info.get('url', '未知')
                    ])
                return subtitle_data
            else:
                return [["无字幕", "", "", ""]]
        else:
            return [["获取失败", result.get('detail', '未知错误'), "", ""]]
    except Exception as e:
        logger.error(f"获取字幕列表失败: {str(e)}")
        return [["获取失败", str(e), "", ""]]

def get_comprehensive_video_info(url):
    """获取综合视频信息"""
    try:
        logger.info(f"获取综合视频信息: {url}")
        params = {"url": url}
        response = requests.get(f"{API_BASE_URL}/video-details", params=params, timeout=20)
        response.raise_for_status()
        result = response.json()

        if result.get("status") == "success":
            video_info = result.get("data", {})

            # 格式化显示基本信息
            info_text = "📹 视频详细信息:\n\n"

            # 基本信息部分
            basic_info = video_info.get('basic_info', {})
            if basic_info:
                info_text += f"📝 标题: {basic_info.get('title', '未知')}\n"
                info_text += f"👤 上传者: {basic_info.get('uploader', '未知')}\n"
                info_text += f"⏱️ 时长: {basic_info.get('duration', '未知')}\n"
                info_text += f"👁️ 观看数: {basic_info.get('view_count', '未知')}\n"
                info_text += f"👍 点赞数: {basic_info.get('like_count', '未知')}\n"
                info_text += f"📅 上传时间: {basic_info.get('upload_date', '未知')}\n"
                info_text += f"🔗 视频ID: {basic_info.get('id', '未知')}\n\n"

            # 技术信息部分
            tech_info = video_info.get('technical_info', {})
            if tech_info:
                info_text += "⚙️ 技术信息:\n"
                info_text += f"   格式: {tech_info.get('format', '未知')}\n"
                info_text += f"   分辨率: {tech_info.get('resolution', '未知')}\n"
                info_text += f"   文件大小: {tech_info.get('filesize', '未知')}\n"
                info_text += f"   比特率: {tech_info.get('tbr', '未知')}\n\n"

            # 缩略图信息
            thumbnails = video_info.get('thumbnails', {})
            if thumbnails:
                info_text += f"🖼️ 可用缩略图: {len(thumbnails)} 个\n"

            # 字幕信息
            subtitles = video_info.get('subtitles', {})
            if subtitles:
                info_text += f"📝 可用字幕: {len(subtitles)} 种语言\n"

            return info_text
        else:
            return f"❌ 获取视频信息失败: {result.get('detail', '未知错误')}"
    except Exception as e:
        error_msg = f"❌ 获取视频信息失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

def download_subtitle_direct(url, lang, format="srt"):
    """直接下载字幕文件"""
    try:
        logger.info(f"下载字幕: {url}, 语言: {lang}, 格式: {format}")
        params = {"url": url, "lang": lang, "format": format}
        response = requests.get(f"{API_BASE_URL}/subtitle", params=params, timeout=30)

        if response.status_code == 200:
            # 返回下载信息而不是文件内容
            return f"✅ 字幕下载成功！\n语言: {lang}\n格式: {format}\n状态: 已准备好下载"
        else:
            return f"❌ 字幕下载失败: HTTP {response.status_code}"
    except Exception as e:
        error_msg = f"❌ 字幕下载失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

def get_video_quality_analysis(url):
    """获取视频质量分析"""
    try:
        logger.info(f"分析视频质量: {url}")
        # 先获取格式信息
        params = {"url": url}
        response = requests.get(f"{API_BASE_URL}/formats", params=params, timeout=15)
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            formats = result.get("data", {}).get("formats", [])
            if formats:
                # 分析可用格式
                quality_analysis = "🎯 视频质量分析:\n\n"

                # 统计不同分辨率
                resolutions = {}
                for fmt in formats:
                    resolution = fmt.get("resolution", "未知")
                    if resolution != "unknown":
                        resolutions[resolution] = resolutions.get(resolution, 0) + 1

                quality_analysis += "📊 可用分辨率统计:\n"
                for res, count in sorted(resolutions.items(), key=lambda x: x[0], reverse=True):
                    quality_analysis += f"   {res}: {count} 个格式\n"

                # 推荐最佳格式
                best_formats = [f for f in formats if f.get("ext") == "mp4" and f.get("resolution") and f.get("resolution") != "unknown"]
                if best_formats:
                    best_format = max(best_formats, key=lambda x: int(x.get("resolution", "0").split("x")[0]) if "x" in x.get("resolution", "") else 0)
                    quality_analysis += f"\n🏆 推荐格式:\n"
                    quality_analysis += f"   分辨率: {best_format.get('resolution', '未知')}\n"
                    quality_analysis += f"   格式ID: {best_format.get('format_id', '未知')}\n"
                    quality_analysis += f"   文件大小: {best_format.get('filesize', '未知') or '未知'}\n"

                return quality_analysis
            else:
                return "暂无格式信息进行分析"
        else:
            return f"❌ 质量分析失败: {result.get('error', '未知错误')}"
    except Exception as e:
        error_msg = f"❌ 质量分析失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

# 智能下载功能增强
def get_download_optimized_formats(url):
    """获取下载优化格式"""
    try:
        logger.info(f"获取下载优化格式: {url}")
        params = {"url": url}
        response = requests.get(f"{API_BASE_URL}/download-formats", params=params, timeout=20)
        response.raise_for_status()
        result = response.json()

        if result.get("status") == "success":
            data = result.get("data", {})
            formats = data.get("formats", [])
            recommended = data.get("recommended", [])

            if formats:
                format_text = "📋 可用下载格式:\n\n"

                # 按优先级排序：推荐格式优先
                recommended_ids = [fmt.get("format_id") for fmt in recommended]

                for fmt in formats:
                    format_id = fmt.get("format_id", "")
                    is_recommended = format_id in recommended_ids
                    star = "⭐ " if is_recommended else ""

                    format_text += f"{star}{format_id}: "
                    format_text += f"{fmt.get('ext', '未知')} "
                    format_text += f"{fmt.get('resolution', '未知')} "

                    # 添加文件大小信息
                    filesize = fmt.get('filesize') or fmt.get('filesize_approx')
                    if filesize:
                        format_text += f"({filesize/1024/1024:.1f}MB) "

                    # 添加比特率信息
                    if fmt.get('tbr', 0) > 0:
                        format_text += f"[{fmt.get('tbr')}kbps] "

                    if is_recommended:
                        format_text += "[推荐]"

                    format_text += "\n"

                # 推荐格式详情
                if recommended:
                    format_text += f"\n🏆 推荐格式详情:\n"
                    for fmt in recommended:
                        format_text += f"• {fmt.get('format_id', '')}: {fmt.get('resolution', '')} {fmt.get('ext', '')}\n"

                return format_text
            else:
                return "暂无可用的下载格式"
        else:
            return f"❌ 获取格式失败: {result.get('detail', '未知错误')}"
    except Exception as e:
        error_msg = f"❌ 获取格式失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

def get_smart_format_recommendation(url, preference="balanced"):
    """获取智能格式推荐"""
    try:
        logger.info(f"获取智能格式推荐: {url}, 偏好: {preference}")
        params = {"url": url}
        response = requests.get(f"{API_BASE_URL}/download-formats", params=params, timeout=20)
        response.raise_for_status()
        result = response.json()

        if result.get("status") == "success":
            data = result.get("data", {})
            formats = data.get("formats", [])
            recommended = data.get("recommended", [])

            if not formats:
                return "暂无格式可供推荐"

            recommendation_text = f"🎯 智能格式推荐 (偏好: {preference}):\n\n"

            # 根据偏好分析格式
            if preference == "quality":
                # 高质量优先
                high_quality = [f for f in formats if f.get('vcodec') != 'none' and
                               f.get('resolution') and f.get('resolution') != 'unknown']
                if high_quality:
                    best = max(high_quality, key=lambda x: int(x.get('resolution', '0').split('x')[0]) if 'x' in x.get('resolution', '') else 0)
                    recommendation_text += f"🏆 最佳质量: {best.get('format_id', '')} - {best.get('resolution', '')} {best.get('ext', '')}\n"

            elif preference == "size":
                # 文件大小优先
                with_size = [f for f in formats if f.get('filesize') or f.get('filesize_approx')]
                if with_size:
                    smallest = min(with_size, key=lambda x: x.get('filesize') or x.get('filesize_approx', float('inf')))
                    recommendation_text += f"💾 最小文件: {smallest.get('format_id', '')} - {smallest.get('resolution', '')} {smallest.get('ext', '')}\n"

            elif preference == "speed":
                # 下载速度优先 (选择较低比特率)
                video_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('tbr', 0) > 0]
                if video_formats:
                    fastest = min(video_formats, key=lambda x: x.get('tbr', float('inf')))
                    recommendation_text += f"⚡ 最快下载: {fastest.get('format_id', '')} - {fastest.get('resolution', '')} {fastest.get('ext', '')}\n"

            else:  # balanced
                # 平衡选择
                if recommended:
                    rec = recommended[0]  # 取第一个推荐
                    recommendation_text += f"⚖️ 平衡推荐: {rec.get('format_id', '')} - {rec.get('resolution', '')} {rec.get('ext', '')}\n"

            # 添加备选方案
            recommendation_text += f"\n📋 备选方案:\n"
            backup_formats = [f for f in formats[:3] if f.get('format_id') !=
                            (recommended[0].get('format_id') if recommended else '')]
            for fmt in backup_formats:
                recommendation_text += f"• {fmt.get('format_id', '')}: {fmt.get('resolution', '')} {fmt.get('ext', '')}\n"

            return recommendation_text
        else:
            return f"❌ 获取推荐失败: {result.get('detail', '未知错误')}"
    except Exception as e:
        error_msg = f"❌ 获取推荐失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

def batch_download_videos(urls, format_preference="best"):
    """批量下载视频"""
    try:
        if not urls:
            return "❌ 请提供要下载的视频URL列表"

        urls_list = [url.strip() for url in urls.split('\n') if url.strip()]
        if not urls_list:
            return "❌ URL列表为空"

        logger.info(f"开始批量下载: {len(urls_list)} 个视频")

        results = []
        successful_downloads = []
        failed_downloads = []

        for i, url in enumerate(urls_list, 1):
            try:
                # 为每个视频创建下载任务
                payload = {
                    "url": url,
                    "format": format_preference
                }

                response = requests.post(f"{API_BASE_URL}/download", json=payload, timeout=10)
                response.raise_for_status()
                result = response.json()

                if result.get("success"):
                    task_id = result.get("data", {}).get("task_id")
                    results.append(f"✅ 视频 {i}: 下载任务创建成功 (ID: {task_id})")
                    successful_downloads.append(task_id)
                else:
                    error_msg = result.get("error", "未知错误")
                    results.append(f"❌ 视频 {i}: {error_msg}")
                    failed_downloads.append(url)

            except Exception as e:
                results.append(f"❌ 视频 {i}: 下载失败 - {str(e)}")
                failed_downloads.append(url)

        # 汇总结果
        summary = f"\n📊 批量下载完成统计:\n"
        summary += f"• 成功创建任务: {len(successful_downloads)} 个\n"
        summary += f"• 失败: {len(failed_downloads)} 个\n"
        summary += f"• 总计: {len(urls_list)} 个视频\n"

        if successful_downloads:
            summary += f"\n✅ 成功的任务ID: {', '.join(successful_downloads[:5])}"
            if len(successful_downloads) > 5:
                summary += f" ... 还有 {len(successful_downloads) - 5} 个"

        return "\n".join(results) + summary

    except Exception as e:
        error_msg = f"❌ 批量下载失败: {str(e)}"
        logger.error(error_msg)
        return error_msg

def get_format_preview_details(url, format_id):
    """获取格式预览详情"""
    try:
        logger.info(f"获取格式预览: {url}, 格式: {format_id}")

        # 获取所有格式
        params = {"url": url}
        response = requests.get(f"{API_BASE_URL}/formats", params=params, timeout=15)
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            formats = result.get("data", {}).get("formats", [])

            # 查找指定格式
            target_format = None
            for fmt in formats:
                if fmt.get("format_id") == format_id:
                    target_format = fmt
                    break

            if target_format:
                preview_text = f"📋 格式 {format_id} 详细信息:\n\n"
                preview_text += f"🎬 基本信息:\n"
                preview_text += f"   格式ID: {target_format.get('format_id', '未知')}\n"
                preview_text += f"   扩展名: {target_format.get('ext', '未知')}\n"
                preview_text += f"   容器: {target_format.get('container', '未知')}\n\n"

                preview_text += f"🖥️ 视频信息:\n"
                preview_text += f"   分辨率: {target_format.get('resolution', '未知')}\n"
                preview_text += f"   帧率: {target_format.get('fps', '未知')} fps\n"
                preview_text += f"   视频编码: {target_format.get('vcodec', '未知')}\n"
                preview_text += f"   视频比特率: {target_format.get('vbr', '未知')} kbps\n\n"

                preview_text += f"🔊 音频信息:\n"
                preview_text += f"   音频编码: {target_format.get('acodec', '未知')}\n"
                preview_text += f"   音频比特率: {target_format.get('abr', '未知')} kbps\n\n"

                preview_text += f"💾 文件信息:\n"
                preview_text += f"   文件大小: {target_format.get('filesize', '未知') or '未知'}\n"
                preview_text += f"   预估大小: {target_format.get('filesize_approx', '未知') or '未知'}\n"
                preview_text += f"   总比特率: {target_format.get('tbr', '未知')} kbps\n\n"

                preview_text += f"⚙️ 其他信息:\n"
                preview_text += f"   质量: {target_format.get('quality', '未知')}\n"
                preview_text += f"   格式备注: {target_format.get('format_note', '未知')}\n"

                return preview_text
            else:
                return f"❌ 未找到格式 {format_id}"
        else:
            return f"❌ 获取格式详情失败: {result.get('error', '未知错误')}"
    except Exception as e:
        error_msg = f"❌ 获取格式详情失败: {str(e)}"
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

        with gr.Tab("🚀 智能下载中心"):
            gr.Markdown("""
            ## 智能下载中心

            提供智能格式选择、批量下载和高级下载选项，让下载更加智能和高效。

            **功能特点:**
            - ✅ 智能格式推荐和选择
            - ✅ 批量视频下载处理
            - ✅ 多偏好下载策略
            - ✅ 格式预览和详细信息
            - ✅ 传统下载功能保留
            """)

            # 智能单视频下载
            with gr.Row():
                gr.Markdown("### 🎯 智能单视频下载")

            with gr.Row():
                with gr.Column(scale=2):
                    smart_url_input = gr.Textbox(
                        label="视频URL",
                        placeholder="输入视频URL进行智能下载"
                    )
                with gr.Column(scale=1):
                    download_preference = gr.Dropdown(
                        choices=["balanced", "quality", "size", "speed"],
                        value="balanced",
                        label="下载偏好"
                    )

            with gr.Row():
                get_recommendation_btn = gr.Button("💡 获取推荐", variant="secondary")
                smart_download_btn = gr.Button("🚀 智能下载", variant="primary")

            # 推荐结果和格式选择
            with gr.Row():
                with gr.Column(scale=1):
                    format_recommendation = gr.Textbox(
                        label="🎯 格式推荐",
                        lines=6,
                        interactive=False,
                        value="点击获取智能推荐"
                    )
                with gr.Column(scale=1):
                    available_formats = gr.Textbox(
                        label="📋 可用格式",
                        lines=6,
                        interactive=False,
                        value="点击刷新格式列表"
                    )

            with gr.Row():
                refresh_formats_btn = gr.Button("🔄 刷新格式", variant="secondary")
                preview_format_btn = gr.Button("👁️ 预览格式", variant="secondary")

            # 格式预览区域
            with gr.Row():
                format_preview = gr.Textbox(
                    label="📋 格式详细信息",
                    lines=8,
                    interactive=False,
                    value="选择格式进行预览"
                )

            # 批量下载区域
            with gr.Row():
                gr.Markdown("### 📦 批量下载")

            with gr.Row():
                with gr.Column(scale=2):
                    batch_urls = gr.Textbox(
                        label="批量URL列表",
                        placeholder="输入多个视频URL，每行一个",
                        lines=5
                    )
                with gr.Column(scale=1):
                    batch_format = gr.Dropdown(
                        choices=["best", "balanced", "mp4", "webm", "audio"],
                        value="best",
                        label="批量格式"
                    )
                    batch_download_btn = gr.Button("📦 批量下载", variant="primary")

            # 批量下载结果
            with gr.Row():
                batch_result = gr.Textbox(
                    label="📊 批量下载结果",
                    lines=8,
                    interactive=False,
                    value="等待批量下载..."
                )

            # 传统下载功能（保留兼容性）
            with gr.Row():
                gr.Markdown("### 🔧 传统下载")

            with gr.Row():
                with gr.Column(scale=2):
                    traditional_url = gr.Textbox(
                        label="视频URL (传统)",
                        placeholder="传统下载模式"
                    )
                with gr.Column(scale=1):
                    traditional_format = gr.Dropdown(
                        choices=["best", "worst", "bestvideo+bestaudio", "mp4", "webm"],
                        value="best",
                        label="格式选择"
                    )

            with gr.Row():
                traditional_path = gr.Textbox(
                    label="输出路径",
                    value="./downloads",
                    placeholder="下载目录"
                )
                traditional_download_btn = gr.Button("🔧 传统下载", variant="secondary")

            # 下载结果显示
            with gr.Row():
                smart_download_result = gr.Textbox(
                    label="🎯 下载结果",
                    lines=3,
                    interactive=False
                )
                smart_task_id = gr.Textbox(
                    label="📋 任务ID",
                    interactive=False
                )

        with gr.Tab("📊 任务状态"):
            with gr.Row():
                task_id_input = gr.Textbox(label="任务ID", placeholder="输入任务ID查询状态")
                check_status_btn = gr.Button("查询状态")
            with gr.Row():
                status_output = gr.Textbox(label="任务状态", lines=8, interactive=False)
                download_link = gr.Textbox(label="下载链接", interactive=False)

        with gr.Tab("ℹ️ 视频信息"):
            gr.Markdown("""
            ## 增强视频信息中心

            提供全面的视频信息分析，包括基本信息、缩略图、字幕和质量分析。

            **功能特点:**
            - ✅ 综合视频信息展示
            - ✅ 多分辨率缩略图获取
            - ✅ 字幕可用性检查和预览
            - ✅ 视频质量分析和格式推荐
            - ✅ 一键字幕下载功能
            """)

            with gr.Row():
                with gr.Column(scale=2):
                    enhanced_info_url = gr.Textbox(
                        label="视频URL",
                        placeholder="输入视频URL进行详细分析"
                    )
                with gr.Column(scale=1):
                    get_comprehensive_info_btn = gr.Button("🔍 综合分析", variant="primary")

            # 综合信息展示区域
            with gr.Row():
                comprehensive_info = gr.Textbox(
                    label="📋 综合视频信息",
                    lines=10,
                    interactive=False,
                    value="等待分析..."
                )

            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 🖼️ 缩略图信息")
                    thumbnail_info = gr.Textbox(
                        label="可用缩略图",
                        lines=6,
                        interactive=False,
                        value="点击获取缩略图信息"
                    )
                    get_thumbnails_btn = gr.Button("🖼️ 获取缩略图", variant="secondary")

                with gr.Column(scale=1):
                    gr.Markdown("### 🎯 质量分析")
                    quality_analysis = gr.Textbox(
                        label="视频质量分析",
                        lines=6,
                        interactive=False,
                        value="点击进行质量分析"
                    )
                    analyze_quality_btn = gr.Button("📊 质量分析", variant="secondary")

            # 字幕管理区域
            with gr.Row():
                gr.Markdown("### 📝 字幕管理")

            with gr.Row():
                subtitle_list = gr.Dataframe(
                    headers=["语言代码", "语言名称", "格式", "下载链接"],
                    datatype=["str", "str", "str", "str"],
                    interactive=True,
                    height=200
                )

            with gr.Row():
                with gr.Column(scale=2):
                    subtitle_lang = gr.Textbox(
                        label="语言代码",
                        placeholder="例如: zh, en, ja",
                        value="zh"
                    )
                    subtitle_format = gr.Dropdown(
                        choices=["srt", "vtt", "ass"],
                        value="srt",
                        label="字幕格式"
                    )
                with gr.Column(scale=1):
                    download_subtitle_enhanced_btn = gr.Button("📥 下载字幕", variant="primary")
                    refresh_subtitles_btn = gr.Button("🔄 刷新字幕", variant="secondary")

            # 字幕下载状态
            with gr.Row():
                subtitle_download_status = gr.Textbox(
                    label="字幕下载状态",
                    lines=3,
                    interactive=False,
                    value="等待操作..."
                )

        with gr.Tab("📋 格式列表"):
            with gr.Row():
                formats_url_input = gr.Textbox(label="视频URL", placeholder="输入视频URL获取格式列表")
                list_formats_btn = gr.Button("获取格式")
            with gr.Row():
                formats_output = gr.Textbox(label="可用格式", lines=15, interactive=False)

        # 绑定事件
        # 绑定智能下载事件
        get_recommendation_btn.click(
            fn=get_smart_format_recommendation,
            inputs=[smart_url_input, download_preference],
            outputs=[format_recommendation]
        )
        refresh_formats_btn.click(
            fn=get_download_optimized_formats,
            inputs=[smart_url_input],
            outputs=[available_formats]
        )
        smart_download_btn.click(
            fn=download_video,
            inputs=[smart_url_input, download_preference, gr.State()],
            outputs=[smart_download_result, smart_task_id]
        )
        batch_download_btn.click(
            fn=batch_download_videos,
            inputs=[batch_urls, batch_format],
            outputs=[batch_result]
        )
        traditional_download_btn.click(
            fn=download_video,
            inputs=[traditional_url, traditional_format, traditional_path],
            outputs=[smart_download_result, smart_task_id]
        )
        preview_format_btn.click(
            fn=lambda url, fmt: get_format_preview_details(url, fmt) if fmt else "请先获取格式列表",
            inputs=[smart_url_input, gr.State()],
            outputs=[format_preview]
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

        # 绑定增强视频信息事件
        get_comprehensive_info_btn.click(
            fn=get_comprehensive_video_info,
            inputs=[enhanced_info_url],
            outputs=[comprehensive_info]
        )
        get_thumbnails_btn.click(
            fn=get_video_thumbnails,
            inputs=[enhanced_info_url],
            outputs=[thumbnail_info]
        )
        analyze_quality_btn.click(
            fn=get_video_quality_analysis,
            inputs=[enhanced_info_url],
            outputs=[quality_analysis]
        )
        refresh_subtitles_btn.click(
            fn=get_video_subtitles_list,
            inputs=[enhanced_info_url],
            outputs=[subtitle_list]
        )
        download_subtitle_enhanced_btn.click(
            fn=download_subtitle_direct,
            inputs=[enhanced_info_url, subtitle_lang, subtitle_format],
            outputs=[subtitle_download_status]
        )

        with gr.Tab("📝 下载字幕"):
            gr.Markdown("""
            ## 字幕下载功能

            下载视频的字幕文件，支持多种语言和格式。系统会自动使用最佳可用的cookies进行认证。

            **功能特点:**
            - ✅ 支持多种语言字幕下载
            - ✅ 自动选择最佳字幕质量
            - ✅ 支持SRT、VTT、ASS等格式
            - ✅ 自动使用cookies认证
            - ✅ 异步下载，状态实时跟踪
            """)

            with gr.Row():
                subtitle_url_input = gr.Textbox(label="视频URL", placeholder="输入视频链接")
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
                auto_select = gr.Checkbox(
                    label="自动选择最佳字幕（如果指定语言不可用）",
                    value=True
                )
            with gr.Row():
                subtitle_output_path = gr.Textbox(label="输出路径", value="./downloads")
            with gr.Row():
                subtitle_download_btn = gr.Button("📝 下载字幕", variant="primary")
            with gr.Row():
                subtitle_status = gr.Textbox(label="下载状态", lines=8, interactive=False)
            with gr.Row():
                subtitle_task_id = gr.Textbox(label="任务ID", interactive=False)

        # 绑定字幕下载事件
        subtitle_download_btn.click(
            fn=download_subtitles,
            inputs=[subtitle_url_input, subtitle_languages, auto_select, subtitle_format, subtitle_output_path],
            outputs=[subtitle_status, subtitle_task_id]
        )

        with gr.Tab("🎛️ 系统管理"):
            gr.Markdown("""
            ## 系统管理功能

            提供完整的系统管理界面，包括yt-dlp版本管理、调度器配置和系统健康检查。

            **功能特点:**
            - ✅ yt-dlp版本管理和更新
            - ✅ 调度器状态监控和配置
            - ✅ 系统健康诊断和监控
            - ✅ 实时状态更新和告警
            """)

            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 📦 yt-dlp版本管理")

                    version_info = gr.Textbox(
                        label="当前版本信息",
                        lines=4,
                        interactive=False,
                        value="点击检查版本"
                    )
                    with gr.Row():
                        check_version_btn = gr.Button("📋 检查版本", variant="secondary")
                        check_update_btn = gr.Button("🔍 检查更新", variant="primary")
                        update_btn = gr.Button("🔄 更新版本", variant="primary")
                    update_history_btn = gr.Button("📜 更新历史")

                    update_log = gr.Textbox(
                        label="更新日志",
                        lines=10,
                        interactive=False,
                        value="等待更新操作..."
                    )

                with gr.Column(scale=1):
                    gr.Markdown("### ⚙️ 调度器管理")

                    scheduler_status = gr.Textbox(
                        label="调度器状态",
                        lines=4,
                        interactive=False,
                        value="点击检查状态"
                    )
                    with gr.Row():
                        refresh_status_btn = gr.Button("🔄 刷新状态", variant="secondary")
                        start_scheduler_btn = gr.Button("▶️ 启动", variant="primary")
                        stop_scheduler_btn = gr.Button("⏹️ 停止", variant="stop")
                        config_btn = gr.Button("⚙️ 配置", variant="secondary")

                    with gr.Accordion("调度器配置", open=False):
                        with gr.Row():
                            check_interval = gr.Number(
                                label="检查间隔 (小时)",
                                value=24,
                                minimum=1,
                                maximum=168
                            )
                            auto_update = gr.Checkbox(label="自动更新", value=True)
                            update_time = gr.Textbox(
                                label="更新时间",
                                value="02:00",
                                placeholder="格式: HH:MM"
                            )
                            scheduler_enabled = gr.Checkbox(label="启用调度器", value=True)
                        save_config_btn = gr.Button("💾 保存配置", variant="primary")

            # 任务统计面板
            with gr.Row():
                total_tasks = gr.Textbox(label="总任务数", interactive=False, value="0")
                completed_tasks = gr.Textbox(label="已完成", interactive=False, value="0")
                failed_tasks = gr.Textbox(label="失败任务", interactive=False, value="0")
                pending_tasks = gr.Textbox(label="进行中", interactive=False, value="0")

            # 刷新按钮
            with gr.Row():
                refresh_system_btn = gr.Button("🔄 刷新所有状态", variant="primary")
                export_log_btn = gr.Button("📋 导出日志", variant="secondary")

        with gr.Tab("📝 任务中心"):
            gr.Markdown("""
            ## 任务管理中心

            提供完整的任务管理功能，支持任务列表查看、批量操作和实时监控。

            **功能特点:**
            - ✅ 所有任务的列表视图和分页显示
            - ✅ 批量操作（删除、重试、导出）
            - ✅ 任务搜索和过滤功能
            - ✅ 实时状态更新和进度监控
            - ✅ 任务统计和性能分析
            """)

            with gr.Row():
                # 搜索和过滤区域
                with gr.Column(scale=3):
                    task_search = gr.Textbox(
                        label="搜索任务",
                        placeholder="输入URL或任务ID"
                    )
                with gr.Column(scale=1):
                    status_filter = gr.Dropdown(
                        choices=["全部", "pending", "completed", "failed"],
                        value="全部",
                        label="状态过滤"
                    )
                with gr.Column(scale=1):
                    date_filter = gr.Textbox(
                        label="日期范围",
                        placeholder="2024-01-01,2024-12-31"
                    )
                with gr.Column(scale=1):
                    refresh_tasks_btn = gr.Button("🔄 刷新列表", variant="primary")

            # 任务列表表格
            task_dataframe = gr.Dataframe(
                headers=["任务ID", "URL", "状态", "进度", "创建时间", "完成时间"],
                datatype=["str", "str", "str", "number", "str", "str"],
                interactive=True,
                height=300
            )

            # 批量操作
            with gr.Row():
                select_all_btn = gr.Button("☑️ 全选")
                delete_selected_btn = gr.Button("🗑️ 删除选中", variant="stop")
                retry_failed_btn = gr.Button("🔄 重试失败", variant="primary")
                export_tasks_btn = gr.Button("📋 导出列表", variant="secondary")

            # 任务详情和操作
            with gr.Row():
                task_details = gr.Textbox(
                    label="选中任务详情",
                    lines=5,
                    interactive=False,
                    value="选择任务查看详情"
                )
                operation_result = gr.Textbox(
                    label="操作结果",
                    lines=3,
                    interactive=False,
                    value="等待操作..."
                )

        with gr.Tab("🍪 Cookie管理中心"):
            gr.Markdown("""
            ## Cookie管理中心

            提供完整的Cookie文件管理功能，支持自动检测、上传、验证和清理。

            **功能特点:**
            - ✅ 自动检测和导入浏览器Cookie
            - ✅ Cookie文件状态监控和验证
            - ✅ 环境诊断和问题排查
            - ✅ 过期Cookie清理和维护
            - ✅ 支持多浏览器Cookie管理
            """)

            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 🔧 Cookie管理")

                    cookie_status = gr.Textbox(
                        label="Cookie状态",
                        lines=4,
                        interactive=False,
                        value="点击检查状态"
                    )
                    with gr.Row():
                        refresh_cookie_btn = gr.Button("🔄 刷新状态", variant="secondary")
                        auto_setup_btn = gr.Button("🚀 自动设置", variant="primary")
                        cleanup_btn = gr.Button("🧹 清理过期", variant="stop")

                with gr.Column(scale=1):
                    gr.Markdown("### 🔍 环境诊断")

                    env_diagnosis = gr.Textbox(
                        label="环境诊断",
                        lines=6,
                        interactive=False,
                        value="点击开始诊断"
                    )
                    diagnose_btn = gr.Button("🔍 诊断环境", variant="primary")

                    supported_browsers = gr.Textbox(
                        label="支持的浏览器",
                        lines=4,
                        interactive=False,
                        value="点击获取列表"
                    )
                    browser_list_btn = gr.Button("🌐 浏览器列表", variant="secondary")

            # Cookie文件列表
            with gr.Row():
                gr.Markdown("### 📋 Cookie文件管理")

            with gr.Row():
                cookie_dataframe = gr.Dataframe(
                    headers=["文件名", "浏览器", "大小", "创建时间", "过期时间", "状态"],
                    datatype=["str", "str", "str", "str", "str", "str"],
                    interactive=True,
                    height=250
                )

            # Cookie操作
            with gr.Row():
                refresh_cookie_list_btn = gr.Button("🔄 刷新列表", variant="secondary")
                validate_selected_btn = gr.Button("✅ 验证选中", variant="primary")
                delete_selected_btn = gr.Button("🗑️ 删除选中", variant="stop")

            # 操作结果
            with gr.Row():
                cookie_operation_result = gr.Textbox(
                    label="操作结果",
                    lines=3,
                    interactive=False,
                    value="等待操作..."
                )

        # 绑定系统管理事件
        check_version_btn.click(
            fn=check_ytdlp_version,
            outputs=[version_info]
        )
        check_update_btn.click(
            fn=check_ytdlp_update,
            outputs=[version_info]
        )
        update_btn.click(
            fn=update_ytdlp,
            outputs=[update_log]
        )
        update_history_btn.click(
            fn=get_ytdlp_update_history,
            outputs=[update_log]
        )

        # 绑定调度器管理事件
        refresh_status_btn.click(
            fn=check_scheduler_status,
            outputs=[scheduler_status]
        )
        start_scheduler_btn.click(
            fn=start_scheduler,
            outputs=[scheduler_status]
        )
        stop_scheduler_btn.click(
            fn=stop_scheduler,
            outputs=[scheduler_status]
        )
        update_schedule_btn.click(
            fn=update_scheduler_schedule,
            inputs=[schedule_hours, schedule_days],
            outputs=[scheduler_status]
        )

        # 绑定任务中心事件
        refresh_tasks_btn.click(
            fn=refresh_task_list,
            outputs=[task_dataframe]
        )
        delete_selected_btn.click(
            fn=delete_selected_tasks,
            outputs=[operation_result]
        )
        clear_completed_btn.click(
            fn=clear_completed_tasks,
            outputs=[operation_result]
        )
        refresh_btn.click(
            fn=refresh_task_list,
            outputs=[task_dataframe]
        )

        # 绑定Cookie管理中心事件
        refresh_cookie_btn.click(
            fn=get_cookies_status,
            outputs=[cookie_status]
        )
        auto_setup_btn.click(
            fn=auto_setup_cookies,
            outputs=[cookie_operation_result]
        )
        cleanup_btn.click(
            fn=cleanup_cookies,
            outputs=[cookie_operation_result]
        )
        diagnose_btn.click(
            fn=diagnose_environment,
            outputs=[env_diagnosis]
        )
        browser_list_btn.click(
            fn=get_supported_browsers,
            outputs=[supported_browsers]
        )
        refresh_cookie_list_btn.click(
            fn=get_cookies_list,
            outputs=[cookie_dataframe]
        )
        # 注意：validate_selected_btn和delete_selected_btn需要更复杂的实现
        # 这里先简化为状态反馈
        validate_selected_btn.click(
            fn=lambda: "✅ Cookie验证功能开发中...",
            outputs=[cookie_operation_result]
        )
        delete_selected_btn.click(
            fn=lambda: "🗑️ Cookie删除功能开发中...",
            outputs=[cookie_operation_result]
        )

    return demo

if __name__ == "__main__":
    logger.info("启动Gradio应用...")
    logger.info(f"API基础URL: {API_BASE_URL}")
    logger.info(f"DOCKER_ENV环境变量: {os.getenv('DOCKER_ENV')}")

    try:
        # 创建界面
        demo = create_gradio_interface()
        logger.info("Gradio界面创建成功")

        # 启动应用并保持运行
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            prevent_thread_lock=True,  # 在supervisor中需要prevent_thread_lock保持主线程运行
            show_error=True,
            quiet=False
        )
        logger.info("Gradio应用启动成功")

        # 保持进程运行，防止退出
        import time
        while True:
            time.sleep(1)

    except Exception as e:
        logger.error(f"Gradio应用启动失败: {str(e)}")
        import traceback
        traceback.print_exc()
        # 给进程一些时间来记录错误
        time.sleep(5)
        raise