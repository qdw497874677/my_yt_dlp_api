#!/usr/bin/env python3
"""
YT-DLP Cookie Management MCP Server
为yt-dlp API的cookie管理功能提供MCP接口
"""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List, Optional, Union
import aiohttp
from mcp import ClientSession, StdioServerParameters
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# 添加项目路径
sys.path.insert(0, "/Users/quandawei/项目/my_yt_dlp_api")

# 导入项目模块
from cookie_manager import auto_cookie_manager
from utils.browser_utils import detect_browsers, get_system_info

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建MCP Server实例
server = Server("yt-dlp-cookie-manager")

# API基础URL
API_BASE_URL = "http://localhost:8000"

class YtDlpApiClient:
    """YT-DLP API客户端"""

    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """GET请求"""
        url = f"{self.base_url}{endpoint}"
        async with self.session.get(url, params=params) as response:
            return await response.json()

    async def post(self, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """POST请求"""
        url = f"{self.base_url}{endpoint}"
        async with self.session.post(url, json=data) as response:
            return await response.json()

# ===== Cookie管理工具 =====

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """列出所有可用工具"""
    return [
        types.Tool(
            name="get_cookie_status",
            description="获取当前cookie状态和信息",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="auto_setup_cookies",
            description="自动设置Edge浏览器cookies",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="diagnose_environment",
            description="诊断cookie管理环境",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="get_video_info",
            description="获取YouTube视频信息",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "YouTube视频URL"
                    }
                },
                "required": ["url"]
            }
        ),
        types.Tool(
            name="list_video_formats",
            description="列出YouTube视频可用格式",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "YouTube视频URL"
                    }
                },
                "required": ["url"]
            }
        ),
        types.Tool(
            name="create_download_task",
            description="创建视频下载任务",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "YouTube视频URL"
                    },
                    "format": {
                        "type": "string",
                        "description": "视频格式（可选，默认为best）",
                        "enum": ["best", "worst", "bestaudio", "bestvideo"]
                    }
                },
                "required": ["url"]
            }
        ),
        types.Tool(
            name="get_task_status",
            description="获取下载任务状态",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "任务ID"
                    }
                },
                "required": ["task_id"]
            }
        ),
        types.Tool(
            name="list_tasks",
            description="列出所有下载任务",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="refresh_cookies",
            description="刷新cookies",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    """处理工具调用"""
    try:
        async with YtDlpApiClient() as client:
            if name == "get_cookie_status":
                result = await client.get("/cookies/status")
                return [types.TextContent(
                    type="text",
                    text=f"Cookie状态:\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                )]

            elif name == "auto_setup_cookies":
                result = await client.post("/cookies/auto-setup")
                return [types.TextContent(
                    type="text",
                    text=f"自动设置cookies结果:\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                )]

            elif name == "diagnose_environment":
                result = await client.get("/cookies/diagnose")
                return [types.TextContent(
                    type="text",
                    text=f"环境诊断结果:\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                )]

            elif name == "get_video_info":
                url = arguments.get("url")
                if not url:
                    raise ValueError("缺少必需参数: url")

                params = {"url": url}
                result = await client.get("/info", params=params)
                return [types.TextContent(
                    type="text",
                    text=f"视频信息:\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                )]

            elif name == "list_video_formats":
                url = arguments.get("url")
                if not url:
                    raise ValueError("缺少必需参数: url")

                params = {"url": url}
                result = await client.get("/formats", params=params)
                return [types.TextContent(
                    type="text",
                    text=f"可用格式:\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                )]

            elif name == "create_download_task":
                url = arguments.get("url")
                if not url:
                    raise ValueError("缺少必需参数: url")

                format_type = arguments.get("format", "best")
                data = {"url": url, "format": format_type}
                result = await client.post("/download", data=data)
                return [types.TextContent(
                    type="text",
                    text=f"下载任务创建成功:\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                )]

            elif name == "get_task_status":
                task_id = arguments.get("task_id")
                if not task_id:
                    raise ValueError("缺少必需参数: task_id")

                result = await client.get(f"/task/{task_id}")
                return [types.TextContent(
                    type="text",
                    text=f"任务状态:\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                )]

            elif name == "list_tasks":
                result = await client.get("/tasks")
                return [types.TextContent(
                    type="text",
                    text=f"所有任务:\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                )]

            elif name == "refresh_cookies":
                result = await client.post("/cookies/refresh")
                return [types.TextContent(
                    type="text",
                    text=f"刷新cookies结果:\n{json.dumps(result, indent=2, ensure_ascii=False)}"
                )]

            else:
                raise ValueError(f"未知工具: {name}")

    except Exception as e:
        logger.error(f"工具调用失败: {e}")
        return [types.TextContent(
            type="text",
            text=f"错误: {str(e)}"
        )]

# ===== 资源定义 =====

@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """列出所有可用资源"""
    return [
        types.Resource(
            uri="cookie://status",
            name="Cookie状态",
            description="当前cookie状态和信息",
            mimeType="application/json"
        ),
        types.Resource(
            uri="cookie://diagnosis",
            name="环境诊断",
            description="cookie管理环境诊断信息",
            mimeType="application/json"
        ),
        types.Resource(
            uri="cookie://browser-detection",
            name="浏览器检测",
            description="Edge浏览器检测结果",
            mimeType="application/json"
        )
    ]

@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """读取资源内容"""
    try:
        if uri == "cookie://status":
            async with YtDlpApiClient() as client:
                result = await client.get("/cookies/status")
                return json.dumps(result, indent=2, ensure_ascii=False)

        elif uri == "cookie://diagnosis":
            async with YtDlpApiClient() as client:
                result = await client.get("/cookies/diagnose")
                return json.dumps(result, indent=2, ensure_ascii=False)

        elif uri == "cookie://browser-detection":
            # 本地浏览器检测
            detected = detect_browsers()
            system_info = get_system_info()
            result = {
                "system_info": system_info,
                "detected_browsers": detected,
                "timestamp": str(asyncio.get_event_loop().time())
            }
            return json.dumps(result, indent=2, ensure_ascii=False)

        else:
            raise ValueError(f"未知资源: {uri}")

    except Exception as e:
        logger.error(f"读取资源失败: {e}")
        return json.dumps({"error": str(e)})

async def main():
    """启动MCP Server"""
    # 运行服务器
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="yt-dlp-cookie-manager",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())