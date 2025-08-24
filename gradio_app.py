import gradio as gr
import requests
import os
import time
import json

# API配置
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
# 在Docker容器中，如果API_BASE_URL设置为localhost，需要改为容器服务名
if API_BASE_URL == "http://localhost:8000" and os.getenv("DOCKER_ENV"):
    API_BASE_URL = "http://yt-dlp-api:8000"

def download_video(url, format_choice, output_path="./downloads"):
    """提交下载任务"""
    try:
        # 准备请求数据
        payload = {
            "url": url,
            "output_path": output_path,
            "format": format_choice
        }
        
        # 发送POST请求到API
        response = requests.post(f"{API_BASE_URL}/download", json=payload)
        response.raise_for_status()
        
        # 解析响应
        result = response.json()
        task_id = result.get("task_id")
        
        if not task_id:
            return "错误：无法获取任务ID", None
        
        # 轮询任务状态直到完成
        status_output = ""
        while True:
            status_response = requests.get(f"{API_BASE_URL}/task/{task_id}")
            status_response.raise_for_status()
            status_data = status_response.json()
            
            task_status = status_data.get("data", {}).get("status", "unknown")
            status_output += f"任务状态: {task_status}\n"
            
            if task_status == "completed":
                # 获取下载文件
                file_response = requests.get(f"{API_BASE_URL}/download/{task_id}/file")
                if file_response.status_code == 200:
                    # 保存文件
                    filename = f"downloaded_video_{task_id}.mp4"
                    with open(filename, "wb") as f:
                        f.write(file_response.content)
                    return status_output + "下载完成！", filename
                else:
                    return status_output + "错误：无法下载文件", None
            elif task_status == "failed":
                error = status_data.get("data", {}).get("error", "未知错误")
                return status_output + f"下载失败: {error}", None
            
            # 等待一段时间后再次检查
            time.sleep(2)
            
    except Exception as e:
        return f"错误: {str(e)}", None

def get_video_info(url):
    """获取视频信息"""
    try:
        response = requests.get(f"{API_BASE_URL}/info?url={url}")
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
        
        return f"标题: {title}\n时长: {duration}\n上传者: {uploader}"
    except Exception as e:
        return f"获取视频信息失败: {str(e)}"

def list_formats(url):
    """列出可用格式"""
    try:
        response = requests.get(f"{API_BASE_URL}/formats?url={url}")
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
        
        return "\n".join(format_list) if format_list else "未找到可用格式"
    except Exception as e:
        return f"获取格式列表失败: {str(e)}"

# Gradio界面
with gr.Blocks(title="yt-dlp 视频下载器") as demo:
    gr.Markdown("# yt-dlp 视频下载器")
    gr.Markdown("使用此工具下载YouTube等平台的视频")
    
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
            output_path = gr.Textbox(label="输出路径", value="./downloads")
        with gr.Row():
            download_btn = gr.Button("开始下载")
        with gr.Row():
            status_output = gr.Textbox(label="下载状态", interactive=False, lines=10)
        with gr.Row():
            video_output = gr.Video(label="下载的视频")
        
        download_btn.click(
            fn=download_video,
            inputs=[url_input, format_choice, output_path],
            outputs=[status_output, video_output]
        )
    
    with gr.Tab("视频信息"):
        with gr.Row():
            info_url = gr.Textbox(label="视频URL", placeholder="请输入视频链接")
        with gr.Row():
            info_btn = gr.Button("获取信息")
        with gr.Row():
            info_output = gr.Textbox(label="视频信息", interactive=False, lines=10)
        
        info_btn.click(
            fn=get_video_info,
            inputs=[info_url],
            outputs=[info_output]
        )
    
    with gr.Tab("格式列表"):
        with gr.Row():
            formats_url = gr.Textbox(label="视频URL", placeholder="请输入视频链接")
        with gr.Row():
            formats_btn = gr.Button("列出格式")
        with gr.Row():
            formats_output = gr.Textbox(label="可用格式", interactive=False, lines=15)
        
        formats_btn.click(
            fn=list_formats,
            inputs=[formats_url],
            outputs=[formats_output]
        )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
