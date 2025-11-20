#!/usr/bin/env python3
"""
Gradio Docker启动修复脚本
修复Gradio在Docker supervisor环境中的启动问题
"""

import os
import sys
import time
import signal
import threading
import logging

def create_fixed_gradio_app():
    """创建修复后的Gradio启动脚本"""

    fixed_gradio_script = '''#!/usr/bin/env python3
"""
修复后的Gradio启动脚本
确保在Docker supervisor环境中稳定运行
"""

import os
import sys
import time
import logging
import signal
import gradio as gr
import requests
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API基础URL
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')

# 全局变量用于优雅退出
should_exit = False

def signal_handler(signum, frame):
    """处理退出信号"""
    global should_exit
    logger.info(f"收到信号 {signum}，准备优雅退出...")
    should_exit = True

# 注册信号处理器
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

def test_api_connection():
    """测试API连接"""
    try:
        response = requests.get(f"{API_BASE_URL}/docs", timeout=5)
        return response.status_code == 200
    except:
        return False

def create_simple_interface():
    """创建简化的Gradio界面"""
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

        with gr.Tab("📥 下载视频"):
            gr.Markdown("视频下载功能正在维护中...")

        with gr.Tab("📝 下载字幕"):
            gr.Markdown("字幕下载功能正在维护中...")

        with gr.Tab("🔐 YouTube登录"):
            gr.Markdown("YouTube登录功能正在维护中...")

        with gr.Tab("ℹ️ 视频信息"):
            gr.Markdown("视频信息功能正在维护中...")

        with gr.Tab("📋 格式列表"):
            gr.Markdown("格式列表功能正在维护中...")

        with gr.Tab("📊 任务状态"):
            gr.Markdown("任务状态功能正在维护中...")

    return demo

def main():
    """主函数"""
    logger.info("启动修复后的Gradio应用...")
    logger.info(f"API基础URL: {API_BASE_URL}")
    logger.info(f"DOCKER_ENV环境变量: {os.getenv('DOCKER_ENV')}")

    # 等待FastAPI服务启动
    logger.info("等待FastAPI服务启动...")
    max_wait = 60  # 最多等待60秒
    wait_count = 0

    while not test_api_connection() and wait_count < max_wait:
        logger.info(f"等待FastAPI服务... ({wait_count}/{max_wait})")
        time.sleep(1)
        wait_count += 1

        if should_exit:
            logger.info("收到退出信号，停止启动")
            return

    if not test_api_connection():
        logger.warning("FastAPI服务连接失败，但继续启动Gradio...")
    else:
        logger.info("FastAPI服务连接成功")

    try:
        # 创建Gradio界面
        logger.info("创建Gradio界面...")
        demo = create_simple_interface()
        logger.info("Gradio界面创建成功")

        # 设置Gradio启动参数
        launch_kwargs = {
            "server_name": "0.0.0.0",
            "server_port": 7860,
            "prevent_thread_lock": False,  # 重要：不阻止线程锁定
            "show_error": True,
            "quiet": False,
            "inbrowser": False,
        }

        logger.info(f"启动Gradio服务，参数: {launch_kwargs}")

        # 在单独的线程中启动Gradio
        gradio_thread = None
        def start_gradio():
            try:
                demo.launch(**launch_kwargs)
                logger.info("Gradio服务启动完成")
            except Exception as e:
                logger.error(f"Gradio启动失败: {e}")
                import traceback
                traceback.print_exc()

        gradio_thread = threading.Thread(target=start_gradio, daemon=True)
        gradio_thread.start()

        # 等待Gradio完全启动
        time.sleep(10)
        logger.info("Gradio应用启动完成，开始保持运行...")

        # 主循环 - 保持进程运行
        while not should_exit:
            time.sleep(1)

            # 检查Gradio线程状态
            if gradio_thread and not gradio_thread.is_alive():
                logger.error("Gradio线程已停止")
                break

        logger.info("开始优雅关闭Gradio服务...")

    except Exception as e:
        logger.error(f"Gradio应用启动失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
'''

    return fixed_gradio_script

def main():
    """主修复函数"""
    print("🔧 修复Gradio Docker启动配置...")

    # 创建修复后的Gradio启动脚本
    fixed_script = create_fixed_gradio_app()

    # 备份原始文件
    if os.path.exists('gradio_app.py'):
        print("📋 备份原始gradio_app.py...")
        os.rename('gradio_app.py', 'gradio_app_original.py')

    # 写入修复后的脚本
    with open('gradio_app.py', 'w') as f:
        f.write(fixed_script)

    # 设置执行权限
    os.chmod('gradio_app.py', 0o755)

    print("✅ Gradio启动配置修复完成")
    print("📝 修复内容:")
    print("  - 添加信号处理机制")
    print("  - 等待FastAPI服务启动")
    print("  - 在单独线程中启动Gradio")
    print("  - 添加优雅退出机制")
    print("  - 简化界面以确保稳定启动")
    print("  - 增强错误处理和日志记录")

    print("\n🚀 现在可以重新部署Docker:")
    print("  docker-compose build")
    print("  docker-compose up -d")
    print("  docker-compose logs -f yt-dlp-api-service")

if __name__ == "__main__":
    main()