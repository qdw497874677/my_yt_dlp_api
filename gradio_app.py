import gradio as gr
import requests
import os
import time
import json
import logging

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

# Gradio界面
with gr.Blocks(title="yt-dlp 视频下载器") as demo:
    gr.Markdown("# yt-dlp 视频下载器")
    gr.Markdown("使用此工具下载YouTube等平台的视频")
    
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
    
    with gr.Tab("下载视频"):
        with gr.Row():
            url_input = gr.Textbox(label="视频URL", placeholder="请输入视频链接")
        with gr.Row():
            format_choice = gr.Dropdown(
                choices=["best", "bestvideo+bestaudio/best", "mp4", "webm", "flv"],
                value="bestvideo+bestaudio/best",
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
