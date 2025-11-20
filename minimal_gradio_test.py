#!/usr/bin/env python3
"""
最小化Gradio测试应用
用于验证Gradio启动逻辑，不依赖外部库
"""

import os
import sys
import logging
import time
import threading
import signal
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局变量
should_exit = False

def signal_handler(signum, frame):
    """处理退出信号"""
    global should_exit
    logger.info(f"收到信号 {signum}，准备退出...")
    should_exit = True

# 注册信号处理器
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

class MinimalGradio:
    """最小化Gradio模拟类"""

    def __init__(self):
        self.components = []

    def Blocks(self, title=None):
        """创建Blocks容器"""
        return BlocksContainer(title)

    def Textbox(self, label=None, placeholder=None, value=None, interactive=False, lines=None):
        """创建文本框组件"""
        comp = {
            'type': 'textbox',
            'label': label,
            'placeholder': placeholder,
            'value': value,
            'interactive': interactive,
            'lines': lines
        }
        self.components.append(comp)
        return comp

    def Button(self, value=None, variant=None):
        """创建按钮组件"""
        comp = {
            'type': 'button',
            'value': value,
            'variant': variant
        }
        self.components.append(comp)
        return comp

    def Tab(self, label=None):
        """创建标签页"""
        return TabContainer(label)

    def Markdown(self, content=None):
        """创建Markdown组件"""
        comp = {
            'type': 'markdown',
            'content': content
        }
        self.components.append(comp)
        return comp

class BlocksContainer:
    """Blocks容器"""

    def __init__(self, title=None):
        self.title = title
        self.children = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return self

    def launch(self, server_name="0.0.0.0", server_port=7860, **kwargs):
        """启动应用"""
        logger.info(f"启动Gradio应用 '{self.title}'")
        logger.info(f"服务器地址: http://{server_name}:{server_port}")
        logger.info(f"启动参数: {kwargs}")

        print(f"""
🎉 Gradio应用启动成功！
📱 访问地址: http://{server_name}:{server_port}
📊 标题: {self.title}
🧪 组件数量: {len(self.children)} 个标签页
""")

        return True

class TabContainer:
    """标签页容器"""

    def __init__(self, label):
        self.label = label
        self.components = []

    def __enter__(self):
        print(f"  📁 创建标签页: {self.label}")
        return self

    def __exit__(self, *args):
        return self

    def Row(self):
        """创建行容器"""
        return self

    def Column(self):
        """创建列容器"""
        return self

    def add_component(self, comp):
        """添加组件"""
        self.components.append(comp)

class MockRequests:
    """模拟requests库"""

    class Response:
        def __init__(self, status_code=200, json_data=None):
            self.status_code = status_code
            self._json_data = json_data or {"success": True, "data": {}}

        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception(f"HTTP {self.status_code}")

        def json(self):
            return self._json_data

    def get(self, url, **kwargs):
        logger.info(f"模拟GET请求: {url}")
        return self.Response()

    def post(self, url, **kwargs):
        logger.info(f"模拟POST请求: {url}")
        return self.Response()

# 创建全局实例
gr = MinimalGradio()
requests = MockRequests()

def create_minimal_interface():
    """创建最小化Gradio界面"""

    with gr.Blocks(title="yt-dlp 视频下载器 - 最小测试版") as demo:
        gr.Markdown("# 🎬 yt-dlp 视频下载器")
        gr.Markdown("最小测试版本 - 验证启动逻辑")

        with gr.Tab("🔧 系统测试"):
            gr.Markdown("## 系统信息")
            gr.Textbox(
                label="Python版本",
                value=f"{sys.version}",
                interactive=False
            )
            gr.Textbox(
                label="启动时间",
                value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                interactive=False
            )
            gr.Textbox(
                label="工作目录",
                value=os.getcwd(),
                interactive=False
            )
            gr.Button("🧪 运行测试", variant="primary")

        with gr.Tab("📥 视频下载"):
            gr.Markdown("## 视频下载功能")
            gr.Textbox(label="视频URL", placeholder="输入视频链接")
            gr.Textbox(label="下载状态", value="等待测试...", interactive=False)
            gr.Button("📥 开始下载", variant="primary")

        with gr.Tab("🔐 YouTube登录"):
            gr.Markdown("## YouTube浏览器登录")
            gr.Textbox(label="登录状态", value="等待测试...", interactive=False)
            gr.Button("🚀 启动登录", variant="primary")

        with gr.Tab("📝 字幕下载"):
            gr.Markdown("## 字幕下载功能")
            gr.Textbox(label="字幕状态", value="等待测试...", interactive=False)
            gr.Button("📝 下载字幕", variant="primary")

    return demo

def main():
    """主函数"""
    logger.info("启动最小化Gradio测试应用...")
    logger.info(f"Python版本: {sys.version}")
    logger.info(f"工作目录: {os.getcwd()}")
    logger.info(f"环境变量 DOCKER_ENV: {os.getenv('DOCKER_ENV', 'None')}")

    try:
        # 创建界面
        logger.info("创建Gradio界面...")
        demo = create_minimal_interface()
        logger.info("Gradio界面创建成功")

        # 启动参数
        launch_kwargs = {
            "server_name": "0.0.0.0",
            "server_port": 7860,
            "prevent_thread_lock": True,
            "show_error": True,
            "quiet": False
        }

        logger.info(f"启动参数: {launch_kwargs}")

        # 在后台线程中启动（模拟真实Gradio行为）
        def start_in_background():
            return demo.launch(**launch_kwargs)

        background_thread = threading.Thread(target=start_in_background, daemon=True)
        background_thread.start()

        logger.info("Gradio应用启动成功")

        # 保持主进程运行
        logger.info("保持进程运行，按 Ctrl+C 退出...")
        while not should_exit:
            time.sleep(1)

        logger.info("应用正常退出")

    except KeyboardInterrupt:
        logger.info("收到中断信号，退出应用")
    except Exception as e:
        logger.error(f"应用启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()